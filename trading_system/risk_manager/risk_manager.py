"""
Core Risk Manager - The Heart of Capital Preservation

This is the most critical component of the trading system.
It ensures proper position sizing and risk management for every trade.
"""
import math
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from loguru import logger

from ..core.config_manager import get_config_manager
from ..core.position_state import EnhancedSignal, PositionState
from ..core.position_sizing import ExchangeLimits
from ..data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher


@dataclass
class RiskCalculationResult:
    """Result of risk calculation with all relevant metrics."""
    # Input parameters
    signal: EnhancedSignal
    current_price: float
    account_balance: float
    
    # Core calculations
    risk_amount: float  # Dollar amount at risk
    position_size: float  # Number of units to trade
    position_value: float  # Total position value in USD
    required_margin: float  # Required margin for leveraged position
    
    # Risk metrics
    risk_percentage: float  # Percentage of account at risk
    reward_risk_ratio: float  # Potential reward vs risk ratio
    max_loss_percentage: float  # Maximum loss as % of account
    
    # Exchange compliance
    meets_min_notional: bool
    meets_min_quantity: bool
    adjusted_for_limits: bool
    
    # Safety checks
    is_safe_to_trade: bool
    safety_warnings: list
    rejection_reason: Optional[str] = None
    
    # Liquidation analysis
    liquidation_price: Optional[float] = None
    liquidation_distance: Optional[float] = None  # Distance to liquidation in %
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            'symbol': self.signal.symbol,
            'signal_type': self.signal.signal_type.value,
            'current_price': self.current_price,
            'account_balance': self.account_balance,
            'risk_amount': self.risk_amount,
            'position_size': self.position_size,
            'position_value': self.position_value,
            'required_margin': self.required_margin,
            'risk_percentage': self.risk_percentage,
            'reward_risk_ratio': self.reward_risk_ratio,
            'max_loss_percentage': self.max_loss_percentage,
            'meets_min_notional': self.meets_min_notional,
            'meets_min_quantity': self.meets_min_quantity,
            'adjusted_for_limits': self.adjusted_for_limits,
            'is_safe_to_trade': self.is_safe_to_trade,
            'safety_warnings': self.safety_warnings,
            'rejection_reason': self.rejection_reason,
            'liquidation_price': self.liquidation_price,
            'liquidation_distance': self.liquidation_distance,
            'timestamp': datetime.now().isoformat()
        }


