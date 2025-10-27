"""
Refactored Configuration Manager - Non-singleton with dependency injection.

This is the new, improved configuration manager that:
- Uses dependency injection instead of singleton pattern
- Acts as a structured container for configuration sections
- Provides strongly-typed access via Pydantic models
- Eliminates global mutable state

Usage:
    # Create and inject at application entry point
    from trading_system.core.config_manager_refactored import ConfigManager
    
    config_loader = ConfigLoader(config_dir=Path("config"))
    config_manager = ConfigManager(config_loader.load_application_config())
    
    # Inject into components
    trading_engine = TradingEngine(config_manager)
"""
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from .config_schemas import (
    ApplicationConfig,
    RiskManagementConfig,
    DataFetchingConfig,
    SignalGenerationConfig,
    VolumeSettings,
    JobSettings,
)
from .config_loader import ConfigLoader


class ConfigManager:
    """
    Configuration Manager - Structured container for application configuration.
    
    This class is a lightweight container that provides easy access to
    strongly-typed configuration sections. It should be instantiated at the
    application entry point and injected into components.
    
    Benefits over the old singleton pattern:
    - Testable: Easy to inject test configurations
    - No global state: Each component gets its own view
    - Clear dependencies: Explicit configuration passing
    - Thread-safe: No shared mutable state
    - Immutable: Configuration cannot be accidentally modified
    
    Example:
        from trading_system.core.config_loader import ConfigLoader
        from trading_system.core.config_manager_refactored import ConfigManager
        
        # Load configuration
        loader = ConfigLoader()
        app_config = loader.load_application_config("exchanges_config.json")
        
        # Create manager
        manager = ConfigManager(app_config)
        
        # Inject into components
        engine = TradingEngine(config_manager=manager)
    """
    
    def __init__(self, app_config: ApplicationConfig):
        """
        Initialize the configuration manager with an application configuration.
        
        Args:
            app_config: Complete application configuration (from ConfigLoader)
        """
        self._app_config = app_config
        logger.info("ConfigManager initialized with application configuration")
    
    @classmethod
    def create(
        cls,
        config_name: str = "exchanges_config.json",
        config_dir: Optional[Path] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> 'ConfigManager':
        """
        Factory method to create a ConfigManager from a config file.
        
        Args:
            config_name: Name of the configuration file
            config_dir: Directory containing config files
            overrides: Optional configuration overrides
            
        Returns:
            Configured ConfigManager instance
        """
        loader = ConfigLoader(config_dir=config_dir)
        app_config = loader.load_application_config(
            config_name=config_name,
            overrides=overrides
        )
        return cls(app_config)
    
    @classmethod
    def create_for_testing(
        cls,
        overrides: Optional[Dict[str, Any]] = None
    ) -> 'ConfigManager':
        """
        Create a ConfigManager for testing with overrides.
        
        Args:
            overrides: Configuration overrides for testing
            
        Returns:
            ConfigManager with test configuration
        """
        # Create a test configuration
        test_config = {
            'risk_management': {
                'default_budget': 1000.0,
                'max_risk_per_trade': 0.01,
                'max_positions': 1,
            },
            'data_fetching': {
                'max_retries': 1,
                'timeout_seconds': 5,
            },
            'trading_mode': 'paper',
        }
        
        if overrides:
            def deep_merge(base, override):
                for key, value in override.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        base[key] = deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base
            test_config = deep_merge(test_config, overrides)
        
        # Create Pydantic model with defaults
        app_config = ApplicationConfig(**test_config)
        return cls(app_config)
    
    # Properties for easy access to configuration sections
    
    @property
    def risk_management(self) -> RiskManagementConfig:
        """Get risk management configuration."""
        return self._app_config.risk_management
    
    @property
    def data_fetching(self) -> DataFetchingConfig:
        """Get data fetching configuration."""
        return self._app_config.data_fetching
    
    @property
    def signal_generation(self) -> SignalGenerationConfig:
        """Get signal generation configuration."""
        return self._app_config.signal_generation
    
    @property
    def volume_settings(self) -> VolumeSettings:
        """Get volume settings."""
        return self._app_config.volume_settings
    
    @property
    def job_settings(self) -> JobSettings:
        """Get job settings."""
        return self._app_config.job_settings
    
    @property
    def trading_mode(self) -> str:
        """Get current trading mode (paper or live)."""
        return self._app_config.trading_mode
    
    @property
    def is_paper_trading(self) -> bool:
        """Check if in paper trading mode."""
        return self._app_config.trading_mode == "paper"
    
    @property
    def is_live_trading(self) -> bool:
        """Check if in live trading mode."""
        return self._app_config.trading_mode == "live"
    
    def get_exchange_config(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific exchange.
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            Exchange configuration dictionary or None
        """
        return self._app_config.exchanges.get(exchange_name)
    
    def get_all_exchange_configs(self) -> Dict[str, Any]:
        """Get all exchange configurations."""
        return self._app_config.exchanges
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration as dictionary (for serialization)."""
        return self._app_config.dict(exclude_none=True)
    
    def reload(self, config_name: str, config_dir: Optional[Path] = None):
        """
        Reload configuration from file.
        
        Args:
            config_name: Name of the configuration file
            config_dir: Directory containing config files
        """
        logger.info(f"Reloading configuration from {config_name}")
        loader = ConfigLoader(config_dir=config_dir)
        self._app_config = loader.load_application_config(config_name)
        logger.info("Configuration reloaded successfully")
    
    def __repr__(self) -> str:
        """String representation of the configuration manager."""
        return (
            f"ConfigManager("
            f"mode={self.trading_mode}, "
            f"budget={self.risk_management.default_budget}, "
            f"risk_per_trade={self.risk_management.max_risk_per_trade}"
            f")"
        )

