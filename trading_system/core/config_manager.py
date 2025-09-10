"""
Centralized Configuration Manager
Provides singleton access to all application configuration.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from .position_sizing import RiskManagementConfig
from ..config_loader import SecureConfigLoader


@dataclass
class DataFetchingConfig:
    """Configuration for data fetching and retry logic."""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    timeout_seconds: int = 30
    rate_limit_buffer: float = 1.2


@dataclass
class SignalGenerationConfig:
    """Configuration for trading signal generation."""
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    min_signal_strength: float = 0.6
    signal_cooldown_minutes: int = 15


@dataclass
class VolumeSettings:
    """Volume analysis settings."""
    min_volume_usd_24h: int = 1000000
    min_volume_rank: int = 200
    max_markets_per_exchange: int = 100


@dataclass
class JobSettings:
    """Job execution settings."""
    schedule_time: str = "09:00"
    retention_days: int = 30
    output_directory: str = "volume_data"


class ConfigManager:
    """
    Singleton configuration manager for the entire application.
    
    This ensures consistent configuration across all components:
    - CLI commands
    - Background jobs
    - Data fetchers
    - Signal generators
    - Risk managers
    """
    
    _instance: Optional['ConfigManager'] = None
    _config_data: Optional[Dict[str, Any]] = None
    _config_path: Optional[str] = None
    
    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        if self._config_data is None:
            self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None):
        """Load configuration from JSON file with environment variable override."""
        if config_path:
            self._config_path = config_path
        else:
            # Default config path
            current_dir = Path(__file__).parent.parent.parent
            self._config_path = str(current_dir / "config" / "exchanges_config.json")
        
        # Use secure config loader
        config_dir = str(Path(self._config_path).parent)
        secure_loader = SecureConfigLoader(config_dir)
        
        try:
            self._config_data = secure_loader.load_config(Path(self._config_path).name)
            logger.info(f"Configuration loaded from {self._config_path} with environment variable override")
        except Exception as e:
            logger.warning(f"Error loading config: {e}. Using defaults.")
            self._config_data = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file is missing or invalid."""
        return {
            "risk_management": {
                "default_budget": 50.0,
                "max_risk_per_trade": 0.002,
                "min_safety_ratio": 1.5,
                "default_leverage": 5,
                "max_position_percent": 0.1,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "max_positions": 5,
                "emergency_stop_loss": 10.0
            },
            "data_fetching": {
                "max_retries": 3,
                "retry_delay": 1.0,
                "backoff_multiplier": 2.0,
                "timeout_seconds": 30,
                "rate_limit_buffer": 1.2
            },
            "signal_generation": {
                "rsi_period": 14,
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "min_signal_strength": 0.6,
                "signal_cooldown_minutes": 15
            },
            "volume_settings": {
                "min_volume_usd_24h": 1000000,
                "min_volume_rank": 200,
                "max_markets_per_exchange": 100
            },
            "job_settings": {
                "schedule_time": "09:00",
                "retention_days": 30,
                "output_directory": "volume_data"
            }
        }
    
    def get_risk_management_config(self, budget_override: Optional[float] = None,
                                 risk_override: Optional[float] = None) -> RiskManagementConfig:
        """Get risk management configuration with optional overrides."""
        risk_data = self._config_data.get("risk_management", {})
        
        return RiskManagementConfig(
            max_budget=budget_override or risk_data.get("default_budget", 50.0),
            max_risk_per_trade=risk_override or risk_data.get("max_risk_per_trade", 0.002),
            min_safety_ratio=risk_data.get("min_safety_ratio", 1.5),
            default_leverage=risk_data.get("default_leverage", 5),
            max_position_percent=risk_data.get("max_position_percent", 0.1)
        )
    
    def get_data_fetching_config(self) -> DataFetchingConfig:
        """Get data fetching configuration."""
        data = self._config_data.get("data_fetching", {})
        
        return DataFetchingConfig(
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1.0),
            backoff_multiplier=data.get("backoff_multiplier", 2.0),
            timeout_seconds=data.get("timeout_seconds", 30),
            rate_limit_buffer=data.get("rate_limit_buffer", 1.2)
        )
    
    def get_signal_generation_config(self) -> SignalGenerationConfig:
        """Get signal generation configuration."""
        data = self._config_data.get("signal_generation", {})
        
        return SignalGenerationConfig(
            rsi_period=data.get("rsi_period", 14),
            rsi_oversold=data.get("rsi_oversold", 30),
            rsi_overbought=data.get("rsi_overbought", 70),
            macd_fast=data.get("macd_fast", 12),
            macd_slow=data.get("macd_slow", 26),
            macd_signal=data.get("macd_signal", 9),
            min_signal_strength=data.get("min_signal_strength", 0.6),
            signal_cooldown_minutes=data.get("signal_cooldown_minutes", 15)
        )
    
    def get_volume_settings(self) -> VolumeSettings:
        """Get volume analysis settings."""
        data = self._config_data.get("volume_settings", {})
        
        return VolumeSettings(
            min_volume_usd_24h=data.get("min_volume_usd_24h", 1000000),
            min_volume_rank=data.get("min_volume_rank", 200),
            max_markets_per_exchange=data.get("max_markets_per_exchange", 100)
        )
    
    def get_job_settings(self) -> JobSettings:
        """Get job execution settings."""
        data = self._config_data.get("job_settings", {})
        
        return JobSettings(
            schedule_time=data.get("schedule_time", "09:00"),
            retention_days=data.get("retention_days", 30),
            output_directory=data.get("output_directory", "volume_data")
        )
    
    def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Get configuration for a specific exchange."""
        return self._config_data.get(exchange_name, {})
    
    def get_all_exchange_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all exchange configurations."""
        exchanges = {}
        for key, value in self._config_data.items():
            if isinstance(value, dict) and value.get("enabled") is not None:
                exchanges[key] = value
        return exchanges
    
    def reload_config(self, config_path: Optional[str] = None):
        """Reload configuration from file."""
        self._config_data = None
        self._load_config(config_path)
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration data."""
        return self._config_data.copy()
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """Update configuration section and save to file."""
        if section not in self._config_data:
            self._config_data[section] = {}
        
        self._config_data[section].update(updates)
        
        # Save to file
        try:
            with open(self._config_path, 'w') as f:
                json.dump(self._config_data, f, indent=2)
            logger.info(f"Configuration updated and saved to {self._config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> 'ConfigManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._config_data = None


# Global function for easy access
def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get the global configuration manager instance."""
    return ConfigManager.get_instance(config_path)