class RiskManager:
    """
    Core Risk Manager - Capital Preservation Engine
    
    This class implements the fundamental risk management formula:
    position_size = risk_amount / price_difference
    
    Key responsibilities:
    1. Calculate proper position sizes based on account balance and risk tolerance
    2. Ensure compliance with exchange minimum/maximum limits
    3. Validate trades against multiple safety checks
    4. Prevent catastrophic losses through position limits
    5. Calculate liquidation risks for leveraged positions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Risk Manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_manager = get_config_manager(config_path)
        self.risk_config = self.config_manager.get_risk_management_config()
        self.limits_fetcher = ExchangeLimitsFetcher()
        
        # Risk limits
        self.max_risk_per_trade = self.risk_config.max_risk_per_trade  # e.g., 0.002 = 0.2%
        self.max_position_size_percent = self.risk_config.max_position_percent  # e.g., 0.1 = 10%
        self.emergency_stop_loss_percent = 0.1  # 10% account emergency stop
        
        logger.info(f"RiskManager initialized - Max risk per trade: {self.max_risk_per_trade:.3%}")
    
    def calculate_position_size(self, 
                               signal: EnhancedSignal,
                               current_price: float,
                               account_balance: float,
                               leverage: int = 1,
                               exchange_limits: Optional[ExchangeLimits] = None) -> RiskCalculationResult:
        """
        Calculate position size based on risk management principles.
        
        This is the CORE METHOD of capital preservation.
        
        Args:
            signal: Trading signal with entry/exit prices
            current_price: Current market price
            account_balance: Total account balance in USD
            leverage: Leverage to use (1 = no leverage)
            exchange_limits: Exchange trading limits
            
        Returns:
            RiskCalculationResult with all calculations and safety checks
        """
        logger.info(f"Calculating position size for {signal.symbol} - "
                   f"Signal: {signal.signal_type.value}, Price: ${current_price:.4f}")
        
        # Initialize result
        result = RiskCalculationResult(
            signal=signal,
            current_price=current_price,
            account_balance=account_balance,
            risk_amount=0.0,
            position_size=0.0,
            position_value=0.0,
            required_margin=0.0,
            risk_percentage=0.0,
            reward_risk_ratio=0.0,
            max_loss_percentage=0.0,
            meets_min_notional=False,
            meets_min_quantity=False,
            adjusted_for_limits=False,
            is_safe_to_trade=False,
            safety_warnings=[]
        )
        
        # Get exchange limits if not provided
        if exchange_limits is None:
            exchange_limits = self.limits_fetcher.fetch_symbol_limits('binance', signal.symbol)
            if exchange_limits is None:
                result.rejection_reason = "Could not fetch exchange limits"
                return result
        
        # Step 1: Calculate base risk amount
        result.risk_amount = account_balance * self.max_risk_per_trade
        result.risk_percentage = self.max_risk_per_trade * 100
        
        # Step 2: Determine stop loss price from signal
        stop_loss_price = self._get_stop_loss_price(signal, current_price)
        if stop_loss_price is None:
            result.rejection_reason = "Cannot determine stop loss price"
            return result
        
        # Step 3: Calculate price difference (the key to position sizing)
        price_diff = abs(current_price - stop_loss_price)
        if price_diff <= 0:
            result.rejection_reason = "Invalid price difference - entry equals stop loss"
            return result
        
        # Step 4: CORE FORMULA - Calculate position size
        result.position_size = result.risk_amount / price_diff
        result.position_value = result.position_size * current_price
        result.required_margin = result.position_value / leverage
        
        logger.debug(f"Core calculation: risk_amount={result.risk_amount:.2f}, "
                    f"price_diff={price_diff:.4f}, position_size={result.position_size:.6f}")
        
        # Step 5: Check against exchange limits and adjust
        result = self._apply_exchange_limits(result, exchange_limits, current_price)
        
        # Step 6: Apply position size limits
        result = self._apply_position_limits(result, account_balance)
        
        # Step 7: Calculate reward/risk ratio
        result = self._calculate_reward_risk_ratio(result, signal, current_price)
        
        # Step 8: Liquidation analysis for leveraged positions
        if leverage > 1:
            result = self._calculate_liquidation_risk(result, exchange_limits, leverage)
        
        # Step 9: Final safety checks
        result = self._perform_safety_checks(result, account_balance)
        
        # Log final result
        if result.is_safe_to_trade:
            logger.info(f"✅ APPROVED: {signal.symbol} position size {result.position_size:.6f} "
                       f"(${result.position_value:.2f}) - Risk: ${result.risk_amount:.2f} "
                       f"({result.risk_percentage:.2f}%)")
        else:
            logger.warning(f"❌ REJECTED: {signal.symbol} - {result.rejection_reason}")
        
        return result
    
    def _get_stop_loss_price(self, signal: EnhancedSignal, current_price: float) -> Optional[float]:
        """Extract or calculate stop loss price from signal."""
        # For now, use a default 2% stop loss
        # In a full implementation, this would come from the signal or strategy
        stop_loss_percent = 0.02  # 2%
        
        if signal.signal_type.value.startswith('BUY'):
            # Long position - stop loss below entry
            return current_price * (1 - stop_loss_percent)
        elif signal.signal_type.value.startswith('SELL'):
            # Short position - stop loss above entry  
            return current_price * (1 + stop_loss_percent)
        
        return None
    
    def _apply_exchange_limits(self, result: RiskCalculationResult, 
                              limits: ExchangeLimits, current_price: float) -> RiskCalculationResult:
        """Apply exchange minimum/maximum limits and adjust position size."""
        original_size = result.position_size
        
        # Check minimum quantity
        if result.position_size < limits.min_qty:
            result.position_size = limits.min_qty
            result.adjusted_for_limits = True
            result.safety_warnings.append(f"Position size increased to meet minimum quantity: {limits.min_qty}")
        
        # Check minimum notional value
        min_notional_required = max(limits.min_notional, limits.min_qty * current_price)
        if result.position_value < min_notional_required:
            required_size = min_notional_required / current_price
            if required_size > result.position_size:
                result.position_size = required_size
                result.adjusted_for_limits = True
                result.safety_warnings.append(f"Position size increased to meet minimum notional: ${min_notional_required:.2f}")
        
        # Recalculate values after adjustment
        result.position_value = result.position_size * current_price
        result.required_margin = result.position_value / (result.signal.confidence if hasattr(result.signal, 'leverage') else 1)
        
        # Update compliance flags
        result.meets_min_quantity = result.position_size >= limits.min_qty
        result.meets_min_notional = result.position_value >= limits.min_notional
        
        # Recalculate actual risk after adjustment
        if result.adjusted_for_limits:
            stop_loss_price = self._get_stop_loss_price(result.signal, current_price)
            if stop_loss_price:
                price_diff = abs(current_price - stop_loss_price)
                result.risk_amount = result.position_size * price_diff
                result.risk_percentage = (result.risk_amount / result.account_balance) * 100
                
                if result.risk_percentage > self.max_risk_per_trade * 100 * 2:  # Allow 2x over for minimum compliance
                    result.safety_warnings.append(f"Risk increased to {result.risk_percentage:.2f}% due to exchange minimums")
        
        return result
    
    def _apply_position_limits(self, result: RiskCalculationResult, account_balance: float) -> RiskCalculationResult:
        """Apply maximum position size limits."""
        max_position_value = account_balance * self.max_position_size_percent
        
        if result.position_value > max_position_value:
            # Reduce position size to maximum allowed
            old_size = result.position_size
            result.position_size = max_position_value / result.current_price
            result.position_value = max_position_value
            result.adjusted_for_limits = True
            
            result.safety_warnings.append(f"Position size reduced from {old_size:.6f} to {result.position_size:.6f} "
                                        f"due to maximum position limit ({self.max_position_size_percent:.1%})")
            
            # Recalculate risk
            stop_loss_price = self._get_stop_loss_price(result.signal, result.current_price)
            if stop_loss_price:
                price_diff = abs(result.current_price - stop_loss_price)
                result.risk_amount = result.position_size * price_diff
                result.risk_percentage = (result.risk_amount / account_balance) * 100
        
        return result
    
    def _calculate_reward_risk_ratio(self, result: RiskCalculationResult, 
                                   signal: EnhancedSignal, current_price: float) -> RiskCalculationResult:
        """Calculate reward to risk ratio."""
        # For now, assume 2:1 reward/risk ratio target
        # In full implementation, this would come from signal's take profit level
        target_profit_percent = 0.04  # 4% target profit
        
        if signal.signal_type.value.startswith('BUY'):
            target_price = current_price * (1 + target_profit_percent)
        else:
            target_price = current_price * (1 - target_profit_percent)
        
        potential_profit = abs(target_price - current_price) * result.position_size
        result.reward_risk_ratio = potential_profit / result.risk_amount if result.risk_amount > 0 else 0
        
        return result
    
    def _calculate_liquidation_risk(self, result: RiskCalculationResult, 
                                  limits: ExchangeLimits, leverage: int) -> RiskCalculationResult:
        """Calculate liquidation price and risk for leveraged positions."""
        maintenance_margin_rate = limits.maintenance_margin_rate
        
        if result.signal.signal_type.value.startswith('BUY'):
            # Long position liquidation price
            result.liquidation_price = result.current_price * (1 - (1/leverage) + maintenance_margin_rate)
        else:
            # Short position liquidation price  
            result.liquidation_price = result.current_price * (1 + (1/leverage) - maintenance_margin_rate)
        
        # Calculate distance to liquidation
        if result.liquidation_price:
            result.liquidation_distance = abs(result.current_price - result.liquidation_price) / result.current_price * 100
            
            # Warning if liquidation is too close
            if result.liquidation_distance < 5.0:  # Less than 5% to liquidation
                result.safety_warnings.append(f"Liquidation price too close: {result.liquidation_distance:.1f}% away")
        
        return result
    
    def _perform_safety_checks(self, result: RiskCalculationResult, account_balance: float) -> RiskCalculationResult:
        """Perform final safety checks to determine if trade is safe."""
        
        # Check 1: Risk percentage within limits
        if result.risk_percentage > self.max_risk_per_trade * 100 * 3:  # Allow 3x over for extreme cases
            result.rejection_reason = f"Risk too high: {result.risk_percentage:.2f}% > {self.max_risk_per_trade * 100 * 3:.2f}%"
            return result
        
        # Check 2: Position value reasonable
        if result.position_value > account_balance * 0.5:  # Position > 50% of account
            result.rejection_reason = f"Position too large: ${result.position_value:.2f} > 50% of account"
            return result
        
        # Check 3: Required margin available
        if result.required_margin > account_balance * 0.8:  # Margin > 80% of account
            result.rejection_reason = f"Insufficient margin: ${result.required_margin:.2f} > 80% of account"
            return result
        
        # Check 4: Exchange compliance
        if not result.meets_min_notional or not result.meets_min_quantity:
            result.rejection_reason = "Does not meet exchange minimum requirements"
            return result
        
        # Check 5: Liquidation distance (for leveraged positions)
        if result.liquidation_distance is not None and result.liquidation_distance < 2.0:
            result.rejection_reason = f"Liquidation too close: {result.liquidation_distance:.1f}%"
            return result
        
        # Check 6: Reward/risk ratio
        if result.reward_risk_ratio < 1.0:
            result.safety_warnings.append(f"Low reward/risk ratio: {result.reward_risk_ratio:.2f}")
        
        # All checks passed
        result.is_safe_to_trade = True
        result.max_loss_percentage = (result.risk_amount / account_balance) * 100
        
        return result
    
    def validate_account_balance(self, account_balance: float) -> Tuple[bool, Optional[str]]:
        """Validate that account balance is sufficient for trading."""
        min_balance = 10.0  # Minimum $10 to trade
        
        if account_balance < min_balance:
            return False, f"Account balance too low: ${account_balance:.2f} < ${min_balance:.2f}"
        
        return True, None
    
    def calculate_max_position_size(self, symbol: str, account_balance: float, 
                                  current_price: float) -> float:
        """Calculate maximum position size for a symbol given account balance."""
        max_position_value = account_balance * self.max_position_size_percent
        return max_position_value / current_price
    
    def get_risk_summary(self, account_balance: float) -> Dict[str, Any]:
        """Get risk management summary for account."""
        return {
            'account_balance': account_balance,
            'max_risk_per_trade_usd': account_balance * self.max_risk_per_trade,
            'max_risk_per_trade_percent': self.max_risk_per_trade * 100,
            'max_position_value': account_balance * self.max_position_size_percent,
            'max_position_percent': self.max_position_size_percent * 100,
            'emergency_stop_loss_level': account_balance * (1 - self.emergency_stop_loss_percent),
            'risk_config': self.risk_config.to_dict()
        }
