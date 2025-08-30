# ==============================================================================
# File: strategy.py
# Description: Contains the core trading logic for entry and exit signals.
# ==============================================================================
import pandas as pd
import pandas_ta as ta
from ...config.config import ACTIVE_CONFIG

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