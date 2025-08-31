"""
Custom exceptions for the Augustan Trading Bot

This module defines all custom exceptions used throughout the bot
to provide better error handling and debugging.
"""

class AugustanError(Exception):
    """Base exception class for all Augustan Trading Bot errors"""
    pass


class ConfigurationError(AugustanError):
    """Raised when there's a configuration error"""
    pass


class ExchangeConnectionError(AugustanError):
    """Raised when unable to connect to an exchange"""
    pass


class ExchangeAPIError(AugustanError):
    """Raised when an exchange API call fails"""
    
    def __init__(self, message: str, exchange: str = None, status_code: int = None):
        super().__init__(message)
        self.exchange = exchange
        self.status_code = status_code


class DataFetchError(AugustanError):
    """Raised when unable to fetch market data"""
    
    def __init__(self, message: str, symbol: str = None, timeframe: str = None):
        super().__init__(message)
        self.symbol = symbol
        self.timeframe = timeframe


class StrategyError(AugustanError):
    """Raised when there's an error in strategy execution"""
    
    def __init__(self, message: str, strategy_name: str = None):
        super().__init__(message)
        self.strategy_name = strategy_name


class RiskManagementError(AugustanError):
    """Raised when there's an error in risk management calculations"""
    
    def __init__(self, message: str, calculation_type: str = None):
        super().__init__(message)
        self.calculation_type = calculation_type


class OrderError(AugustanError):
    """Raised when there's an error with order operations"""
    
    def __init__(self, message: str, order_id: str = None, symbol: str = None):
        super().__init__(message)
        self.order_id = order_id
        self.symbol = symbol


class InsufficientBalanceError(AugustanError):
    """Raised when there's insufficient balance for a trade"""
    
    def __init__(self, message: str, currency: str = None, required: float = None, available: float = None):
        super().__init__(message)
        self.currency = currency
        self.required = required
        self.available = available


class ValidationError(AugustanError):
    """Raised when data validation fails"""
    
    def __init__(self, message: str, field: str = None, value: any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class AdapterError(AugustanError):
    """Raised when there's an error with exchange adapters"""
    
    def __init__(self, message: str, adapter_name: str = None):
        super().__init__(message)
        self.adapter_name = adapter_name


class ScannerError(AugustanError):
    """Raised when there's an error in market scanning"""
    
    def __init__(self, message: str, scan_type: str = None):
        super().__init__(message)
        self.scan_type = scan_type


class BacktestError(AugustanError):
    """Raised when there's an error in backtesting"""
    
    def __init__(self, message: str, backtest_id: str = None):
        super().__init__(message)
        self.backtest_id = backtest_id
