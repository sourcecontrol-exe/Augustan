"""
Backtesting Service Module

Comprehensive backtesting engine with performance analytics.
"""

from .backtester import AugustanBacktester, BacktestConfig
from .indicators import *
from .performance_metrics import PerformanceAnalyzer
from .strategy_framework import *

__all__ = [
    'AugustanBacktester', 'BacktestConfig',
    'PerformanceAnalyzer'
]
