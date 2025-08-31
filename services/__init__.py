"""
Augustan Services Module

Contains all core trading services organized by functionality.
"""

from .data import DataService, DataLoader
from .trading import Strategy, TradingEngine
from .backtesting import BacktestEngine, AugustanBacktester
from .paper_trading import PaperTradingEngine
from .risk import RiskManager
from .adapters import BaseAdapter, CCXTAdapter, Pi42Adapter

__all__ = [
    'DataService', 'DataLoader',
    'Strategy', 'TradingEngine', 
    'BacktestEngine', 'AugustanBacktester',
    'PaperTradingEngine',
    'RiskManager',
    'BaseAdapter', 'CCXTAdapter', 'Pi42Adapter',
]
