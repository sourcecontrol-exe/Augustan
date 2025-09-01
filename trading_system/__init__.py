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

from .core.config_manager import ConfigManager, get_config_manager
from .core.position_state import PositionState, EnhancedSignal, PositionManager

from .data_feeder.futures_data_feeder import FuturesDataFeeder
from .data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
from .data_feeder.realtime_feeder import BinanceWebsocketFeeder, MultiExchangeRealtimeFeeder

from .risk_manager.risk_manager import RiskManager, RiskCalculationResult
from .risk_manager.portfolio_manager import PortfolioManager, PortfolioMetrics

from .live_trading.live_engine import LiveTradingEngine
from .live_trading.signal_processor import LiveSignalProcessor

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
    
    # Core management
    "ConfigManager",
    "get_config_manager",
    "PositionState",
    "EnhancedSignal", 
    "PositionManager",
    
    # Data feeders
    "FuturesDataFeeder",
    "ExchangeLimitsFetcher",
    "BinanceWebsocketFeeder",
    "MultiExchangeRealtimeFeeder",
    
    # Risk management
    "RiskManager",
    "RiskCalculationResult",
    "PortfolioManager",
    "PortfolioMetrics",
    
    # Live trading
    "LiveTradingEngine",
    "LiveSignalProcessor",
    
    # Jobs
    "DailyVolumeJob",
    "EnhancedVolumeJob",
]
