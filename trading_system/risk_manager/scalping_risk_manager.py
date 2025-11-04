"""
Enhanced Risk Manager for Scalping Trading
Implements tighter stop mechanisms, fixed R:R ratios, and trailing stops.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from loguru import logger
import ta

from ..core.config_manager import ConfigManager
from ..core.position_state import EnhancedSignal, PositionState, SignalType
from ..core.position_sizing import ExchangeLimits
from ..core.futures_models import ExchangeType
from ..data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher


@dataclass
class ScalpingRiskConfig:
    """Configuration for scalping risk management."""
    # Position sizing
    max_position_size_percent: float = 0.02  # 2% of account per trade
    max_total_exposure_percent: float = 0.10  # 10% total exposure
    
    # Stop loss settings
    atr_period: int = 14
    atr_multiplier: float = 1.5  # Stop loss = ATR * multiplier
    max_stop_loss_percent: float = 0.005  # 0.5% max stop loss
    
    # Take profit settings
    risk_reward_ratio: float = 1.5  # Minimum R:R ratio
    max_take_profit_percent: float = 0.015  # 1.5% max take profit
    
    # Trailing stop settings
    enable_trailing_stop: bool = True
    trailing_stop_atr_multiplier: float = 1.0  # Trailing stop = ATR * multiplier
    trailing_stop_activation_percent: float = 0.003  # Activate after 0.3% profit
    
    # Risk limits
    max_daily_loss_percent: float = 0.05  # 5% max daily loss
    max_consecutive_losses: int = 3
    cooldown_period_minutes: int = 5  # Cooldown after losses
    
    # Volume and volatility filters
    min_volume_spike: float = 1.5  # Minimum volume spike
    max_volatility_percent: float = 0.02  # 2% max volatility (ATR/price)
    
    # Time-based filters
    max_hold_time_minutes: int = 30  # Maximum position hold time
    avoid_news_minutes: int = 5  # Avoid trading near news events


@dataclass
class ScalpingRiskResult:
    """Result of scalping risk calculation."""
    # Input
    signal: EnhancedSignal
    current_price: float
    account_balance: float
    market_data: pd.DataFrame
    
    # Risk calculations
    atr_value: float
    calculated_stop_loss: float
    calculated_take_profit: float
    position_size: float
    position_value: float
    risk_amount: float
    
    # Risk metrics
    risk_percentage: float
    reward_risk_ratio: float
    max_loss_percentage: float
    
    # Safety checks
    is_safe_to_trade: bool
    safety_warnings: List[str]
    rejection_reasons: List[str]
    
    # Trailing stop
    trailing_stop_price: Optional[float] = None
    trailing_stop_active: bool = False
    
    # Time limits
    max_hold_until: Optional[datetime] = None


class ScalpingRiskManager:
    """
    Enhanced Risk Manager for Scalping Trading
    
    Features:
    - ATR-based dynamic stop losses
    - Fixed risk-reward ratios
    - Trailing stop logic
    - Volume and volatility filters
    - Time-based position limits
    - Consecutive loss protection
    """
    
    def __init__(self, config: ScalpingRiskConfig = None, config_path: Optional[str] = None,
                 config_manager: Optional[ConfigManager] = None):
        """
        Initialize scalping risk manager.
        
        Args:
            config: Scalping risk config
            config_path: Path to config file (deprecated, use config_manager)
            config_manager: Configuration manager instance
        """
        self.config = config or ScalpingRiskConfig()
        
        # Use dependency injection if provided
        if config_manager is None:
            if config_path:
                self.config_manager = ConfigManager.create(config_path)
            else:
                self.config_manager = ConfigManager.create_for_testing()
        else:
            self.config_manager = config_manager
        
        self.limits_fetcher = ExchangeLimitsFetcher()
        
        # Position tracking
        self.active_positions: Dict[str, Dict] = {}
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.last_loss_time: Optional[datetime] = None
        
        # Event subscriptions removed - deprecated global event system
        
        logger.info("Scalping Risk Manager initialized")
    
    def handle_order_filled(self, symbol: str, side: str, quantity: float, price: float):
        """
        Handle order filled events for position tracking.
        
        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Fill price
        """
        # Update position tracking
        if symbol not in self.active_positions:
            from datetime import datetime
            self.active_positions[symbol] = {
                'side': side,
                'quantity': quantity,
                'entry_price': price,
                'entry_time': datetime.now(),
                'stop_loss': None,
                'take_profit': None,
                'trailing_stop': None
            }
        else:
            # Update existing position
            pos = self.active_positions[symbol]
            if side != pos['side']:
                # Closing position
                pnl = self._calculate_pnl(pos, price, quantity)
                self.daily_pnl += pnl
                
                if pnl < 0:
                    self.consecutive_losses += 1
                    from datetime import datetime
                    self.last_loss_time = datetime.now()
                else:
                    self.consecutive_losses = 0
                
                # Remove position
                del self.active_positions[symbol]
                
                logger.info(f"Position closed for {symbol}: PnL ${pnl:.2f}")
    
    def calculate_risk(self, signal: EnhancedSignal, current_price: float, 
                      account_balance: float, market_data: pd.DataFrame) -> ScalpingRiskResult:
        """
        Calculate risk parameters for scalping trade.
        
        Args:
            signal: Trading signal
            current_price: Current market price
            account_balance: Account balance
            market_data: Recent market data for calculations
            
        Returns:
            ScalpingRiskResult with all risk calculations
        """
        warnings = []
        rejections = []
        
        # Check cooldown period
        if self._is_in_cooldown():
            rejections.append("In cooldown period after consecutive losses")
        
        # Check daily loss limit
        if self.daily_pnl <= -self.config.max_daily_loss_percent * account_balance:
            rejections.append("Daily loss limit exceeded")
        
        # Check consecutive losses
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            rejections.append("Maximum consecutive losses reached")
        
        # Calculate ATR
        atr_value = self._calculate_atr(market_data)
        
        # Calculate stop loss
        side = 'buy' if signal.signal_type in [SignalType.BUY_OPEN, SignalType.BUY_CLOSE] else 'sell'
        stop_loss = self._calculate_stop_loss(current_price, atr_value, side)
        
        # Check stop loss limits
        stop_loss_percent = abs(current_price - stop_loss) / current_price
        if stop_loss_percent > self.config.max_stop_loss_percent:
            stop_loss = self._adjust_stop_loss(current_price, side)
            warnings.append(f"Stop loss adjusted to max limit: {self.config.max_stop_loss_percent*100:.1f}%")
        
        # Calculate take profit
        take_profit = self._calculate_take_profit(current_price, stop_loss, side)
        
        # Check take profit limits
        take_profit_percent = abs(take_profit - current_price) / current_price
        if take_profit_percent > self.config.max_take_profit_percent:
            take_profit = self._adjust_take_profit(current_price, side)
            warnings.append(f"Take profit adjusted to max limit: {self.config.max_take_profit_percent*100:.1f}%")
        
        # Calculate position size
        risk_amount = abs(current_price - stop_loss)
        max_risk_amount = self.config.max_position_size_percent * account_balance
        position_size = min(max_risk_amount / risk_amount, 
                          self._get_max_position_size(current_price, account_balance))
        
        position_value = position_size * current_price
        
        # Check total exposure
        total_exposure = self._calculate_total_exposure() + position_value
        if total_exposure > self.config.max_total_exposure_percent * account_balance:
            position_size = (self.config.max_total_exposure_percent * account_balance - 
                           self._calculate_total_exposure()) / current_price
            position_value = position_size * current_price
            warnings.append("Position size reduced due to total exposure limit")
        
        # Calculate risk metrics
        risk_percentage = (risk_amount * position_size) / account_balance
        reward_risk_ratio = abs(take_profit - current_price) / risk_amount
        
        # Check volume and volatility
        if len(market_data) > 20:
            volume_spike = market_data['volume'].iloc[-1] / market_data['volume'].rolling(20).mean().iloc[-1]
            if volume_spike < self.config.min_volume_spike:
                rejections.append("Insufficient volume spike")
            
            volatility = atr_value / current_price
            if volatility > self.config.max_volatility_percent:
                rejections.append("Excessive volatility")
        
        # Calculate trailing stop
        trailing_stop_price = None
        trailing_stop_active = False
        if self.config.enable_trailing_stop:
            trailing_stop_price = self._calculate_trailing_stop(current_price, atr_value, side)
            trailing_stop_active = True
        
        # Calculate max hold time
        max_hold_until = datetime.now() + timedelta(minutes=self.config.max_hold_time_minutes)
        
        # Determine if safe to trade
        is_safe = len(rejections) == 0 and position_size > 0
        
        return ScalpingRiskResult(
            signal=signal,
            current_price=current_price,
            account_balance=account_balance,
            market_data=market_data,
            atr_value=atr_value,
            calculated_stop_loss=stop_loss,
            calculated_take_profit=take_profit,
            position_size=position_size,
            position_value=position_value,
            risk_amount=risk_amount * position_size,
            risk_percentage=risk_percentage,
            reward_risk_ratio=reward_risk_ratio,
            max_loss_percentage=self.config.max_daily_loss_percent,
            is_safe_to_trade=is_safe,
            safety_warnings=warnings,
            rejection_reasons=rejections,
            trailing_stop_price=trailing_stop_price,
            trailing_stop_active=trailing_stop_active,
            max_hold_until=max_hold_until
        )
    
    def _calculate_atr(self, market_data: pd.DataFrame) -> float:
        """Calculate Average True Range."""
        if len(market_data) < self.config.atr_period:
            return market_data['close'].std() * 0.02  # Fallback
        
        atr = ta.volatility.AverageTrueRange(
            market_data['high'], 
            market_data['low'], 
            market_data['close'], 
            window=self.config.atr_period
        ).average_true_range()
        
        return atr.iloc[-1] if not atr.empty else market_data['close'].std() * 0.02
    
    def _calculate_stop_loss(self, price: float, atr: float, side: str) -> float:
        """Calculate ATR-based stop loss."""
        stop_distance = atr * self.config.atr_multiplier
        
        if side == 'buy':
            return price - stop_distance
        else:
            return price + stop_distance
    
    def _calculate_take_profit(self, price: float, stop_loss: float, side: str) -> float:
        """Calculate take profit based on risk-reward ratio."""
        risk = abs(price - stop_loss)
        reward = risk * self.config.risk_reward_ratio
        
        if side == 'buy':
            return price + reward
        else:
            return price - reward
    
    def _adjust_stop_loss(self, price: float, side: str) -> float:
        """Adjust stop loss to maximum allowed percentage."""
        max_stop_distance = price * self.config.max_stop_loss_percent
        
        if side == 'buy':
            return price - max_stop_distance
        else:
            return price + max_stop_distance
    
    def _adjust_take_profit(self, price: float, side: str) -> float:
        """Adjust take profit to maximum allowed percentage."""
        max_take_distance = price * self.config.max_take_profit_percent
        
        if side == 'buy':
            return price + max_take_distance
        else:
            return price - max_take_distance
    
    def _get_max_position_size(self, price: float, account_balance: float) -> float:
        """Get maximum position size based on account balance."""
        max_position_value = self.config.max_position_size_percent * account_balance
        return max_position_value / price
    
    def _calculate_total_exposure(self) -> float:
        """Calculate total current exposure."""
        total = 0.0
        for symbol, position in self.active_positions.items():
            total += position['quantity'] * position['entry_price']
        return total
    
    def _calculate_trailing_stop(self, price: float, atr: float, side: str) -> float:
        """Calculate trailing stop price."""
        trailing_distance = atr * self.config.trailing_stop_atr_multiplier
        
        if side == 'buy':
            return price - trailing_distance
        else:
            return price + trailing_distance
    
    def _is_in_cooldown(self) -> bool:
        """Check if currently in cooldown period."""
        if self.last_loss_time is None:
            return False
        
        cooldown_end = self.last_loss_time + timedelta(minutes=self.config.cooldown_period_minutes)
        return datetime.now() < cooldown_end
    
    def _calculate_pnl(self, position: Dict, exit_price: float, exit_quantity: float) -> float:
        """Calculate P&L for a position."""
        if position['side'] == 'buy':
            return (exit_price - position['entry_price']) * exit_quantity
        else:
            return (position['entry_price'] - exit_price) * exit_quantity
    
    def update_trailing_stops(self, current_prices: Dict[str, float]) -> Dict[str, Dict]:
        """
        Update trailing stops for active positions.
        
        Args:
            current_prices: Current prices for all symbols
            
        Returns:
            Dictionary of updated stop orders
        """
        updated_stops = {}
        
        for symbol, position in self.active_positions.items():
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            side = position['side']
            entry_price = position['entry_price']
            
            # Calculate profit percentage
            if side == 'buy':
                profit_percent = (current_price - entry_price) / entry_price
            else:
                profit_percent = (entry_price - current_price) / entry_price
            
            # Activate trailing stop if profit threshold reached
            if profit_percent >= self.config.trailing_stop_activation_percent:
                # Calculate new trailing stop
                # Get recent market data for ATR calculation
                # This would need to be passed in or fetched
                atr = self._estimate_atr(symbol)  # Simplified for now
                new_trailing_stop = self._calculate_trailing_stop(current_price, atr, side)
                
                # Update trailing stop if it's better (closer to current price)
                if position['trailing_stop'] is None or self._is_better_trailing_stop(
                    new_trailing_stop, position['trailing_stop'], side, current_price
                ):
                    position['trailing_stop'] = new_trailing_stop
                    updated_stops[symbol] = {
                        'stop_price': new_trailing_stop,
                        'side': 'sell' if side == 'buy' else 'buy',
                        'quantity': position['quantity']
                    }
        
        return updated_stops
    
    def _estimate_atr(self, symbol: str) -> float:
        """Estimate ATR for a symbol (simplified)."""
        # In a real implementation, this would fetch recent market data
        # For now, return a conservative estimate
        return 0.001  # 0.1% of price
    
    def _is_better_trailing_stop(self, new_stop: float, current_stop: float, side: str, current_price: float) -> bool:
        """Check if new trailing stop is better than current one."""
        if current_stop is None:
            return True
        
        if side == 'buy':
            # For long positions, trailing stop should be higher (closer to current price)
            return new_stop > current_stop
        else:
            # For short positions, trailing stop should be lower (closer to current price)
            return new_stop < current_stop
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk summary."""
        return {
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'active_positions': len(self.active_positions),
            'total_exposure': self._calculate_total_exposure(),
            'in_cooldown': self._is_in_cooldown(),
            'last_loss_time': self.last_loss_time
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of new trading day)."""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_loss_time = None
        logger.info("Daily risk statistics reset")
