"""
Base strategy class for all trading strategies.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd

from ..core.models import MarketData, TradingSignal, StrategyType


class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, strategy_type: StrategyType):
        self.strategy_type = strategy_type
        self.name = strategy_type.value
    
    @abstractmethod
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """
        Generate trading signals based on market data.
        
        Args:
            market_data: List of MarketData objects
            
        Returns:
            List of TradingSignal objects
        """
        pass
    
    def prepare_dataframe(self, market_data: List[MarketData]) -> pd.DataFrame:
        """Convert market data to pandas DataFrame for analysis."""
        if not market_data:
            return pd.DataFrame()
        
        data = []
        for md in market_data:
            data.append({
                'timestamp': md.timestamp,
                'open': md.open,
                'high': md.high,
                'low': md.low,
                'close': md.close,
                'volume': md.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def validate_data(self, df: pd.DataFrame, min_periods: int = 20) -> bool:
        """Validate if we have enough data for the strategy."""
        if df.empty or len(df) < min_periods:
            return False
        return True
