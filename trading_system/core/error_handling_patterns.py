"""
Error Handling Patterns - Best practices for replacing broad exception catching.

Shows:
- Specific exception handling
- Error context and logging
- Proper re-raising
- Error recovery patterns
"""

from typing import Optional, Dict, Any
from loguru import logger

from .exceptions import (
    TradingSystemError,
    ExchangeError,
    RateLimitError,
    NetworkError,
    OrderError,
    handle_exception
)
from .logging_config import StructuredLogger


# Pattern 1: Replace broad exception catching with specific exceptions
def pattern_1_specific_exceptions():
    """
    ❌ BAD: Broad exception catching
    try:
        trade()
    except Exception as e:
        logger.error(e)
    
    ✅ GOOD: Specific exception handling
    """
    try:
        # Perform trade
        pass
    except OrderError as e:
        logger.error(f"Order failed: {e.message}", order_id=e.order_id, symbol=e.symbol)
        # Handle specifically
    except RateLimitError as e:
        logger.warning(f"Rate limited: {e.message}, retry at {e.reset_time}")
        # Implement backoff
    except NetworkError as e:
        logger.error(f"Network error: {e.message}")
        # Retry logic
    except TradingSystemError as e:
        logger.error(f"Trading error: {e.message}, code: {e.error_code}")
    # Don't catch base Exception unless absolutely necessary


# Pattern 2: Add error context
def pattern_2_error_context():
    """
    ✅ GOOD: Add context to errors for better debugging
    """
    try:
        # Some operation
        symbol = "BTC/USDT"
        order_id = "12345"
        result = place_order(symbol, order_id)
    except Exception as e:
        # Add context before re-raising
        context = {
            'symbol': symbol,
            'order_id': order_id,
            'operation': 'place_order'
        }
        
        trading_error = handle_exception(e, context=context)
        logger.error(trading_error)
        raise trading_error


# Pattern 3: Error recovery with retry
def pattern_3_retry_with_specific_errors():
    """
    ✅ GOOD: Retry logic with specific error handling
    """
    import asyncio
    from .exceptions import RateLimitError, NetworkError
    
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            return await execute_operation()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.reset_time - time.time() if e.reset_time else retry_delay
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                continue
            raise
        except NetworkError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error, retrying in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise
    
    raise TradingSystemError("Max retries exceeded")


# Pattern 4: Structured logging for errors
def pattern_4_structured_error_logging():
    """
    ✅ GOOD: Use structured logging for errors
    """
    try:
        # Operation
        pass
    except TradingSystemError as e:
        StructuredLogger.log_error(
            error=e,
            context={
                'operation': 'trade_execution',
                'symbol': 'BTC/USDT'
            },
            error_code=e.error_code
        )
        
        # Re-raise with context
        raise


# Pattern 5: Error handling in async functions
def pattern_5_async_error_handling():
    """
    ✅ GOOD: Proper error handling in async functions
    """
    import asyncio
    
    async def process_trade(symbol: str):
        try:
            return await execute_trade(symbol)
        except OrderError as e:
            StructuredLogger.log_error(
                error=e,
                context={'symbol': symbol, 'operation': 'process_trade'},
                error_code='ORDER_ERROR'
            )
            # Decide whether to re-raise or return error
            raise
        except asyncio.CancelledError:
            # Must re-raise CancelledError
            raise
        except Exception as e:
            # Last resort - convert and re-raise
            trading_error = handle_exception(e, context={'symbol': symbol})
            StructuredLogger.log_error(trading_error)
            raise trading_error from e


# Pattern 6: Error handling in background tasks
def pattern_6_background_task_errors():
    """
    ✅ GOOD: Handle errors in background tasks without stopping the system
    """
    import asyncio
    
    async def background_monitoring():
        while True:
            try:
                await monitor_system()
            except TradingSystemError as e:
                # Log but don't crash the system
                StructuredLogger.log_error(
                    error=e,
                    context={'task': 'monitoring'},
                    error_code=e.error_code
                )
                # Continue monitoring
            except asyncio.CancelledError:
                # Properly handle cancellation
                logger.info("Monitoring task cancelled")
                break
            except Exception as e:
                # Log and continue for unexpected errors
                logger.error(f"Unexpected error in monitoring: {e}")
            
            await asyncio.sleep(1)


# Pattern 7: Graceful degradation
def pattern_7_graceful_degradation():
    """
    ✅ GOOD: Graceful degradation when non-critical operations fail
    """
    results = {}
    
    # Try to get data from primary source
    try:
        results['primary'] = await fetch_from_primary_source()
    except DataError as e:
        logger.warning(f"Primary source failed: {e.message}")
        
        # Fallback to secondary source
        try:
            results['secondary'] = await fetch_from_secondary_source()
        except DataError as e:
            logger.error(f"Secondary source also failed: {e.message}")
            # Continue with degraded functionality
            results = {}
    
    return results


# Helper functions for common patterns
async def execute_operation():
    """Dummy function for examples."""
    pass


async def execute_trade(symbol: str):
    """Dummy function for examples."""
    pass


def place_order(symbol: str, order_id: str):
    """Dummy function for examples."""
    pass


async def fetch_from_primary_source():
    """Dummy function for examples."""
    pass


async def fetch_from_secondary_source():
    """Dummy function for examples."""
    pass


async def monitor_system():
    """Dummy function for examples."""
    pass

