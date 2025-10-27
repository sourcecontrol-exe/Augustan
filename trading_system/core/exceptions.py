"""
Custom exceptions for the trading system.

Provides specific exception types instead of generic Exception catching.
"""
from typing import Optional, Dict, Any


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(TradingSystemError):
    """Raised when configuration is invalid or missing."""
    pass


class ExchangeError(TradingSystemError):
    """Raised when exchange operations fail."""
    pass


class OrderError(TradingSystemError):
    """Raised when order operations fail."""
    def __init__(self, message: str, order_id: Optional[str] = None, symbol: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.symbol = symbol


class RiskManagementError(TradingSystemError):
    """Raised when risk management checks fail."""
    pass


class SignalGenerationError(TradingSystemError):
    """Raised when signal generation fails."""
    pass


class DataError(TradingSystemError):
    """Raised when data operations fail."""
    pass


class ValidationError(TradingSystemError):
    """Raised when validation fails."""
    pass


class RateLimitError(ExchangeError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, reset_time: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.reset_time = reset_time


class NetworkError(ExchangeError):
    """Raised when network operations fail."""
    pass


class AuthenticationError(ExchangeError):
    """Raised when authentication fails."""
    pass


class InsufficientBalanceError(OrderError):
    """Raised when insufficient balance for order."""
    pass


class InvalidOrderError(OrderError):
    """Raised when order parameters are invalid."""
    pass


class OrderExecutionError(OrderError):
    """Raised when order execution fails."""
    pass


class MarketDataError(DataError):
    """Raised when market data operations fail."""
    pass


class StrategyExecutionError(SignalGenerationError):
    """Raised when strategy execution fails."""
    pass


def handle_exception(error: Exception, context: Optional[Dict[str, Any]] = None) -> TradingSystemError:
    """
    Convert generic exceptions to specific trading system exceptions.
    
    Args:
        error: Original exception
        context: Additional context information
        
    Returns:
        Appropriate TradingSystemError subclass
    """
    context = context or {}
    
    # Map common exceptions to specific types
    error_msg = str(error)
    
    if "rate limit" in error_msg.lower() or "429" in error_msg:
        return RateLimitError(
            f"Rate limit exceeded: {error_msg}",
            error_code="RATE_LIMIT",
            details=context
        )
    
    if "network" in error_msg.lower() or "connection" in error_msg.lower():
        return NetworkError(
            f"Network error: {error_msg}",
            error_code="NETWORK_ERROR",
            details=context
        )
    
    if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
        return AuthenticationError(
            f"Authentication failed: {error_msg}",
            error_code="AUTH_ERROR",
            details=context
        )
    
    if "insufficient balance" in error_msg.lower():
        return InsufficientBalanceError(
            f"Insufficient balance: {error_msg}",
            error_code="INSUFFICIENT_BALANCE",
            details=context
        )
    
    if "invalid" in error_msg.lower():
        return ValidationError(
            f"Validation error: {error_msg}",
            error_code="VALIDATION_ERROR",
            details=context
        )
    
    # Return generic error if no specific match
    return TradingSystemError(
        f"Trading system error: {error_msg}",
        error_code="GENERIC_ERROR",
        details=context
    )

