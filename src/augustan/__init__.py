"""
Augustan - Advanced Algorithmic Trading Bot

A comprehensive trading system with backtesting, paper trading, and live trading capabilities.
"""

__version__ = "1.0.0"
__author__ = "Augustan Development Team"

# Core imports - lazy loading to avoid circular imports
def get_strategy():
    from .core.strategy.strategy import Strategy
    return Strategy

def get_risk_manager():
    from .core.risk_management.risk_manager import RiskManager
    return RiskManager

def get_data_service():
    from .data.services.data_service import DataService
    return DataService

def get_paper_trading_engine():
    from .trading.paper.paper_trader import PaperTradingEngine, PaperTradingConfig
    return PaperTradingEngine, PaperTradingConfig

# Direct imports for commonly used classes
from .utils.exceptions import *
from .utils.constants import *

__all__ = [
    'get_strategy',
    'get_risk_manager', 
    'get_data_service',
    'get_paper_trading_engine'
]