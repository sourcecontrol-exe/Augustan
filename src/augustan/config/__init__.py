"""
Configuration package for Augustan Trading Bot

This package contains configuration files and management utilities for different
environments (testing, live trading, etc.).
"""

from .config_manager import (
    ConfigManager,
    config_manager,
    get_trading_config,
    get_scanner_config,
    get_risk_config,
    get_exchanges_config,
    get_active_config
)

__all__ = [
    'ConfigManager',
    'config_manager',
    'get_trading_config',
    'get_scanner_config',
    'get_risk_config',
    'get_exchanges_config',
    'get_active_config'
]
