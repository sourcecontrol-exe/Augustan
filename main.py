# The main entry point to start the bot.# ==============================================================================
# File: risk_manager.py
# Description: Manages portfolio risk, position sizing, and stop-loss.
# ==============================================================================

import pandas as pd
import pandas_ta as ta
from config import ACTIVE_CONFIG

class RiskManager:
    def __init__(self):
        risk_settings = ACTIVE_CONFIG['risk']
        trading_settings = ACTIVE_CONFIG['trading']
        
        self.risk_per_trade = risk_settings.get('risk_per_trade', 0.01)
        self.risk_reward_ratio = risk_settings.get('risk_reward_ratio', 2.0)
        self.total_capital = trading_settings.get('total_capital', 1000)

    def calculate_trade_details(self, df, signal):
        """Calculates position size and stop-loss for a potential trade."""
        current_price = df['close'].iloc[-1]
        
        df.ta.atr(length=14, append=True)
        atr = df['ATR_14'].iloc[-1]
        
        if pd.isna(atr) or atr == 0:
            return None # Cannot calculate risk if ATR is invalid

        stop_loss_multiplier = 2.0

        if signal == 'BUY':
            stop_loss_price = current_price - (atr * stop_loss_multiplier)
        elif signal == 'SELL':
            stop_loss_price = current_price + (atr * stop_loss_multiplier)
        else:
            return None

        price_risk_per_unit = abs(current_price - stop_loss_price)
        if price_risk_per_unit == 0:
            return None

        risk_amount = self.total_capital * self.risk_per_trade
        position_size = risk_amount / price_risk_per_unit
        
        take_profit_price = current_price + (price_risk_per_unit * self.risk_reward_ratio) if signal == 'BUY' else current_price - (price_risk_per_unit * self.risk_reward_ratio)

        return {
            'position_size': position_size,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'entry_price': current_price
        }
