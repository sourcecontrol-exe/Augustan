"""
Scalping Strategies for High-Frequency Trading
Implements EMA Crossover, Bollinger Bands, and VWAP strategies optimized for scalping.
"""
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
import ta

from ..core.models import MarketData, TradingSignal, StrategyType
from ..core.position_state import EnhancedSignal, SignalType
from .base_strategy import BaseStrategy


@dataclass
class ScalpingConfig:
    """Configuration for scalping strategies."""
    # EMA Crossover
    ema_fast: int = 9
    ema_slow: int = 21
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    bb_squeeze_threshold: float = 0.1  # Minimum squeeze threshold
    
    # VWAP
    vwap_period: int = 20
    
    # Risk Management
    atr_period: int = 14
    atr_multiplier: float = 1.5  # Stop loss = ATR * multiplier
    risk_reward_ratio: float = 1.5  # Minimum R:R ratio
    
    # Signal Filters
    min_volume_spike: float = 1.5  # Minimum volume spike for signals
    min_price_movement: float = 0.001  # Minimum price movement (0.1%)
    
    # Timeframes
    primary_timeframe: str = "1m"
    confirmation_timeframes: List[str] = None  # ["3m", "5m"]
    
    def __post_init__(self):
        if self.confirmation_timeframes is None:
            self.confirmation_timeframes = ["3m", "5m"]


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy for Scalping
    
    Signals:
    - BUY: Fast EMA crosses above Slow EMA with volume confirmation
    - SELL: Fast EMA crosses below Slow EMA with volume confirmation
    """
    
    def __init__(self, config: ScalpingConfig = None):
        """Initialize EMA Crossover strategy."""
        BaseStrategy.__init__(self, StrategyType.SCALPING)
        self.config = config or ScalpingConfig()
        self.name = "EMA_Crossover_Scalping"
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        
        # Event subscriptions removed - deprecated global event system
        self.event_callbacks = []
        
        logger.info(f"EMA Crossover Strategy initialized: {self.config.ema_fast}EMA vs {self.config.ema_slow}EMA")
    
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """Generate signals from market data (legacy method)."""
        # This method is for compatibility with BaseStrategy
        # The real signal generation happens in _generate_signals via events
        return []
    
    async def handle_candle_closed(self, event: CandleClosedEvent):
        """Handle candle closed events."""
        await self._process_candle(event.symbol, event.candle_data, event.timeframe)
    
    async def _process_candle(self, symbol: str, candle_data: MarketData, timeframe: str):
        """Process new candle data."""
        if timeframe != self.config.primary_timeframe:
            return
        
        # Update symbol data
        if symbol not in self.symbol_data:
            self.symbol_data[symbol] = pd.DataFrame()
        
        # Add new candle
        new_row = pd.DataFrame([{
            'timestamp': candle_data.timestamp,
            'open': candle_data.open,
            'high': candle_data.high,
            'low': candle_data.low,
            'close': candle_data.close,
            'volume': candle_data.volume
        }])
        
        self.symbol_data[symbol] = pd.concat([self.symbol_data[symbol], new_row], ignore_index=True)
        
        # Keep only recent data (last 100 candles)
        if len(self.symbol_data[symbol]) > 100:
            self.symbol_data[symbol] = self.symbol_data[symbol].tail(100)
        
        # Generate signals if we have enough data
        if len(self.symbol_data[symbol]) >= self.config.ema_slow + 5:
            await self._generate_signals(symbol)
    
    async def _generate_signals(self, symbol: str):
        """Generate trading signals."""
        df = self.symbol_data[symbol].copy()
        
        # Calculate EMAs
        df['ema_fast'] = ta.trend.EMAIndicator(df['close'], window=self.config.ema_fast).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(df['close'], window=self.config.ema_slow).ema_indicator()
        
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Check for crossover
        current_fast_above_slow = current['ema_fast'] > current['ema_slow']
        previous_fast_above_slow = previous['ema_fast'] > previous['ema_slow']
        
        # Volume confirmation
        volume_spike = current['volume'] / current['volume_ma'] if current['volume_ma'] > 0 else 1
        
        # Generate signals
        if not previous_fast_above_slow and current_fast_above_slow and volume_spike >= self.config.min_volume_spike:
            # Bullish crossover
            signal = EnhancedSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                entry_price=current['close'],
                stop_loss=self._calculate_stop_loss(df, current['close'], 'long'),
                take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'long'), 'long'),
                confidence=self._calculate_confidence(df, 'bullish'),
                timestamp=datetime.now(),
                strategy_name=self.name,
                metadata={
                    'ema_fast': current['ema_fast'],
                    'ema_slow': current['ema_slow'],
                    'volume_spike': volume_spike,
                    'timeframe': self.config.primary_timeframe
                }
            )
            
            await self._emit_signal(signal)
            
        elif previous_fast_above_slow and not current_fast_above_slow and volume_spike >= self.config.min_volume_spike:
            # Bearish crossover
            signal = EnhancedSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                entry_price=current['close'],
                stop_loss=self._calculate_stop_loss(df, current['close'], 'short'),
                take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'short'), 'short'),
                confidence=self._calculate_confidence(df, 'bearish'),
                timestamp=datetime.now(),
                strategy_name=self.name,
                metadata={
                    'ema_fast': current['ema_fast'],
                    'ema_slow': current['ema_slow'],
                    'volume_spike': volume_spike,
                    'timeframe': self.config.primary_timeframe
                }
            )
            
            await self._emit_signal(signal)
    
    def _calculate_stop_loss(self, df: pd.DataFrame, entry_price: float, side: str) -> float:
        """Calculate ATR-based stop loss."""
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=self.config.atr_period).average_true_range().iloc[-1]
        
        if side == 'long':
            return entry_price - (atr * self.config.atr_multiplier)
        else:
            return entry_price + (atr * self.config.atr_multiplier)
    
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, side: str) -> float:
        """Calculate take profit based on risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = risk * self.config.risk_reward_ratio
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward
    
    def _calculate_confidence(self, df: pd.DataFrame, signal_type: str) -> float:
        """Calculate signal confidence."""
        # Base confidence
        confidence = 0.5
        
        # Volume confirmation
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 2.0:
            confidence += 0.2
        elif volume_ratio > 1.5:
            confidence += 0.1
        
        # Price momentum
        price_change = abs(df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        if price_change > 0.01:  # 1% movement
            confidence += 0.1
        
        # EMA separation
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]
        ema_separation = abs(ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0
        
        if ema_separation > 0.005:  # 0.5% separation
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _emit_signal(self, signal: EnhancedSignal):
        """Emit signal event to callbacks (no longer using global event bus)."""
        signal_data = {
            'symbol': signal.symbol,
            'signal_data': signal.to_dict(),
            'strategy_name': signal.strategy_name,
            'confidence': signal.confidence
        }
        
        # Notify all callbacks
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(signal_data)
                else:
                    callback(signal_data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
        
        logger.info(f"EMA Crossover signal generated: {signal.signal_type.value} {signal.symbol} @ {signal.entry_price}")
    
    def add_event_callback(self, callback):
        """Add event callback for signal generation."""
        self.event_callbacks.append(callback)


class BollingerBandStrategy(BaseStrategy):
    """
    Bollinger Band Squeeze/Breakout Strategy for Scalping
    
    Signals:
    - BUY: Price breaks above upper band after squeeze with volume
    - SELL: Price breaks below lower band after squeeze with volume
    """
    
    def __init__(self, config: ScalpingConfig = None):
        """Initialize Bollinger Band strategy."""
        BaseStrategy.__init__(self, StrategyType.SCALPING)
        self.config = config or ScalpingConfig()
        self.name = "Bollinger_Band_Scalping"
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        self.squeeze_state: Dict[str, bool] = {}  # Track squeeze state per symbol
        
        # Event subscriptions removed - deprecated global event system
        self.event_callbacks = []
        
        logger.info(f"Bollinger Band Strategy initialized: {self.config.bb_period} period, {self.config.bb_std} std")
    
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """Generate signals from market data (legacy method)."""
        # This method is for compatibility with BaseStrategy
        # The real signal generation happens in _generate_signals via events
        return []
    
    async def handle_candle_closed(self, event: CandleClosedEvent):
        """Handle candle closed events."""
        await self._process_candle(event.symbol, event.candle_data, event.timeframe)
    
    async def _process_candle(self, symbol: str, candle_data: MarketData, timeframe: str):
        """Process new candle data."""
        if timeframe != self.config.primary_timeframe:
            return
        
        # Update symbol data
        if symbol not in self.symbol_data:
            self.symbol_data[symbol] = pd.DataFrame()
            self.squeeze_state[symbol] = False
        
        # Add new candle
        new_row = pd.DataFrame([{
            'timestamp': candle_data.timestamp,
            'open': candle_data.open,
            'high': candle_data.high,
            'low': candle_data.low,
            'close': candle_data.close,
            'volume': candle_data.volume
        }])
        
        self.symbol_data[symbol] = pd.concat([self.symbol_data[symbol], new_row], ignore_index=True)
        
        # Keep only recent data
        if len(self.symbol_data[symbol]) > 100:
            self.symbol_data[symbol] = self.symbol_data[symbol].tail(100)
        
        # Generate signals if we have enough data
        if len(self.symbol_data[symbol]) >= self.config.bb_period + 5:
            await self._generate_signals(symbol)
    
    async def _generate_signals(self, symbol: str):
        """Generate trading signals."""
        df = self.symbol_data[symbol].copy()
        
        # Calculate Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=self.config.bb_period, window_dev=self.config.bb_std)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Get current values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Check for squeeze (low volatility)
        current_squeeze = current['bb_width'] < self.config.bb_squeeze_threshold
        previous_squeeze = previous['bb_width'] < self.config.bb_squeeze_threshold
        
        # Update squeeze state
        if current_squeeze and not self.squeeze_state[symbol]:
            self.squeeze_state[symbol] = True
            logger.info(f"Bollinger Band squeeze detected for {symbol}")
        
        # Volume confirmation
        volume_spike = current['volume'] / current['volume_ma'] if current['volume_ma'] > 0 else 1
        
        # Generate signals
        if self.squeeze_state[symbol] and volume_spike >= self.config.min_volume_spike:
            if current['close'] > current['bb_upper'] and previous['close'] <= previous['bb_upper']:
                # Bullish breakout
                signal = EnhancedSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    entry_price=current['close'],
                    stop_loss=self._calculate_stop_loss(df, current['close'], 'long'),
                    take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'long'), 'long'),
                    confidence=self._calculate_confidence(df, 'bullish'),
                    timestamp=datetime.now(),
                    strategy_name=self.name,
                    metadata={
                        'bb_upper': current['bb_upper'],
                        'bb_lower': current['bb_lower'],
                        'bb_width': current['bb_width'],
                        'volume_spike': volume_spike,
                        'timeframe': self.config.primary_timeframe
                    }
                )
                
                await self._emit_signal(signal)
                self.squeeze_state[symbol] = False  # Reset squeeze state
                
            elif current['close'] < current['bb_lower'] and previous['close'] >= previous['bb_lower']:
                # Bearish breakout
                signal = EnhancedSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    entry_price=current['close'],
                    stop_loss=self._calculate_stop_loss(df, current['close'], 'short'),
                    take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'short'), 'short'),
                    confidence=self._calculate_confidence(df, 'bearish'),
                    timestamp=datetime.now(),
                    strategy_name=self.name,
                    metadata={
                        'bb_upper': current['bb_upper'],
                        'bb_lower': current['bb_lower'],
                        'bb_width': current['bb_width'],
                        'volume_spike': volume_spike,
                        'timeframe': self.config.primary_timeframe
                    }
                )
                
                await self._emit_signal(signal)
                self.squeeze_state[symbol] = False  # Reset squeeze state
    
    def _calculate_stop_loss(self, df: pd.DataFrame, entry_price: float, side: str) -> float:
        """Calculate ATR-based stop loss."""
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=self.config.atr_period).average_true_range().iloc[-1]
        
        if side == 'long':
            return entry_price - (atr * self.config.atr_multiplier)
        else:
            return entry_price + (atr * self.config.atr_multiplier)
    
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, side: str) -> float:
        """Calculate take profit based on risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = risk * self.config.risk_reward_ratio
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward
    
    def _calculate_confidence(self, df: pd.DataFrame, signal_type: str) -> float:
        """Calculate signal confidence."""
        confidence = 0.6  # Higher base confidence for breakout signals
        
        # Volume confirmation
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 2.0:
            confidence += 0.2
        elif volume_ratio > 1.5:
            confidence += 0.1
        
        # Band width (volatility)
        bb_width = df['bb_width'].iloc[-1]
        if bb_width < 0.05:  # Very tight bands
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _emit_signal(self, signal: EnhancedSignal):
        """Emit signal event to callbacks (no longer using global event bus)."""
        signal_data = {
            'symbol': signal.symbol,
            'signal_data': signal.to_dict(),
            'strategy_name': signal.strategy_name,
            'confidence': signal.confidence
        }
        
        # Notify all callbacks
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(signal_data)
                else:
                    callback(signal_data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
        
        logger.info(f"Bollinger Band signal generated: {signal.signal_type.value} {signal.symbol} @ {signal.entry_price}")
    
    def add_event_callback(self, callback):
        """Add event callback for signal generation."""
        self.event_callbacks.append(callback)


class VWAPReversionStrategy(BaseStrategy):
    """
    VWAP Reversion Strategy for Scalping
    
    Signals:
    - BUY: Price dips below VWAP and shows rejection (wick below VWAP, close above)
    - SELL: Price spikes above VWAP and shows rejection (wick above VWAP, close below)
    """
    
    def __init__(self, config: ScalpingConfig = None):
        """Initialize VWAP Reversion strategy."""
        BaseStrategy.__init__(self, StrategyType.SCALPING)
        self.config = config or ScalpingConfig()
        self.name = "VWAP_Reversion_Scalping"
        self.symbol_data: Dict[str, pd.DataFrame] = {}
        
        # Event subscriptions removed - deprecated global event system
        self.event_callbacks = []
        
        logger.info(f"VWAP Reversion Strategy initialized: {self.config.vwap_period} period")
    
    def generate_signals(self, market_data: List[MarketData]) -> List[TradingSignal]:
        """Generate signals from market data (legacy method)."""
        # This method is for compatibility with BaseStrategy
        # The real signal generation happens in _generate_signals via events
        return []
    
    async def handle_candle_closed(self, event: CandleClosedEvent):
        """Handle candle closed events."""
        await self._process_candle(event.symbol, event.candle_data, event.timeframe)
    
    async def _process_candle(self, symbol: str, candle_data: MarketData, timeframe: str):
        """Process new candle data."""
        if timeframe != self.config.primary_timeframe:
            return
        
        # Update symbol data
        if symbol not in self.symbol_data:
            self.symbol_data[symbol] = pd.DataFrame()
        
        # Add new candle
        new_row = pd.DataFrame([{
            'timestamp': candle_data.timestamp,
            'open': candle_data.open,
            'high': candle_data.high,
            'low': candle_data.low,
            'close': candle_data.close,
            'volume': candle_data.volume
        }])
        
        self.symbol_data[symbol] = pd.concat([self.symbol_data[symbol], new_row], ignore_index=True)
        
        # Keep only recent data
        if len(self.symbol_data[symbol]) > 100:
            self.symbol_data[symbol] = self.symbol_data[symbol].tail(100)
        
        # Generate signals if we have enough data
        if len(self.symbol_data[symbol]) >= self.config.vwap_period + 5:
            await self._generate_signals(symbol)
    
    async def _generate_signals(self, symbol: str):
        """Generate trading signals."""
        df = self.symbol_data[symbol].copy()
        
        # Calculate VWAP
        df['vwap'] = (df['close'] * df['volume']).rolling(window=self.config.vwap_period).sum() / df['volume'].rolling(window=self.config.vwap_period).sum()
        
        # Calculate volume moving average
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        # Get current values
        current = df.iloc[-1]
        
        # Volume confirmation
        volume_spike = current['volume'] / current['volume_ma'] if current['volume_ma'] > 0 else 1
        
        # Check for VWAP rejection patterns
        if volume_spike >= self.config.min_volume_spike:
            # Bullish rejection: Low below VWAP, close above VWAP
            if current['low'] < current['vwap'] and current['close'] > current['vwap']:
                # Check if there's a significant rejection (wick)
                rejection_size = current['close'] - current['low']
                vwap_distance = current['close'] - current['vwap']
                
                if rejection_size > vwap_distance * 2:  # Strong rejection
                    signal = EnhancedSignal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        entry_price=current['close'],
                        stop_loss=self._calculate_stop_loss(df, current['close'], 'long'),
                        take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'long'), 'long'),
                        confidence=self._calculate_confidence(df, 'bullish'),
                        timestamp=datetime.now(),
                        strategy_name=self.name,
                        metadata={
                            'vwap': current['vwap'],
                            'rejection_size': rejection_size,
                            'volume_spike': volume_spike,
                            'timeframe': self.config.primary_timeframe
                        }
                    )
                    
                    await self._emit_signal(signal)
            
            # Bearish rejection: High above VWAP, close below VWAP
            elif current['high'] > current['vwap'] and current['close'] < current['vwap']:
                # Check if there's a significant rejection (wick)
                rejection_size = current['high'] - current['close']
                vwap_distance = current['vwap'] - current['close']
                
                if rejection_size > vwap_distance * 2:  # Strong rejection
                    signal = EnhancedSignal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        entry_price=current['close'],
                        stop_loss=self._calculate_stop_loss(df, current['close'], 'short'),
                        take_profit=self._calculate_take_profit(current['close'], self._calculate_stop_loss(df, current['close'], 'short'), 'short'),
                        confidence=self._calculate_confidence(df, 'bearish'),
                        timestamp=datetime.now(),
                        strategy_name=self.name,
                        metadata={
                            'vwap': current['vwap'],
                            'rejection_size': rejection_size,
                            'volume_spike': volume_spike,
                            'timeframe': self.config.primary_timeframe
                        }
                    )
                    
                    await self._emit_signal(signal)
    
    def _calculate_stop_loss(self, df: pd.DataFrame, entry_price: float, side: str) -> float:
        """Calculate ATR-based stop loss."""
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=self.config.atr_period).average_true_range().iloc[-1]
        
        if side == 'long':
            return entry_price - (atr * self.config.atr_multiplier)
        else:
            return entry_price + (atr * self.config.atr_multiplier)
    
    def _calculate_take_profit(self, entry_price: float, stop_loss: float, side: str) -> float:
        """Calculate take profit based on risk-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = risk * self.config.risk_reward_ratio
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward
    
    def _calculate_confidence(self, df: pd.DataFrame, signal_type: str) -> float:
        """Calculate signal confidence."""
        confidence = 0.7  # High base confidence for VWAP reversion
        
        # Volume confirmation
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 2.0:
            confidence += 0.2
        elif volume_ratio > 1.5:
            confidence += 0.1
        
        # VWAP distance
        current_price = df['close'].iloc[-1]
        vwap = df['vwap'].iloc[-1]
        vwap_distance = abs(current_price - vwap) / vwap if vwap > 0 else 0
        
        if vwap_distance > 0.01:  # 1% distance from VWAP
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def _emit_signal(self, signal: EnhancedSignal):
        """Emit signal event to callbacks (no longer using global event bus)."""
        signal_data = {
            'symbol': signal.symbol,
            'signal_data': signal.to_dict(),
            'strategy_name': signal.strategy_name,
            'confidence': signal.confidence
        }
        
        # Notify all callbacks
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(signal_data)
                else:
                    callback(signal_data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
        
        logger.info(f"VWAP Reversion signal generated: {signal.signal_type.value} {signal.symbol} @ {signal.entry_price}")
    
    def add_event_callback(self, callback):
        """Add event callback for signal generation."""
        self.event_callbacks.append(callback)


class ScalpingStrategyManager:
    """
    Manages multiple scalping strategies and coordinates their execution.
    """
    
    def __init__(self, config: ScalpingConfig = None):
        """Initialize strategy manager."""
        self.config = config or ScalpingConfig()
        self.strategies = {}
        
        # Initialize strategies
        self.strategies['ema_crossover'] = EMACrossoverStrategy(self.config)
        self.strategies['bollinger_bands'] = BollingerBandStrategy(self.config)
        self.strategies['vwap_reversion'] = VWAPReversionStrategy(self.config)
        
        logger.info(f"Scalping Strategy Manager initialized with {len(self.strategies)} strategies")
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get strategy by name."""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """Get all strategies."""
        return self.strategies.copy()
    
    def cleanup(self):
        """Cleanup all strategies."""
        for strategy in self.strategies.values():
            if hasattr(strategy, 'cleanup'):
                strategy.cleanup()
        logger.info("Scalping Strategy Manager cleaned up")
