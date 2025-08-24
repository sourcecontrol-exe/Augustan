"""
Configuration Manager for Augustan Trading Bot

This module manages loading different configuration files based on environment
(testing, live, or default) and provides a unified interface for accessing
configuration values.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages configuration loading from different environment-specific files.
    
    Supports:
    - Testing configuration (configs/testing/config.json)
    - Live trading configuration (configs/live/config.json)
    - Default configuration (configs/default.json)
    """
    
    def __init__(self, environment: str = None):
        """
        Initialize configuration manager.
        
        Args:
            environment: 'testing', 'live', or None for auto-detection
        """
        self.environment = environment or self._detect_environment()
        self.config_path = self._get_config_path()
        self.config_data = {}
        self._load_config()
        
        logger.info(f"Configuration loaded from: {self.config_path}")
    
    def _detect_environment(self) -> str:
        """
        Auto-detect environment based on environment variables or file existence.
        
        Returns:
            Environment name: 'testing', 'live', or 'default'
        """
        # Check environment variable first
        env_var = os.getenv('AUGUSTAN_ENV', '').lower()
        if env_var in ['testing', 'live']:
            return env_var
        
        # Check if live config exists and is accessible
        live_config = Path('configs/live/config.json')
        if live_config.exists() and self._is_live_environment():
            return 'live'
        
        # Default to testing for safety
        return 'testing'
    
    def _is_live_environment(self) -> bool:
        """
        Check if this is a live trading environment.
        
        Returns:
            True if live environment, False otherwise
        """
        # Check for production indicators
        production_indicators = [
            os.getenv('PRODUCTION', '').lower() == 'true',
            os.getenv('LIVE_TRADING', '').lower() == 'true',
            os.getenv('DEPLOYMENT_ENV', '').lower() == 'production'
        ]
        
        return any(production_indicators)
    
    def _get_config_path(self) -> Path:
        """
        Get the path to the configuration file for the current environment.
        
        Returns:
            Path to configuration file
        """
        base_path = Path('configs')
        
        if self.environment == 'testing':
            config_file = base_path / 'testing' / 'config.json'
        elif self.environment == 'live':
            config_file = base_path / 'live' / 'config.json'
        else:
            config_file = base_path / 'default.json'
        
        # Ensure the config file exists
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            # Fallback to default
            config_file = base_path / 'default.json'
            
            if not config_file.exists():
                raise FileNotFoundError(f"No configuration file found in {base_path}")
        
        return config_file
    
    def _load_config(self):
        """Load configuration from the selected file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'trading.timeframe')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                value = value[k]
            
            return value
        except (KeyError, TypeError):
            return default
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration section."""
        return self.config_data.get('trading', {})
    
    def get_scanner_config(self) -> Dict[str, Any]:
        """Get scanner configuration section."""
        return self.config_data.get('scanner', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration section."""
        return self.config_data.get('risk_management', {})
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy parameters configuration section."""
        return self.config_data.get('strategy_parameters', {})
    
    def get_exchanges_config(self) -> Dict[str, Any]:
        """Get exchanges configuration section."""
        return self.config_data.get('exchanges', {})
    
    def get_trading_sessions_config(self) -> Dict[str, Any]:
        """Get trading sessions configuration section."""
        return self.config_data.get('trading_sessions', {})
    
    def get_backtesting_config(self) -> Dict[str, Any]:
        """Get backtesting configuration section."""
        return self.config_data.get('backtesting', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration section."""
        return self.config_data.get('logging', {})
    
    def get_notifications_config(self) -> Dict[str, Any]:
        """Get notifications configuration section."""
        return self.config_data.get('notifications', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration section."""
        return self.config_data.get('monitoring', {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get the complete configuration."""
        return self.config_data.copy()
    
    def reload(self):
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        self._load_config()
    
    def switch_environment(self, environment: str):
        """
        Switch to a different environment configuration.
        
        Args:
            environment: 'testing', 'live', or 'default'
        """
        if environment not in ['testing', 'live', 'default']:
            raise ValueError(f"Invalid environment: {environment}")
        
        logger.info(f"Switching environment from {self.environment} to {environment}")
        self.environment = environment
        self.config_path = self._get_config_path()
        self._load_config()
    
    def validate(self) -> bool:
        """
        Validate configuration completeness and values.
        
        Returns:
            True if valid, False otherwise
        """
        required_sections = ['trading', 'scanner', 'risk_management', 'exchanges']
        
        for section in required_sections:
            if section not in self.config_data:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate critical values
        trading_config = self.get_trading_config()
        if not trading_config.get('total_capital', 0) > 0:
            logger.error("Total capital must be positive")
            return False
        
        risk_config = self.get_risk_config()
        if not (0 < risk_config.get('risk_per_trade', 0) <= 0.1):
            logger.error("Risk per trade must be between 0 and 0.1")
            return False
        
        logger.info("Configuration validation passed")
        return True
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the current configuration environment."""
        return {
            'environment': self.environment,
            'config_file': str(self.config_path),
            'testnet': self.get('trading.testnet', True),
            'total_capital': self.get('trading.total_capital', 0),
            'timeframe': self.get('trading.timeframe', 'unknown'),
            'risk_per_trade': self.get('risk_management.risk_per_trade', 0)
        }


# Global configuration instance
config_manager = ConfigManager()

# Convenience functions for backward compatibility
def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration (backward compatibility)."""
    return config_manager.get_trading_config()

def get_scanner_config() -> Dict[str, Any]:
    """Get scanner configuration (backward compatibility)."""
    return config_manager.get_scanner_config()

def get_risk_config() -> Dict[str, Any]:
    """Get risk management configuration (backward compatibility)."""
    return config_manager.get_risk_config()

def get_exchanges_config() -> Dict[str, Any]:
    """Get exchanges configuration (backward compatibility)."""
    return config_manager.get_exchanges_config()

def get_active_config() -> Dict[str, Any]:
    """Get all active configuration (backward compatibility)."""
    return config_manager.get_all_config()
