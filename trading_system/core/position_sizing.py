"""
Position Sizing and Risk Management Models
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import math


class PositionSide(Enum):
    """Position side for futures trading."""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class ExchangeLimits:
    """Exchange trading limits for a symbol."""
    symbol: str
    exchange: str
    min_notional: float  # Minimum order value in USDT
    min_qty: float  # Minimum quantity
    max_qty: float  # Maximum quantity
    qty_step: float  # Quantity step size
    price_step: float  # Price step size
    max_leverage: int  # Maximum leverage allowed
    maintenance_margin_rate: float  # Maintenance margin rate (e.g., 0.005 = 0.5%)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'min_notional': self.min_notional,
            'min_qty': self.min_qty,
            'max_qty': self.max_qty,
            'qty_step': self.qty_step,
            'price_step': self.price_step,
            'max_leverage': self.max_leverage,
            'maintenance_margin_rate': self.maintenance_margin_rate
        }


@dataclass
class PositionSizingInput:
    """Input parameters for position sizing calculation."""
    symbol: str
    entry_price: float
    stop_loss_price: float
    take_profit_price: Optional[float]
    user_budget: float  # Total available budget in USDT
    risk_per_trade_percent: float  # Risk percentage (e.g., 0.002 = 0.2%)
    leverage: int  # Desired leverage (1-100x)
    position_side: PositionSide
    exchange_limits: ExchangeLimits


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation."""
    symbol: str
    is_tradeable: bool
    rejection_reason: Optional[str]
    
    # Position details
    position_size_qty: float  # Quantity to trade
    position_size_usdt: float  # Position size in USDT
    required_margin: float  # Required margin in USDT
    
    # Risk metrics
    risk_amount: float  # Maximum loss in USDT
    risk_percent: float  # Risk as percentage of budget
    
    # Liquidation analysis
    liquidation_price: float
    liquidation_buffer: float  # Distance from entry to liquidation
    risk_buffer: float  # Distance from entry to stop loss
    safety_ratio: float  # liquidation_buffer / risk_buffer
    
    # Exchange compliance
    meets_min_notional: bool
    meets_min_qty: bool
    min_feasible_notional: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'is_tradeable': self.is_tradeable,
            'rejection_reason': self.rejection_reason,
            'position_size_qty': self.position_size_qty,
            'position_size_usdt': self.position_size_usdt,
            'required_margin': self.required_margin,
            'risk_amount': self.risk_amount,
            'risk_percent': self.risk_percent,
            'liquidation_price': self.liquidation_price,
            'liquidation_buffer': self.liquidation_buffer,
            'risk_buffer': self.risk_buffer,
            'safety_ratio': self.safety_ratio,
            'meets_min_notional': self.meets_min_notional,
            'meets_min_qty': self.meets_min_qty,
            'min_feasible_notional': self.min_feasible_notional
        }


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    max_budget: float = 50.0  # Maximum budget in USDT
    max_risk_per_trade: float = 0.002  # 0.2% maximum risk per trade
    min_safety_ratio: float = 1.5  # Minimum liquidation safety ratio
    default_leverage: int = 5  # Default leverage for calculations
    max_position_percent: float = 0.1  # Maximum 10% of budget per position
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_budget': self.max_budget,
            'max_risk_per_trade': self.max_risk_per_trade,
            'min_safety_ratio': self.min_safety_ratio,
            'default_leverage': self.default_leverage,
            'max_position_percent': self.max_position_percent
        }


