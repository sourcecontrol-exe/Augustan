"""
Live Signal Processor - Generates Trading Signals from Real-Time Data
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional
from loguru import logger
import ta

from ..core.position_state import EnhancedSignal, SignalType, PositionState, PositionManager
from ..core.config_manager import get_config_manager


class LiveSignalProcessor:
    """
    Processes live market data to generate trading signals.
    
    Features:
    - Real-time RSI and MACD signal generation
    - Position state awareness
    - Configurable parameters
    - Signal confidence scoring
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize signal processor."""
        self.config_manager = get_config_manager(config_path)
        self.signal_config = self.config_manager.get_signal_generation_config()
        self.position_manager = PositionManager()
        
        logger.info("LiveSignalProcessor initialized with real-time signal generation")
    
    def process_live_data(self, symbol: str, df: pd.DataFrame, current_price: float) -> List[EnhancedSignal]:
        """
        Process live data and generate signals.
        
        Args:
            symbol: Trading symbol
            df: Recent OHLCV data
            current_price: Current market price
            
        Returns:
            List of generated signals
        """
        if df.empty or len(df) < 50:  # Need sufficient data for indicators
            return []
        
        signals = []
        
        try:
            # Generate RSI signals
            rsi_signals = self._generate_rsi_signals(symbol, df, current_price)
            signals.extend(rsi_signals)
            
            # Generate MACD signals
            macd_signals = self._generate_macd_signals(symbol, df, current_price)
            signals.extend(macd_signals)
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
        
        return signals
    
    def _generate_rsi_signals(self, symbol: str, df: pd.DataFrame, current_price: float) -> List[EnhancedSignal]:
        """Generate RSI-based signals."""
        signals = []
        
        try:
            # Calculate RSI
            rsi = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=self.signal_config.rsi_period
            ).rsi()
            
            if rsi.empty or len(rsi) < 2:
                return signals
            
            current_rsi = rsi.iloc[-1]
            previous_rsi = rsi.iloc[-2]
            
            # RSI signal logic
            raw_signal = None
            confidence = 0.0
            reason = ""
            
            # Oversold condition (potential BUY)
            if previous_rsi <= self.signal_config.rsi_oversold and current_rsi > self.signal_config.rsi_oversold:
                raw_signal = "BUY"
                confidence = min(0.9, (self.signal_config.rsi_oversold - min(previous_rsi, current_rsi)) / 20 + 0.5)
                reason = f"RSI oversold recovery: {current_rsi:.1f} from {previous_rsi:.1f}"
            
            # Overbought condition (potential SELL)
            elif previous_rsi >= self.signal_config.rsi_overbought and current_rsi < self.signal_config.rsi_overbought:
                raw_signal = "SELL"
                confidence = min(0.9, (max(previous_rsi, current_rsi) - self.signal_config.rsi_overbought) / 20 + 0.5)
                reason = f"RSI overbought correction: {current_rsi:.1f} from {previous_rsi:.1f}"
            
            # Generate signal if criteria met
            if raw_signal and confidence >= self.signal_config.min_signal_strength:
                signal = self.position_manager.validate_and_create_signal(
                    symbol=symbol,
                    raw_signal_type=raw_signal,
                    price=current_price,
                    strategy="RSI",
                    confidence=confidence,
                    reason=reason,
                    rsi_value=current_rsi
                )
                
                if signal.is_valid():
                    signals.append(signal)
                    logger.info(f"🔄 RSI Signal: {symbol} {signal.signal_type.value} - "
                               f"RSI: {current_rsi:.1f}, Confidence: {confidence:.2f}")
        
        except Exception as e:
            logger.error(f"RSI signal generation error for {symbol}: {e}")
        
        return signals
    
    def _generate_macd_signals(self, symbol: str, df: pd.DataFrame, current_price: float) -> List[EnhancedSignal]:
        """Generate MACD-based signals."""
        signals = []
        
        try:
            # Calculate MACD
            macd_indicator = ta.trend.MACD(
                close=df['close'],
                window_fast=self.signal_config.macd_fast,
                window_slow=self.signal_config.macd_slow,
                window_sign=self.signal_config.macd_signal
            )
            
            macd_line = macd_indicator.macd()
            macd_signal_line = macd_indicator.macd_signal()
            macd_histogram = macd_indicator.macd_diff()
            
            if macd_line.empty or len(macd_line) < 2:
                return signals
            
            current_macd = macd_line.iloc[-1]
            current_signal = macd_signal_line.iloc[-1]
            current_histogram = macd_histogram.iloc[-1]
            
            previous_macd = macd_line.iloc[-2]
            previous_signal = macd_signal_line.iloc[-2]
            previous_histogram = macd_histogram.iloc[-2]
            
            # MACD signal logic
            raw_signal = None
            confidence = 0.0
            reason = ""
            
            # Bullish crossover (MACD crosses above signal line)
            if previous_macd <= previous_signal and current_macd > current_signal:
                raw_signal = "BUY"
                crossover_strength = abs(current_macd - current_signal)
                confidence = min(0.9, crossover_strength * 1000 + 0.5)  # Scale crossover strength
                reason = f"MACD bullish crossover: {current_macd:.4f} > {current_signal:.4f}"
            
            # Bearish crossover (MACD crosses below signal line)
            elif previous_macd >= previous_signal and current_macd < current_signal:
                raw_signal = "SELL"
                crossover_strength = abs(current_macd - current_signal)
                confidence = min(0.9, crossover_strength * 1000 + 0.5)
                reason = f"MACD bearish crossover: {current_macd:.4f} < {current_signal:.4f}"
            
            # Additional confirmation from histogram
            if raw_signal:
                # Increase confidence if histogram confirms the direction
                if raw_signal == "BUY" and current_histogram > previous_histogram:
                    confidence = min(0.95, confidence + 0.1)
                    reason += " (histogram confirming)"
                elif raw_signal == "SELL" and current_histogram < previous_histogram:
                    confidence = min(0.95, confidence + 0.1)
                    reason += " (histogram confirming)"
            
            # Generate signal if criteria met
            if raw_signal and confidence >= self.signal_config.min_signal_strength:
                signal = self.position_manager.validate_and_create_signal(
                    symbol=symbol,
                    raw_signal_type=raw_signal,
                    price=current_price,
                    strategy="MACD",
                    confidence=confidence,
                    reason=reason,
                    macd_value=current_macd,
                    macd_signal=current_signal
                )
                
                if signal.is_valid():
                    signals.append(signal)
                    logger.info(f"📊 MACD Signal: {symbol} {signal.signal_type.value} - "
                               f"MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, "
                               f"Confidence: {confidence:.2f}")
        
        except Exception as e:
            logger.error(f"MACD signal generation error for {symbol}: {e}")
        
        return signals
    
    def _calculate_volume_confirmation(self, df: pd.DataFrame) -> float:
        """Calculate volume confirmation factor."""
        if 'volume' not in df.columns or len(df) < 20:
            return 1.0
        
        try:
            # Compare recent volume to average
            recent_volume = df['volume'].iloc[-5:].mean()  # Last 5 candles
            avg_volume = df['volume'].iloc[-20:].mean()    # Last 20 candles
            
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Volume confirmation factor (1.0 = normal, >1.0 = high volume confirmation)
            return min(1.3, max(0.7, volume_ratio))
            
        except Exception:
            return 1.0
    
    def get_current_indicators(self, symbol: str, df: pd.DataFrame) -> dict:
        """Get current indicator values for a symbol."""
        if df.empty:
            return {}
        
        try:
            indicators = {}
            
            # RSI
            rsi = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=self.signal_config.rsi_period
            ).rsi()
            if not rsi.empty:
                indicators['rsi'] = rsi.iloc[-1]
            
            # MACD
            macd_indicator = ta.trend.MACD(
                close=df['close'],
                window_fast=self.signal_config.macd_fast,
                window_slow=self.signal_config.macd_slow,
                window_sign=self.signal_config.macd_signal
            )
            
            macd_line = macd_indicator.macd()
            macd_signal = macd_indicator.macd_signal()
            
            if not macd_line.empty:
                indicators['macd'] = macd_line.iloc[-1]
                indicators['macd_signal'] = macd_signal.iloc[-1]
                indicators['macd_histogram'] = macd_line.iloc[-1] - macd_signal.iloc[-1]
            
            # Volume
            if 'volume' in df.columns:
                indicators['volume'] = df['volume'].iloc[-1]
                indicators['volume_sma_20'] = df['volume'].rolling(20).mean().iloc[-1]
            
            # Price info
            indicators['current_price'] = df['close'].iloc[-1]
            indicators['price_change_1h'] = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) * 100 if len(df) >= 60 else 0
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}
