"""
Paper Trading Module for Augustan Trading Bot

Provides virtual trading capabilities with real-time market data,
realistic order execution, and comprehensive performance tracking.
"""

from .paper_trader import PaperTradingEngine, PaperTradingConfig

__all__ = ['PaperTradingEngine', 'PaperTradingConfig']
