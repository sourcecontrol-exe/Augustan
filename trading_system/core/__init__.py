"""
Trading System Core Module

Provides core functionality for the trading system.

Migration Guide:
- config_manager.ConfigManager -> config_manager_refactored.ConfigManager
- event_system.EventBus -> event_system_refactored.EventBus
"""
import warnings

# Export refactored components (recommended)
from .config_manager_refactored import ConfigManager as NewConfigManager
from .event_system_refactored import EventBus as NewEventBus, create_event_bus
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

# Backward compatibility - deprecate old imports
try:
    from .config_manager import ConfigManager as OldConfigManager
    from .event_system import EventBus as OldEventBus, event_bus as old_event_bus
    
    # Alias for backward compatibility with deprecation warning
    def ConfigManager(*args, **kwargs):
        warnings.warn(
            "ConfigManager is deprecated. Use NewConfigManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return OldConfigManager(*args, **kwargs)
    
except ImportError:
    pass

__all__ = [
    # Refactored (recommended)
    'NewConfigManager',
    'NewEventBus',
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
