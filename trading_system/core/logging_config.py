"""
Structured logging configuration for the trading system.

Provides:
- Consistent log levels
- Structured JSON logging
- Context logging
- Performance logging
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
from pathlib import Path


class StructuredLogger:
    """
    Structured logger for the trading system.
    
    Provides:
    - JSON structured logs
    - Context information
    - Performance metrics
    - Consistent formatting
    """
    
    @staticmethod
    def log_trade_event(
        event_type: str,
        symbol: str,
        details: Dict[str, Any],
        level: str = "INFO"
    ):
        """
        Log a trade event with structured data.
        
        Args:
            event_type: Type of event (e.g., 'order_placed', 'signal_generated')
            symbol: Trading symbol
            details: Event details
            level: Log level
        """
        log_data = {
            'event_type': event_type,
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            **details
        }
        
        getattr(logger, level.lower())(json.dumps(log_data))
    
    @staticmethod
    def log_performance(
        operation: str,
        duration_ms: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log performance metrics.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            context: Additional context
        """
        log_data = {
            'type': 'performance',
            'operation': operation,
            'duration_ms': duration_ms,
            'timestamp': datetime.now().isoformat()
        }
        
        if context:
            log_data.update(context)
        
        logger.info(json.dumps(log_data))
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        """
        Log error with context.
        
        Args:
            error: Exception object
            context: Additional context
            error_code: Error code
        """
        log_data = {
            'type': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        
        if error_code:
            log_data['error_code'] = error_code
        
        if context:
            log_data['context'] = context
        
        if hasattr(error, 'error_code'):
            log_data['error_code'] = error.error_code
        
        if hasattr(error, 'details'):
            log_data['details'] = error.details
        
        logger.error(json.dumps(log_data))
    
    @staticmethod
    def log_system_event(
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log system events.
        
        Args:
            event_type: Type of event
            message: Event message
            details: Additional details
        """
        log_data = {
            'type': 'system_event',
            'event_type': event_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            log_data.update(details)
        
        logger.info(json.dumps(log_data))


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup structured logging.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with structured format
    logger.add(
        lambda msg: print(msg, end=''),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=log_level.upper()
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level=log_level.upper(),
            rotation="10 MB",
            retention="30 days"
        )
    
    # Set Python logging to use loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            logger_opt = logger.opt(depth=6, exception=record.exc_info)
            logger_opt.log(record.levelname, record.getMessage())
    
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level.upper())


# Performance decorator
def log_performance(func):
    """Decorator to log function performance."""
    from functools import wraps
    import time
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            StructuredLogger.log_performance(
                operation=func.__name__,
                duration_ms=duration
            )
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            StructuredLogger.log_error(e)
            StructuredLogger.log_performance(
                operation=func.__name__,
                duration_ms=duration,
                context={'error': True}
            )
            raise
    
    return wrapper


def log_performance_async(func):
    """Async decorator to log function performance."""
    from functools import wraps
    import time
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            StructuredLogger.log_performance(
                operation=func.__name__,
                duration_ms=duration
            )
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            StructuredLogger.log_error(e)
            StructuredLogger.log_performance(
                operation=func.__name__,
                duration_ms=duration,
                context={'error': True}
            )
            raise
    
    return wrapper

