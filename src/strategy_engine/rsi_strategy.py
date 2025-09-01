"""
RSI (Relative Strength Index) Strategy Implementation.
"""
import pandas as pd
from typing import List
from datetime import datetime
import ta

from .base_strategy import BaseStrategy
from ..core.models import MarketData, TradingSignal, SignalType, StrategyType


class RSIStrategy(BaseStrategy):
    """RSI-based trading strategy."""
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        """
        Initialize RSI strategy.
        
        Args:
            period: RSI calculation period
            overbought: RSI overbought threshold (sell signal)
            oversold: RSI oversold threshold (buy signal)
        """
        super().__init__(StrategyType.RSI)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI values."""
        return ta.momentum.RSIIndicator(
            close=df['close'], 
            window=self.period
        ).rsi()
    
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """Generate RSI-based trading signals."""
        if not market_data:
            return []
        
        df = self.prepare_dataframe(market_data)
        
        if not self.validate_data(df, self.period + 5):
            return []
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df)
        
        signals = []
        symbol = market_data[0].symbol
        
        # Generate signals based on RSI levels
        for i in range(len(df)):
            if pd.isna(df['rsi'].iloc[i]):
                continue
                
            rsi_value = df['rsi'].iloc[i]
            price = df['close'].iloc[i]
            timestamp = df.index[i]
            
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # RSI oversold - potential buy signal
            if rsi_value <= self.oversold:
                signal_type = SignalType.BUY
                confidence = min(0.9, (self.oversold - rsi_value) / self.oversold + 0.6)
            
            # RSI overbought - potential sell signal
            elif rsi_value >= self.overbought:
                signal_type = SignalType.SELL
                confidence = min(0.9, (rsi_value - self.overbought) / (100 - self.overbought) + 0.6)
            
            # Only create signals for BUY/SELL (skip HOLD)
            if signal_type != SignalType.HOLD:
                signal = TradingSignal(
                    symbol=symbol,
                    strategy=self.strategy_type,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=price,
                    timestamp=timestamp,
                    metadata={
                        'rsi_value': rsi_value,
                        'overbought_threshold': self.overbought,
                        'oversold_threshold': self.oversold,
                        'period': self.period
                    }
                )
                signals.append(signal)
        
        # Return only the most recent signal if any
        if signals:
            return [signals[-1]]
        
        return []