class PositionSizingCalculator:
    """Calculator for position sizing and risk management."""
    
    def __init__(self, risk_config: RiskManagementConfig = None):
        """Initialize position sizing calculator."""
        self.risk_config = risk_config or RiskManagementConfig()
    
    def calculate_min_feasible_notional(self, limits: ExchangeLimits, current_price: float) -> float:
        """Calculate minimum feasible notional value for a symbol."""
        return max(
            limits.min_notional,
            limits.min_qty * current_price
        )
    
    def calculate_liquidation_price(self, entry_price: float, leverage: int, 
                                  maintenance_margin_rate: float, position_side: PositionSide) -> float:
        """
        Calculate liquidation price for a position.
        
        For LONG: liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)
        For SHORT: liquidation_price = entry_price * (1 + (1/leverage) - maintenance_margin_rate)
        """
        leverage_factor = 1.0 / leverage
        
        if position_side == PositionSide.LONG:
            liquidation_price = entry_price * (1 - leverage_factor + maintenance_margin_rate)
        else:  # SHORT
            liquidation_price = entry_price * (1 + leverage_factor - maintenance_margin_rate)
        
        return liquidation_price
    
    def calculate_position_size_by_risk(self, entry_price: float, stop_loss_price: float,
                                      risk_amount: float) -> float:
        """Calculate position size based on risk amount."""
        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0:
            return 0
        
        return risk_amount / price_diff
    
    def calculate_required_margin(self, position_size_usdt: float, leverage: int) -> float:
        """Calculate required margin for a position."""
        return position_size_usdt / leverage
    
    def round_to_step_size(self, value: float, step_size: float) -> float:
        """Round value to exchange step size."""
        if step_size == 0:
            return value
        
        return math.floor(value / step_size) * step_size
    
    def analyze_position_sizing(self, inputs: PositionSizingInput) -> PositionSizingResult:
        """
        Comprehensive position sizing analysis.
        
        Returns a PositionSizingResult with all calculations and safety checks.
        """
        symbol = inputs.symbol
        entry_price = inputs.entry_price
        stop_loss_price = inputs.stop_loss_price
        user_budget = inputs.user_budget
        risk_per_trade_percent = inputs.risk_per_trade_percent
        leverage = inputs.leverage
        position_side = inputs.position_side
        limits = inputs.exchange_limits
        
        # Initialize result
        result = PositionSizingResult(
            symbol=symbol,
            is_tradeable=False,
            rejection_reason=None,
            position_size_qty=0,
            position_size_usdt=0,
            required_margin=0,
            risk_amount=0,
            risk_percent=0,
            liquidation_price=0,
            liquidation_buffer=0,
            risk_buffer=0,
            safety_ratio=0,
            meets_min_notional=False,
            meets_min_qty=False,
            min_feasible_notional=0
        )
        
        # Step 1: Calculate minimum feasible notional
        min_feasible_notional = self.calculate_min_feasible_notional(limits, entry_price)
        result.min_feasible_notional = min_feasible_notional
        
        # Step 2: Check if budget can cover minimum order
        if user_budget < min_feasible_notional:
            result.rejection_reason = f"Budget ({user_budget:.2f} USDT) < Min Notional ({min_feasible_notional:.2f} USDT)"
            return result
        
        # Step 3: Calculate risk-based position size
        risk_amount = user_budget * risk_per_trade_percent
        result.risk_amount = risk_amount
        result.risk_percent = risk_per_trade_percent * 100
        
        # Calculate position size based on risk
        risk_buffer = abs(entry_price - stop_loss_price)
        result.risk_buffer = risk_buffer
        
        if risk_buffer == 0:
            result.rejection_reason = "Entry price equals stop loss price"
            return result
        
        position_size_qty = self.calculate_position_size_by_risk(
            entry_price, stop_loss_price, risk_amount
        )
        
        # Round to exchange step size
        position_size_qty = self.round_to_step_size(position_size_qty, limits.qty_step)
        result.position_size_qty = position_size_qty
        
        # Calculate position size in USDT
        position_size_usdt = position_size_qty * entry_price
        result.position_size_usdt = position_size_usdt
        
        # Step 4: Check exchange limits
        result.meets_min_qty = position_size_qty >= limits.min_qty
        result.meets_min_notional = position_size_usdt >= limits.min_notional
        
        if not result.meets_min_qty:
            result.rejection_reason = f"Position size ({position_size_qty:.6f}) < Min Qty ({limits.min_qty:.6f})"
            return result
        
        if not result.meets_min_notional:
            result.rejection_reason = f"Position value ({position_size_usdt:.2f}) < Min Notional ({limits.min_notional:.2f})"
            return result
        
        # Step 5: Calculate required margin
        required_margin = self.calculate_required_margin(position_size_usdt, leverage)
        result.required_margin = required_margin
        
        if required_margin > user_budget:
            result.rejection_reason = f"Required margin ({required_margin:.2f}) > Budget ({user_budget:.2f})"
            return result
        
        # Step 6: Calculate liquidation price and safety
        liquidation_price = self.calculate_liquidation_price(
            entry_price, leverage, limits.maintenance_margin_rate, position_side
        )
        result.liquidation_price = liquidation_price
        
        # Calculate liquidation buffer
        if position_side == PositionSide.LONG:
            liquidation_buffer = entry_price - liquidation_price
        else:  # SHORT
            liquidation_buffer = liquidation_price - entry_price
        
        result.liquidation_buffer = liquidation_buffer
        
        # Step 7: Safety ratio check
        if liquidation_buffer <= 0:
            result.rejection_reason = "Liquidation price too close to entry price"
            return result
        
        safety_ratio = liquidation_buffer / risk_buffer
        result.safety_ratio = safety_ratio
        
        if safety_ratio < self.risk_config.min_safety_ratio:
            result.rejection_reason = f"Safety ratio ({safety_ratio:.2f}) < Min required ({self.risk_config.min_safety_ratio:.2f})"
            return result
        
        # Step 8: Final budget check
        max_position_size = user_budget * self.risk_config.max_position_percent
        if required_margin > max_position_size:
            result.rejection_reason = f"Position too large: {required_margin:.2f} > {max_position_size:.2f} USDT (max {self.risk_config.max_position_percent:.1%})"
            return result
        
        # All checks passed!
        result.is_tradeable = True
        return result
    
    def filter_tradeable_symbols(self, symbols_data: List[Dict], 
                                risk_config: RiskManagementConfig = None) -> List[PositionSizingResult]:
        """
        Filter symbols based on position sizing and risk management criteria.
        
        Args:
            symbols_data: List of dicts containing symbol info with keys:
                - symbol, current_price, exchange_limits, etc.
            risk_config: Risk management configuration
            
        Returns:
            List of PositionSizingResult objects, sorted by safety ratio (descending)
        """
        if risk_config:
            self.risk_config = risk_config
        
        results = []
        
        for symbol_data in symbols_data:
            # Create position sizing input
            # Note: This assumes we have stop loss calculation logic
            # For now, we'll use a simple 2% stop loss
            entry_price = symbol_data['current_price']
            stop_loss_price = entry_price * 0.98  # 2% stop loss for LONG
            
            inputs = PositionSizingInput(
                symbol=symbol_data['symbol'],
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                take_profit_price=entry_price * 1.04,  # 4% take profit
                user_budget=self.risk_config.max_budget,
                risk_per_trade_percent=self.risk_config.max_risk_per_trade,
                leverage=self.risk_config.default_leverage,
                position_side=PositionSide.LONG,
                exchange_limits=symbol_data['exchange_limits']
            )
            
            result = self.analyze_position_sizing(inputs)
            results.append(result)
        
        # Sort by safety ratio (descending) for tradeable symbols
        tradeable_results = [r for r in results if r.is_tradeable]
        non_tradeable_results = [r for r in results if not r.is_tradeable]
        
        tradeable_results.sort(key=lambda x: x.safety_ratio, reverse=True)
        
        return tradeable_results + non_tradeable_results
