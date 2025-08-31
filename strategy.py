# ==============================================================================
# File: strategy.py
# Description: Contains the core trading logic for entry and exit signals.
# ==============================================================================
import pandas as pd
import pandas_ta as ta
from config import ACTIVE_CONFIG
from backtesting import Strategy as BacktestingStrategy
from backtesting.lib import crossover
import numpy as np

class Strategy:
    def __init__(self):
        # Load strategy-specific parameters from the config
        self.params = ACTIVE_CONFIG.get('strategy_parameters', {})
        self.rsi_length = self.params.get('rsi_length', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)

    def generate_signal(self, df: pd.DataFrame):
        """Analyzes market data and returns a signal: 'BUY', 'SELL', or 'HOLD'."""
        if df.empty:
            return 'HOLD'

        # --- Calculate Indicators using parameters from config ---
        df.ta.rsi(length=self.rsi_length, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)

        latest = df.iloc[-1]
        
        # --- Define Conditions ---
        macd_bullish = latest['MACD_12_26_9'] > latest['MACDs_12_26_9']
        macd_bearish = latest['MACD_12_26_9'] < latest['MACDs_12_26_9']
        rsi_column_name = f'RSI_{self.rsi_length}'

        # --- Generate Signal ---
        if latest[rsi_column_name] < self.rsi_oversold and macd_bullish:
            return 'BUY'
        elif latest[rsi_column_name] > self.rsi_overbought and macd_bearish:
            return 'SELL'
        else:
            return 'HOLD'


class BacktestableStrategy(BacktestingStrategy):
    """
    Backtestable strategy class that inherits from backtesting.py library
    Converts our trading logic to work with the backtesting framework
    """
    
    # Strategy parameters (can be optimized)
    rsi_length = 14
    rsi_oversold = 30
    rsi_overbought = 70
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    def init(self):
        """Initialize indicators for backtesting"""
        # Calculate RSI
        self.rsi = self.I(self._rsi, self.data.Close, self.rsi_length)
        
        # Calculate MACD
        macd_line, macd_signal, _ = self._macd(
            self.data.Close, self.macd_fast, self.macd_slow, self.macd_signal
        )
        self.macd = self.I(lambda: macd_line)
        self.macd_signal = self.I(lambda: macd_signal)
    
    def next(self):
        """Define trading logic for each bar"""
        # Get current values
        current_rsi = self.rsi[-1]
        current_macd = self.macd[-1]
        current_macd_signal = self.macd_signal[-1]
        
        # Define conditions
        macd_bullish = current_macd > current_macd_signal
        macd_bearish = current_macd < current_macd_signal
        
        # Entry conditions
        if (current_rsi < self.rsi_oversold and macd_bullish and not self.position):
            self.buy()
        
        # Exit conditions
        elif (current_rsi > self.rsi_overbought and macd_bearish and self.position):
            self.sell()
    
    @staticmethod
    def _rsi(close_prices, period=14):
        """Calculate RSI indicator"""
        delta = np.diff(close_prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=period).mean()
        avg_loss = pd.Series(loss).rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Pad with NaN for the first period values
        rsi = np.concatenate([np.full(period, np.nan), rsi[period:]])
        return rsi
    
    @staticmethod
    def _macd(close_prices, fast=12, slow=26, signal=9):
        """Calculate MACD indicator"""
        close_series = pd.Series(close_prices)
        
        # Calculate EMAs
        ema_fast = close_series.ewm(span=fast).mean()
        ema_slow = close_series.ewm(span=slow).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        macd_signal = macd_line.ewm(span=signal).mean()
        
        # Histogram
        macd_histogram = macd_line - macd_signal
        
        return macd_line.values, macd_signal.values, macd_histogram.values


class RSIMACDStrategy(BacktestableStrategy):
    """RSI + MACD strategy optimized for backtesting"""
    
    # Optimizable parameters
    rsi_length = 14
    rsi_oversold = 30
    rsi_overbought = 70
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # Risk management
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.06  # 6% take profit


class BollingerRSIStrategy(BacktestableStrategy):
    """Bollinger Bands + RSI strategy"""
    
    # Parameters
    bb_period = 20
    bb_std = 2
    rsi_length = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    def init(self):
        # Bollinger Bands
        self.bb_upper, self.bb_middle, self.bb_lower = self._bollinger_bands(
            self.data.Close, self.bb_period, self.bb_std
        )
        self.bb_upper = self.I(lambda: self.bb_upper)
        self.bb_middle = self.I(lambda: self.bb_middle)
        self.bb_lower = self.I(lambda: self.bb_lower)
        
        # RSI
        self.rsi = self.I(self._rsi, self.data.Close, self.rsi_length)
    
    def next(self):
        price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        
        # Buy when price touches lower BB and RSI is oversold
        if (price <= self.bb_lower[-1] and 
            current_rsi < self.rsi_oversold and 
            not self.position):
            self.buy()
        
        # Sell when price touches upper BB and RSI is overbought
        elif (price >= self.bb_upper[-1] and 
              current_rsi > self.rsi_overbought and 
              self.position):
            self.sell()
    
    @staticmethod
    def _bollinger_bands(close_prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        close_series = pd.Series(close_prices)
        
        # Simple moving average
        sma = close_series.rolling(window=period).mean()
        
        # Standard deviation
        std = close_series.rolling(window=period).std()
        
        # Bollinger Bands
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band.values, sma.values, lower_band.values


class MeanReversionStrategy(BacktestableStrategy):
    """Mean reversion strategy using RSI and price deviation"""
    
    # Parameters
    rsi_length = 14
    rsi_oversold = 20
    rsi_overbought = 80
    sma_period = 50
    deviation_threshold = 0.02  # 2% deviation from SMA
    
    def init(self):
        self.rsi = self.I(self._rsi, self.data.Close, self.rsi_length)
        self.sma = self.I(lambda: pd.Series(self.data.Close).rolling(self.sma_period).mean())
    
    def next(self):
        price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_sma = self.sma[-1]
        
        if np.isnan(current_sma):
            return
        
        # Calculate deviation from SMA
        deviation = (price - current_sma) / current_sma
        
        # Buy when price is below SMA and RSI is oversold
        if (deviation < -self.deviation_threshold and 
            current_rsi < self.rsi_oversold and 
            not self.position):
            self.buy()
        
        # Sell when price is above SMA and RSI is overbought
        elif (deviation > self.deviation_threshold and 
              current_rsi > self.rsi_overbought and 
              self.position):
            self.sell()