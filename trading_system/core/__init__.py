"""
Trading System Core Module

Provides core functionality for the trading system.
"""
from .config_manager import ConfigManager
from .event_system import EventBus, create_event_bus
from .exceptions import (
    TradingSystemError,
    ConfigurationError,
    ExchangeError,
    OrderError,
    RiskManagementError,
    SignalGenerationError,
    handle_exception
)
from .logging_config import (
    StructuredLogger,
    setup_logging,
    log_performance,
    log_performance_async
)
from .testing_utils import (
    MockMarketDataFactory,
    MockConfigFactory,
    MockExchangeFactory,
    AssertionHelpers,
    PerformanceTestHelpers
)

# Export config_schemas
from .config_schemas import (
    ApplicationConfig,
    RiskManagementConfig,
    DataFetchingConfig,
    SignalGenerationConfig,
    VolumeSettings,
    JobSettings,
    ConfigPaths
)

# Export config_loader
from .config_loader import ConfigLoader

__all__ = [
    # Configuration
    'ConfigManager',
    # Event system
    'EventBus',
    'create_event_bus',
    
    # Exceptions
    'TradingSystemError',
    'ConfigurationError',
    'ExchangeError',
    'OrderError',
    'RiskManagementError',
    'SignalGenerationError',
    'handle_exception',
    
    # Logging
    'StructuredLogger',
    'setup_logging',
    'log_performance',
    'log_performance_async',
    
    # Testing
    'MockMarketDataFactory',
    'MockConfigFactory',
    'MockExchangeFactory',
    'AssertionHelpers',
    'PerformanceTestHelpers',
    
    # Config
    'ApplicationConfig',
    'RiskManagementConfig',
    'DataFetchingConfig',
    'SignalGenerationConfig',
    'VolumeSettings',
    'JobSettings',
    'ConfigPaths',
    'ConfigLoader',
]
