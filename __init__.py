"""
Augustan - Advanced Algorithmic Trading Bot

A comprehensive trading system with backtesting, paper trading, and live trading capabilities.
"""

__version__ = "1.0.0"
__author__ = "Augustan Development Team"

# Core services
from .services.data import DataService, DataLoader
from .services.trading import Strategy, RSIMACDStrategy, BollingerRSIStrategy, MeanReversionStrategy
from .services.backtesting import AugustanBacktester
from .services.paper_trading import PaperTradingEngine
from .services.risk import RiskManager
from .services.adapters import BaseAdapter, CCXTAdapter, Pi42Adapter

# Core utilities
from .core.config import ConfigManager, load_config
from .core.exceptions import (
    AugustanError, DataFetchError, ValidationError, 
    RiskManagementError, TradingError
)

__all__ = [
    # Services
    'DataService', 'DataLoader',
    'Strategy', 'RSIMACDStrategy', 'BollingerRSIStrategy', 'MeanReversionStrategy',
    'AugustanBacktester',
    'PaperTradingEngine',
    'RiskManager',
    'BaseAdapter', 'CCXTAdapter', 'Pi42Adapter',
    
    # Core
    'ConfigManager', 'load_config',
    'AugustanError', 'DataFetchError', 'ValidationError',
    'RiskManagementError', 'TradingError',
]
