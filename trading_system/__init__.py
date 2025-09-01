"""
Augustan Trading System

The ultimate futures trading and position sizing tool with intelligent risk management.
"""

__version__ = "1.0.0"
__author__ = "Augustan Trading"
__email__ = "info@augustan.trading"

from .core.position_sizing import (
    PositionSizingCalculator,
    RiskManagementConfig,
    ExchangeLimits,
    PositionSizingResult,
    PositionSide,
)

from .core.futures_models import (
    FuturesMarketInfo,
    VolumeMetrics,
    ExchangeType,
    FuturesMarketRanking,
)

from .data_feeder.futures_data_feeder import FuturesDataFeeder
from .data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
from .jobs.daily_volume_job import DailyVolumeJob
from .jobs.enhanced_volume_job import EnhancedVolumeJob

__all__ = [
    # Position sizing
    "PositionSizingCalculator",
    "RiskManagementConfig", 
    "ExchangeLimits",
    "PositionSizingResult",
    "PositionSide",
    
    # Futures models
    "FuturesMarketInfo",
    "VolumeMetrics", 
    "ExchangeType",
    "FuturesMarketRanking",
    
    # Data feeders
    "FuturesDataFeeder",
    "ExchangeLimitsFetcher",
    
    # Jobs
    "DailyVolumeJob",
    "EnhancedVolumeJob",
]
