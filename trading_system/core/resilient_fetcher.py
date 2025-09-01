"""
Resilient Data Fetcher with Retry Logic and Error Handling
"""
import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
import ccxt

from .config_manager import get_config_manager, DataFetchingConfig


@dataclass
class ExchangeStatus:
    """Track exchange health and failures."""
    name: str
    is_enabled: bool = True
    failure_count: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    disabled_until: Optional[datetime] = None


class ResilientFetcher:
    """
    Resilient data fetcher with exponential backoff and automatic exchange disabling.
    
    Features:
    - Exponential backoff retry mechanism
    - Automatic exchange disabling after repeated failures
    - Health monitoring and recovery
    - Rate limiting protection
    - Comprehensive error handling
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize resilient fetcher."""
        self.config_manager = get_config_manager(config_path)
        self.fetch_config = self.config_manager.get_data_fetching_config()
        self.exchange_status: Dict[str, ExchangeStatus] = {}
        
        logger.info(f"ResilientFetcher initialized with {self.fetch_config.max_retries} max retries")
    
    def _get_exchange_status(self, exchange_name: str) -> ExchangeStatus:
        """Get or create exchange status tracker."""
        if exchange_name not in self.exchange_status:
            self.exchange_status[exchange_name] = ExchangeStatus(name=exchange_name)
        return self.exchange_status[exchange_name]
    
    def _is_exchange_available(self, exchange_name: str) -> bool:
        """Check if exchange is currently available for use."""
        status = self._get_exchange_status(exchange_name)
        
        # Check if exchange is temporarily disabled
        if status.disabled_until and datetime.now() < status.disabled_until:
            return False
        
        # Re-enable if cooldown period has passed
        if status.disabled_until and datetime.now() >= status.disabled_until:
            status.is_enabled = True
            status.disabled_until = None
            status.consecutive_failures = 0
            logger.info(f"Re-enabled {exchange_name} after cooldown period")
        
        return status.is_enabled
    
    def _record_success(self, exchange_name: str):
        """Record successful operation."""
        status = self._get_exchange_status(exchange_name)
        status.last_success = datetime.now()
        status.consecutive_failures = 0
        
        # Re-enable if it was disabled
        if not status.is_enabled:
            status.is_enabled = True
            status.disabled_until = None
            logger.info(f"Re-enabled {exchange_name} after successful operation")
    
    def _record_failure(self, exchange_name: str, error: Exception):
        """Record failed operation and potentially disable exchange."""
        status = self._get_exchange_status(exchange_name)
        status.failure_count += 1
        status.consecutive_failures += 1
        status.last_failure = datetime.now()
        
        logger.warning(f"{exchange_name} failure #{status.consecutive_failures}: {error}")
        
        # Disable exchange after too many consecutive failures
        if status.consecutive_failures >= self.fetch_config.max_retries * 2:
            disable_minutes = min(60, status.consecutive_failures * 5)  # Max 1 hour
            status.is_enabled = False
            status.disabled_until = datetime.now() + timedelta(minutes=disable_minutes)
            
            logger.error(f"Disabled {exchange_name} for {disable_minutes} minutes due to repeated failures")
    
    async def fetch_with_retry(self, 
                              fetch_func: Callable,
                              exchange_name: str,
                              *args, **kwargs) -> Optional[Any]:
        """
        Execute a fetch function with retry logic and error handling.
        
        Args:
            fetch_func: Function to execute
            exchange_name: Name of the exchange for status tracking
            *args, **kwargs: Arguments to pass to fetch_func
            
        Returns:
            Result of fetch_func or None if all retries failed
        """
        if not self._is_exchange_available(exchange_name):
            logger.debug(f"Skipping {exchange_name} - currently disabled")
            return None
        
        last_error = None
        delay = self.fetch_config.retry_delay
        
        for attempt in range(self.fetch_config.max_retries):
            try:
                # Add timeout protection
                result = await asyncio.wait_for(
                    self._execute_fetch(fetch_func, *args, **kwargs),
                    timeout=self.fetch_config.timeout_seconds
                )
                
                self._record_success(exchange_name)
                return result
                
            except asyncio.TimeoutError as e:
                last_error = f"Timeout after {self.fetch_config.timeout_seconds}s"
                logger.warning(f"{exchange_name} attempt {attempt + 1} timed out")
                
            except ccxt.NetworkError as e:
                last_error = f"Network error: {str(e)}"
                logger.warning(f"{exchange_name} attempt {attempt + 1} network error: {e}")
                
            except ccxt.RateLimitExceeded as e:
                last_error = f"Rate limit exceeded: {str(e)}"
                logger.warning(f"{exchange_name} rate limit exceeded on attempt {attempt + 1}")
                # Longer delay for rate limits
                delay *= self.fetch_config.rate_limit_buffer
                
            except ccxt.ExchangeError as e:
                last_error = f"Exchange error: {str(e)}"
                logger.warning(f"{exchange_name} exchange error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"{exchange_name} unexpected error on attempt {attempt + 1}: {e}")
            
            # Don't sleep after the last attempt
            if attempt < self.fetch_config.max_retries - 1:
                logger.debug(f"Retrying {exchange_name} in {delay:.1f}s...")
                await asyncio.sleep(delay)
                delay *= self.fetch_config.backoff_multiplier
        
        # All retries failed
        self._record_failure(exchange_name, Exception(last_error))
        logger.error(f"{exchange_name} failed after {self.fetch_config.max_retries} attempts: {last_error}")
        return None
    
    async def _execute_fetch(self, fetch_func: Callable, *args, **kwargs) -> Any:
        """Execute fetch function, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(fetch_func):
            return await fetch_func(*args, **kwargs)
        else:
            # Run synchronous function in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: fetch_func(*args, **kwargs))
    
    def fetch_with_retry_sync(self, 
                             fetch_func: Callable,
                             exchange_name: str,
                             *args, **kwargs) -> Optional[Any]:
        """Synchronous wrapper for fetch_with_retry."""
        return asyncio.run(self.fetch_with_retry(fetch_func, exchange_name, *args, **kwargs))
    
    def get_exchange_health_report(self) -> Dict[str, Dict[str, Any]]:
        """Get health report for all exchanges."""
        report = {}
        
        for exchange_name, status in self.exchange_status.items():
            report[exchange_name] = {
                "is_enabled": status.is_enabled,
                "failure_count": status.failure_count,
                "consecutive_failures": status.consecutive_failures,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "last_failure": status.last_failure.isoformat() if status.last_failure else None,
                "disabled_until": status.disabled_until.isoformat() if status.disabled_until else None,
            }
        
        return report
    
    def reset_exchange_status(self, exchange_name: str):
        """Reset status for a specific exchange."""
        if exchange_name in self.exchange_status:
            status = self.exchange_status[exchange_name]
            status.is_enabled = True
            status.consecutive_failures = 0
            status.disabled_until = None
            logger.info(f"Reset status for {exchange_name}")
    
    def get_enabled_exchanges(self) -> List[str]:
        """Get list of currently enabled exchanges."""
        enabled = []
        for name, status in self.exchange_status.items():
            if self._is_exchange_available(name):
                enabled.append(name)
        return enabled
    
    def get_disabled_exchanges(self) -> List[str]:
        """Get list of currently disabled exchanges."""
        disabled = []
        for name, status in self.exchange_status.items():
            if not self._is_exchange_available(name):
                disabled.append(name)
        return disabled
