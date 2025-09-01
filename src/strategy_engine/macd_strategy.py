"""
MACD (Moving Average Convergence Divergence) Strategy Implementation.
"""
import pandas as pd
from typing import List
from datetime import datetime
import ta

from .base_strategy import BaseStrategy
from ..core.models import MarketData, TradingSignal, SignalType, StrategyType


class MACDStrategy(BaseStrategy):
    """MACD-based trading strategy."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD strategy.
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
        """
        super().__init__(StrategyType.MACD)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate_macd(self, df: pd.DataFrame) -> tuple:
        """Calculate MACD, signal line, and histogram."""
        macd_indicator = ta.trend.MACD(
            close=df['close'],
            window_fast=self.fast_period,
            window_slow=self.slow_period,
            window_sign=self.signal_period
        )
        
        macd_line = macd_indicator.macd()
        signal_line = macd_indicator.macd_signal()
        histogram = macd_indicator.macd_diff()
        
        return macd_line, signal_line, histogram
    
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """Generate MACD-based trading signals."""
        if not market_data:
            return []
        
        df = self.prepare_dataframe(market_data)
        
        min_periods = self.slow_period + self.signal_period + 5
        if not self.validate_data(df, min_periods):
            return []
        
        # Calculate MACD
        macd_line, signal_line, histogram = self.calculate_macd(df)
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram
        
        signals = []
        symbol = market_data[0].symbol
        
        # Generate signals based on MACD crossovers
        for i in range(1, len(df)):
            if (pd.isna(df['macd'].iloc[i]) or 
                pd.isna(df['macd_signal'].iloc[i]) or
                pd.isna(df['macd'].iloc[i-1]) or 
                pd.isna(df['macd_signal'].iloc[i-1])):
                continue
            
            current_macd = df['macd'].iloc[i]
            current_signal = df['macd_signal'].iloc[i]
            prev_macd = df['macd'].iloc[i-1]
            prev_signal = df['macd_signal'].iloc[i-1]
            
            price = df['close'].iloc[i]
            timestamp = df.index[i]
            
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # Bullish crossover - MACD crosses above signal line
            if prev_macd <= prev_signal and current_macd > current_signal:
                signal_type = SignalType.BUY
                # Higher confidence if MACD is below zero (oversold)
                confidence = 0.7 if current_macd < 0 else 0.6
            
            # Bearish crossover - MACD crosses below signal line
            elif prev_macd >= prev_signal and current_macd < current_signal:
                signal_type = SignalType.SELL
                # Higher confidence if MACD is above zero (overbought)
                confidence = 0.7 if current_macd > 0 else 0.6
            
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
                        'macd_value': current_macd,
                        'signal_value': current_signal,
                        'histogram_value': df['macd_histogram'].iloc[i],
                        'fast_period': self.fast_period,
                        'slow_period': self.slow_period,
                        'signal_period': self.signal_period
                    }
                )
                signals.append(signal)
        
        # Return only the most recent signal if any
        if signals:
            return [signals[-1]]
        
        return []
