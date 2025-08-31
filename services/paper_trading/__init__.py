"""
Paper Trading Service Module

Virtual trading simulation with real market data.
"""

from .paper_trader import PaperTradingEngine, VirtualPortfolio, VirtualOrder
from .paper_backtest_bridge import PaperBacktestBridge

__all__ = [
    'PaperTradingEngine', 'VirtualPortfolio', 'VirtualOrder',
    'PaperBacktestBridge'
]
