"""
Futures-specific data models for the trading system.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class ExchangeType(Enum):
    """Supported futures exchanges."""
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    BITGET = "bitget"
    GATE = "gate"


@dataclass
class FuturesMarketInfo:
    """Futures market information."""
    symbol: str
    exchange: ExchangeType
    base_currency: str
    quote_currency: str
    contract_type: str  # perpetual, quarterly, etc.
    contract_size: float
    min_order_size: float
    tick_size: float
    is_active: bool
    listing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None


@dataclass
class VolumeMetrics:
    """Volume metrics for a futures market."""
    symbol: str
    exchange: ExchangeType
    timestamp: datetime
    volume_24h: float  # 24h volume in base currency
    volume_usd_24h: float  # 24h volume in USD
    volume_7d_avg: float  # 7-day average volume
    volume_30d_avg: float  # 30-day average volume
    price: float  # Current price
    price_change_24h: float  # 24h price change percentage
    open_interest: Optional[float] = None  # Open interest if available
    funding_rate: Optional[float] = None  # Funding rate for perpetuals
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange.value,
            'timestamp': self.timestamp.isoformat(),
            'volume_24h': self.volume_24h,
            'volume_usd_24h': self.volume_usd_24h,
            'volume_7d_avg': self.volume_7d_avg,
            'volume_30d_avg': self.volume_30d_avg,
            'price': self.price,
            'price_change_24h': self.price_change_24h,
            'open_interest': self.open_interest,
            'funding_rate': self.funding_rate
        }


@dataclass
class FuturesMarketRanking:
    """Market ranking based on volume and other metrics."""
    symbol: str
    exchange: ExchangeType
    rank: int
    volume_rank: int
    volume_usd_24h: float
    volume_score: float  # Normalized volume score (0-100)
    volatility_score: float  # Price volatility score
    liquidity_score: float  # Based on spreads and depth
    overall_score: float  # Combined score
    is_recommended: bool  # Whether to include in trading
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange.value,
            'rank': self.rank,
            'volume_rank': self.volume_rank,
            'volume_usd_24h': self.volume_usd_24h,
            'volume_score': self.volume_score,
            'volatility_score': self.volatility_score,
            'liquidity_score': self.liquidity_score,
            'overall_score': self.overall_score,
            'is_recommended': self.is_recommended
        }


@dataclass
class FuturesPosition:
    """Futures position information."""
    symbol: str
    exchange: ExchangeType
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    margin_used: float
    leverage: float
    liquidation_price: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange.value,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'unrealized_pnl': self.unrealized_pnl,
            'margin_used': self.margin_used,
            'leverage': self.leverage,
            'liquidation_price': self.liquidation_price
        }
