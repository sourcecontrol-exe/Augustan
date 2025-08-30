"""
Paper Trading Module for Augustan Trading Bot

Provides virtual trading capabilities with real-time market data,
realistic order execution, and comprehensive performance tracking.
"""

from .paper_trader import (
    PaperTradingEngine,
    PaperTradingConfig,
    VirtualPortfolio,
    VirtualOrder,
    VirtualPosition,
    OrderType,
    OrderStatus,
    OrderSide
)

__all__ = [
    'PaperTradingEngine',
    'PaperTradingConfig', 
    'VirtualPortfolio',
    'VirtualOrder',
    'VirtualPosition',
    'OrderType',
    'OrderStatus',
    'OrderSide'
]
