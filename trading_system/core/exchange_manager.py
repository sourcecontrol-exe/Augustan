"""
ExchangeManager - Manages connections to multiple exchanges and handles API interactions.

This module provides centralized management of exchange connections, including
connection pooling, error handling, rate limiting, and failover mechanisms.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import ccxt
from loguru import logger

from .orderbook import OrderBook


class ExchangeStatus(Enum):
    """Exchange connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class ExchangeConfig:
    """Configuration for an exchange."""
    name: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    sandbox: bool = True
    rate_limit: int = 1200  # milliseconds
    timeout: int = 30000  # milliseconds
    retry_count: int = 3
    retry_delay: float = 1.0
    max_connections: int = 5
    enabled: bool = True


@dataclass
class ExchangeHealth:
    """Exchange health metrics."""
    name: str
    status: ExchangeStatus
    last_ping: Optional[datetime] = None
    response_time: Optional[float] = None
    error_count: int = 0
    success_count: int = 0
    last_error: Optional[str] = None
    rate_limit_reset: Optional[datetime] = None


class ExchangeManager:
    """
    Manages connections to multiple exchanges with failover and health monitoring.
    
    Features:
    - Connection pooling and management
    - Automatic failover between exchanges
    - Rate limiting and backoff
    - Health monitoring and recovery
    - Order book synchronization
    - Error handling and retry logic
    """
    
    def __init__(self, configs: List[ExchangeConfig]):
        """
        Initialize exchange manager.
        
        Args:
            configs: List of exchange configurations
        """
        self.configs = {config.name: config for config in configs}
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.health: Dict[str, ExchangeHealth] = {}
        self.orderbooks: Dict[str, Dict[str, OrderBook]] = {}  # exchange -> symbol -> orderbook
        
        # Connection management
        self.connection_pool: Dict[str, List[ccxt.Exchange]] = {}
        self.active_connections: Dict[str, int] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, float]] = {}  # exchange -> endpoint -> last_call_time
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.connection_callbacks: List[Callable[[str, ExchangeStatus], None]] = []
        self.data_callbacks: List[Callable[[str, str, Dict], None]] = []  # exchange, symbol, data
        
        self._initialize_exchanges()
        logger.info(f"ExchangeManager initialized with {len(self.exchanges)} exchanges")
    
    def _initialize_exchanges(self):
        """Initialize exchange connections."""
        for name, config in self.configs.items():
            if not config.enabled:
                continue
                
            try:
                # Create exchange instance
                exchange_class = getattr(ccxt, name.lower(), None)
                if not exchange_class:
                    logger.error(f"Unknown exchange: {name}")
                    continue
                
                exchange_options = {
                    'apiKey': config.api_key,
                    'secret': config.secret,
                    'sandbox': config.sandbox,
                    'rateLimit': config.rate_limit,
                    'timeout': config.timeout,
                    'enableRateLimit': True,
                }
                
                exchange = exchange_class(exchange_options)
                
                # Initialize connection pool
                self.connection_pool[name] = [exchange]
                self.active_connections[name] = 0
                
                # Initialize health tracking
                self.health[name] = ExchangeHealth(
                    name=name,
                    status=ExchangeStatus.DISCONNECTED
                )
                
                # Initialize rate limiting
                self.rate_limits[name] = {}
                
                # Initialize order books
                self.orderbooks[name] = {}
                
                self.exchanges[name] = exchange
                logger.info(f"Initialized exchange: {name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")
                self.health[name] = ExchangeHealth(
                    name=name,
                    status=ExchangeStatus.ERROR,
                    last_error=str(e)
                )
    
    async def connect(self, exchange_name: str) -> bool:
        """
        Connect to a specific exchange.
        
        Args:
            exchange_name: Name of the exchange to connect to
            
        Returns:
            True if connection was successful
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange not found: {exchange_name}")
            return False
        
        try:
            self.health[exchange_name].status = ExchangeStatus.CONNECTING
            
            # Test connection with a simple API call
            exchange = self.exchanges[exchange_name]
            start_time = time.time()
            
            # Try to fetch server time (lightweight call)
            await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_time
            )
            
            response_time = time.time() - start_time
            
            # Update health status
            self.health[exchange_name].status = ExchangeStatus.CONNECTED
            self.health[exchange_name].last_ping = datetime.now()
            self.health[exchange_name].response_time = response_time
            self.health[exchange_name].success_count += 1
            self.health[exchange_name].last_error = None
            
            # Notify callbacks
            self._notify_connection_callbacks(exchange_name, ExchangeStatus.CONNECTED)
            
            logger.info(f"Connected to {exchange_name} (response time: {response_time:.3f}s)")
            return True
            
        except ccxt.RateLimitExceeded as e:
            self.health[exchange_name].status = ExchangeStatus.RATE_LIMITED
            self.health[exchange_name].last_error = str(e)
            logger.warning(f"Rate limited on {exchange_name}: {e}")
            return False
            
        except Exception as e:
            self.health[exchange_name].status = ExchangeStatus.ERROR
            self.health[exchange_name].error_count += 1
            self.health[exchange_name].last_error = str(e)
            logger.error(f"Failed to connect to {exchange_name}: {e}")
            return False
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all enabled exchanges."""
        results = {}
        tasks = []
        
        for exchange_name in self.exchanges.keys():
            task = asyncio.create_task(self.connect(exchange_name))
            tasks.append((exchange_name, task))
        
        for exchange_name, task in tasks:
            try:
                results[exchange_name] = await task
            except Exception as e:
                logger.error(f"Error connecting to {exchange_name}: {e}")
                results[exchange_name] = False
        
        return results
    
    async def disconnect(self, exchange_name: str):
        """Disconnect from an exchange."""
        if exchange_name in self.health:
            self.health[exchange_name].status = ExchangeStatus.DISCONNECTED
            self._notify_connection_callbacks(exchange_name, ExchangeStatus.DISCONNECTED)
            logger.info(f"Disconnected from {exchange_name}")
    
    async def disconnect_all(self):
        """Disconnect from all exchanges."""
        for exchange_name in self.exchanges.keys():
            await self.disconnect(exchange_name)
    
    def get_exchange(self, exchange_name: str) -> Optional[ccxt.Exchange]:
        """Get exchange instance by name."""
        return self.exchanges.get(exchange_name)
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of currently available exchanges."""
        available = []
        for name, health in self.health.items():
            if health.status == ExchangeStatus.CONNECTED:
                available.append(name)
        return available
    
    def get_health_status(self, exchange_name: str) -> Optional[ExchangeHealth]:
        """Get health status for an exchange."""
        return self.health.get(exchange_name)
    
    def get_all_health_status(self) -> Dict[str, ExchangeHealth]:
        """Get health status for all exchanges."""
        return self.health.copy()
    
    async def fetch_orderbook(self, exchange_name: str, symbol: str, 
                            limit: int = 100) -> Optional[Dict]:
        """
        Fetch order book from exchange.
        
        Args:
            exchange_name: Name of the exchange
            symbol: Trading symbol
            limit: Number of levels to fetch
            
        Returns:
            Order book data or None if failed
        """
        if not self._check_rate_limit(exchange_name, 'fetch_orderbook'):
            logger.warning(f"Rate limited: {exchange_name} fetch_orderbook")
            return None
        
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return None
            
            # Fetch order book
            orderbook_data = await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_order_book, symbol, limit
            )
            
            # Update local order book
            await self._update_orderbook(exchange_name, symbol, orderbook_data)
            
            # Notify data callbacks
            self._notify_data_callbacks(exchange_name, symbol, orderbook_data)
            
            return orderbook_data
            
        except ccxt.RateLimitExceeded as e:
            self._handle_rate_limit(exchange_name, 'fetch_orderbook')
            logger.warning(f"Rate limited on {exchange_name}: {e}")
            return None
            
        except Exception as e:
            self.health[exchange_name].error_count += 1
            self.health[exchange_name].last_error = str(e)
            logger.error(f"Error fetching orderbook from {exchange_name}: {e}")
            return None
    
    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Fetch ticker data from exchange."""
        if not self._check_rate_limit(exchange_name, 'fetch_ticker'):
            return None
        
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return None
            
            ticker_data = await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_ticker, symbol
            )
            
            # Notify data callbacks
            self._notify_data_callbacks(exchange_name, symbol, ticker_data)
            
            return ticker_data
            
        except Exception as e:
            self.health[exchange_name].error_count += 1
            self.health[exchange_name].last_error = str(e)
            logger.error(f"Error fetching ticker from {exchange_name}: {e}")
            return None
    
    async def fetch_ohlcv(self, exchange_name: str, symbol: str, 
                         timeframe: str = '1m', limit: int = 100) -> Optional[List]:
        """Fetch OHLCV data from exchange."""
        if not self._check_rate_limit(exchange_name, 'fetch_ohlcv'):
            return None
        
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return None
            
            ohlcv_data = await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_ohlcv, symbol, timeframe, None, limit
            )
            
            # Notify data callbacks
            self._notify_data_callbacks(exchange_name, symbol, ohlcv_data)
            
            return ohlcv_data
            
        except Exception as e:
            self.health[exchange_name].error_count += 1
            self.health[exchange_name].last_error = str(e)
            logger.error(f"Error fetching OHLCV from {exchange_name}: {e}")
            return None
    
    async def _update_orderbook(self, exchange_name: str, symbol: str, 
                              orderbook_data: Dict):
        """Update local order book with new data."""
        try:
            if symbol not in self.orderbooks[exchange_name]:
                self.orderbooks[exchange_name][symbol] = OrderBook(symbol)
            
            orderbook = self.orderbooks[exchange_name][symbol]
            
            # Extract bids and asks
            bids = orderbook_data.get('bids', [])
            asks = orderbook_data.get('asks', [])
            
            # Update order book
            success = orderbook.update(bids, asks)
            if not success:
                logger.warning(f"Failed to update orderbook for {exchange_name}:{symbol}")
            
        except Exception as e:
            logger.error(f"Error updating orderbook: {e}")
    
    def get_orderbook(self, exchange_name: str, symbol: str) -> Optional[OrderBook]:
        """Get local order book for exchange and symbol."""
        return self.orderbooks.get(exchange_name, {}).get(symbol)
    
    def _check_rate_limit(self, exchange_name: str, endpoint: str) -> bool:
        """Check if endpoint is rate limited."""
        if exchange_name not in self.rate_limits:
            return True
        
        last_call = self.rate_limits[exchange_name].get(endpoint, 0)
        config = self.configs[exchange_name]
        rate_limit_ms = config.rate_limit
        
        current_time = time.time() * 1000
        if current_time - last_call < rate_limit_ms:
            return False
        
        self.rate_limits[exchange_name][endpoint] = current_time
        return True
    
    def _handle_rate_limit(self, exchange_name: str, endpoint: str):
        """Handle rate limit exceeded."""
        self.health[exchange_name].status = ExchangeStatus.RATE_LIMITED
        self.health[exchange_name].rate_limit_reset = datetime.now() + timedelta(minutes=1)
    
    def _notify_connection_callbacks(self, exchange_name: str, status: ExchangeStatus):
        """Notify connection status callbacks."""
        for callback in self.connection_callbacks:
            try:
                callback(exchange_name, status)
            except Exception as e:
                logger.error(f"Connection callback error: {e}")
    
    def _notify_data_callbacks(self, exchange_name: str, symbol: str, data: Dict):
        """Notify data callbacks."""
        for callback in self.data_callbacks:
            try:
                callback(exchange_name, symbol, data)
            except Exception as e:
                logger.error(f"Data callback error: {e}")
    
    def add_connection_callback(self, callback: Callable[[str, ExchangeStatus], None]):
        """Add connection status callback."""
        self.connection_callbacks.append(callback)
    
    def add_data_callback(self, callback: Callable[[str, str, Dict], None]):
        """Add data callback."""
        self.data_callbacks.append(callback)
    
    async def start_health_monitoring(self):
        """Start health monitoring task."""
        if self.health_check_task and not self.health_check_task.done():
            return
        
        self.health_check_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("Started health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring task."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped health monitoring")
    
    async def _health_monitoring_loop(self):
        """Health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check health of all exchanges
                for exchange_name in self.exchanges.keys():
                    health = self.health[exchange_name]
                    
                    # Skip if recently checked
                    if health.last_ping and (datetime.now() - health.last_ping).seconds < 30:
                        continue
                    
                    # Test connection
                    await self.connect(exchange_name)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def get_stats(self) -> Dict[str, Any]:
        """Get exchange manager statistics."""
        total_exchanges = len(self.exchanges)
        connected_exchanges = len(self.get_available_exchanges())
        
        health_summary = {}
        for name, health in self.health.items():
            health_summary[name] = {
                'status': health.status.value,
                'response_time': health.response_time,
                'error_count': health.error_count,
                'success_count': health.success_count,
                'last_error': health.last_error
            }
        
        return {
            'total_exchanges': total_exchanges,
            'connected_exchanges': connected_exchanges,
            'health_summary': health_summary,
            'orderbook_count': sum(len(orderbooks) for orderbooks in self.orderbooks.values())
        }
