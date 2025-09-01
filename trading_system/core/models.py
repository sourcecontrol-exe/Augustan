"""
Core data models for the trading system.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class SignalType(Enum):
    """Types of trading signals."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategyType(Enum):
    """Types of trading strategies."""
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    SMA_CROSSOVER = "SMA_CROSSOVER"


@dataclass
class MarketData:
    """Market data structure."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }


@dataclass
class TradingSignal:
    """Trading signal structure."""
    symbol: str
    strategy: StrategyType
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'strategy': self.strategy.value,
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }


@dataclass
class MarketFeatures:
    """Market features for ML model."""
    symbol: str
    timestamp: datetime
    volatility: float
    trend_strength: float
    volume_trend: float
    price_momentum: float
    rsi_value: float
    macd_signal: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'volatility': self.volatility,
            'trend_strength': self.trend_strength,
            'volume_trend': self.volume_trend,
            'price_momentum': self.price_momentum,
            'rsi_value': self.rsi_value,
            'macd_signal': self.macd_signal
        }


@dataclass
class StrategyPerformance:
    """Strategy performance metrics."""
    strategy: StrategyType
    symbol: str
    accuracy: float
    profit_loss: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    timestamp: datetime
