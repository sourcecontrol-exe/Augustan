"""
Portfolio Manager - Manages Multiple Positions and Overall Risk
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger

from ..core.position_state import PositionInfo, PositionState, PositionManager
from .risk_manager import RiskManager, RiskCalculationResult


@dataclass
class PortfolioMetrics:
    """Portfolio-level risk and performance metrics."""
    total_account_balance: float
    total_position_value: float
    total_unrealized_pnl: float
    total_risk_amount: float
    
    # Risk metrics
    portfolio_risk_percentage: float
    position_count: int
    long_positions: int
    short_positions: int
    
    # Utilization metrics
    margin_used: float
    margin_available: float
    margin_utilization_percent: float
    
    # Performance metrics
    total_return_percent: float
    daily_pnl: float
    
    # Risk limits
    max_risk_per_trade: float
    max_portfolio_risk: float
    is_within_risk_limits: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_account_balance': self.total_account_balance,
            'total_position_value': self.total_position_value,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_risk_amount': self.total_risk_amount,
            'portfolio_risk_percentage': self.portfolio_risk_percentage,
            'position_count': self.position_count,
            'long_positions': self.long_positions,
            'short_positions': self.short_positions,
            'margin_used': self.margin_used,
            'margin_available': self.margin_available,
            'margin_utilization_percent': self.margin_utilization_percent,
            'total_return_percent': self.total_return_percent,
            'daily_pnl': self.daily_pnl,
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_portfolio_risk': self.max_portfolio_risk,
            'is_within_risk_limits': self.is_within_risk_limits,
            'timestamp': datetime.now().isoformat()
        }


class PortfolioManager:
    """
    Portfolio Manager - Oversees Multiple Positions and Portfolio Risk
    
    Responsibilities:
    1. Track all open positions across symbols
    2. Calculate portfolio-level risk metrics
    3. Enforce portfolio-wide risk limits
    4. Prevent over-concentration in single positions
    5. Monitor margin utilization
    6. Calculate portfolio performance
    """
    
    def __init__(self, initial_balance: float, config_path: Optional[str] = None):
        """
        Initialize Portfolio Manager.
        
        Args:
            initial_balance: Starting account balance
            config_path: Path to configuration file
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # Initialize managers
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager(config_path)
        
        # Portfolio limits
        self.max_positions = 5  # Maximum simultaneous positions
        self.max_portfolio_risk = 0.05  # 5% maximum portfolio risk
        self.max_correlation_exposure = 0.3  # 30% max exposure to correlated assets
        
        # Performance tracking
        self.daily_pnl_history: List[float] = []
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info(f"PortfolioManager initialized with ${initial_balance:.2f} balance")
    
    def can_open_new_position(self, symbol: str, position_value: float) -> Tuple[bool, Optional[str]]:
        """
        Check if a new position can be opened based on portfolio limits.
        
        Args:
            symbol: Symbol for new position
            position_value: Value of proposed position
            
        Returns:
            (can_open, reason_if_not)
        """
        active_positions = self.position_manager.get_active_positions()
        
        # Check maximum position count
        if len(active_positions) >= self.max_positions:
            return False, f"Maximum positions reached: {len(active_positions)}/{self.max_positions}"
        
        # Check if position already exists for this symbol
        if symbol in active_positions:
            return False, f"Position already exists for {symbol}"
        
        # Check portfolio concentration
        portfolio_value = sum(pos.quantity * pos.entry_price for pos in active_positions.values() 
                            if pos.entry_price and pos.quantity)
        new_portfolio_value = portfolio_value + position_value
        
        position_concentration = position_value / new_portfolio_value if new_portfolio_value > 0 else 0
        if position_concentration > 0.4:  # 40% max concentration
            return False, f"Position too large: {position_concentration:.1%} of portfolio"
        
        # Check available margin
        metrics = self.calculate_portfolio_metrics()
        if metrics.margin_utilization_percent > 80:  # 80% max margin utilization
            return False, f"Insufficient margin: {metrics.margin_utilization_percent:.1f}% utilized"
        
        return True, None
    
    def evaluate_new_trade(self, signal, current_price: float, leverage: int = 1) -> RiskCalculationResult:
        """
        Evaluate a new trade considering portfolio-level constraints.
        
        Args:
            signal: Trading signal
            current_price: Current market price
            leverage: Leverage to use
            
        Returns:
            RiskCalculationResult with portfolio-aware calculations
        """
        # Calculate position size using risk manager
        result = self.risk_manager.calculate_position_size(
            signal, current_price, self.current_balance, leverage
        )
        
        if not result.is_safe_to_trade:
            return result
        
        # Additional portfolio-level checks
        can_open, reason = self.can_open_new_position(signal.symbol, result.position_value)
        if not can_open:
            result.is_safe_to_trade = False
            result.rejection_reason = f"Portfolio limit: {reason}"
            return result
        
        # Check portfolio risk after adding this position
        current_portfolio_risk = self.calculate_portfolio_metrics().portfolio_risk_percentage
        new_portfolio_risk = current_portfolio_risk + result.risk_percentage
        
        if new_portfolio_risk > self.max_portfolio_risk * 100:
            result.is_safe_to_trade = False
            result.rejection_reason = f"Portfolio risk too high: {new_portfolio_risk:.2f}% > {self.max_portfolio_risk * 100:.2f}%"
            return result
        
        logger.info(f"✅ Portfolio approved trade: {signal.symbol} - "
                   f"New portfolio risk: {new_portfolio_risk:.2f}%")
        
        return result
    
    def execute_trade(self, result: RiskCalculationResult) -> bool:
        """
        Execute a trade and update portfolio state.
        
        Args:
            result: Risk calculation result from evaluate_new_trade
            
        Returns:
            True if trade executed successfully
        """
        if not result.is_safe_to_trade:
            logger.error(f"Cannot execute unsafe trade: {result.rejection_reason}")
            return False
        
        # Execute signal through position manager
        success = self.position_manager.execute_signal(result.signal)
        
        if success:
            # Update account balance (subtract margin used)
            self.current_balance -= result.required_margin
            
            # Record trade
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': result.signal.symbol,
                'signal_type': result.signal.signal_type.value,
                'position_size': result.position_size,
                'position_value': result.position_value,
                'required_margin': result.required_margin,
                'risk_amount': result.risk_amount,
                'entry_price': result.current_price
            }
            self.trade_history.append(trade_record)
            
            logger.info(f"✅ Executed trade: {result.signal.symbol} {result.signal.signal_type.value}")
            
        return success
    
    def close_position(self, symbol: str, exit_price: float) -> Optional[Dict[str, Any]]:
        """
        Close a position and update portfolio.
        
        Args:
            symbol: Symbol to close
            exit_price: Exit price
            
        Returns:
            Trade result dictionary or None if failed
        """
        position = self.position_manager.positions.get(symbol)
        if not position or position.state == PositionState.FLAT:
            logger.warning(f"No active position to close for {symbol}")
            return None
        
        # Calculate PnL
        if position.entry_price and position.quantity:
            if position.state == PositionState.LONG:
                pnl = (exit_price - position.entry_price) * position.quantity
            else:  # SHORT
                pnl = (position.entry_price - exit_price) * position.quantity
            
            # Update account balance
            self.current_balance += pnl
            
            # Close position
            self.position_manager.set_position_state(symbol, PositionState.FLAT)
            
            # Record trade result
            trade_result = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'CLOSE',
                'entry_price': position.entry_price,
                'exit_price': exit_price,
                'quantity': position.quantity,
                'pnl': pnl,
                'pnl_percent': (pnl / (position.entry_price * position.quantity)) * 100
            }
            
            self.trade_history.append(trade_result)
            
            logger.info(f"✅ Closed position: {symbol} - PnL: ${pnl:.2f} "
                       f"({trade_result['pnl_percent']:.2f}%)")
            
            return trade_result
        
        return None
    
    def calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics."""
        active_positions = self.position_manager.get_active_positions()
        
        # Basic metrics
        total_position_value = 0.0
        total_unrealized_pnl = 0.0
        total_risk_amount = 0.0
        margin_used = 0.0
        
        long_count = 0
        short_count = 0
        
        for symbol, position in active_positions.items():
            if position.entry_price and position.quantity:
                position_value = position.entry_price * position.quantity
                total_position_value += position_value
                
                if position.unrealized_pnl:
                    total_unrealized_pnl += position.unrealized_pnl
                
                # Estimate risk (2% stop loss assumption)
                total_risk_amount += position_value * 0.02
                
                # Estimate margin used (assuming 5x leverage)
                margin_used += position_value / 5
                
                if position.state == PositionState.LONG:
                    long_count += 1
                else:
                    short_count += 1
        
        # Portfolio risk percentage
        portfolio_risk_percentage = (total_risk_amount / self.current_balance) * 100 if self.current_balance > 0 else 0
        
        # Margin metrics
        margin_available = self.current_balance - margin_used
        margin_utilization_percent = (margin_used / self.current_balance) * 100 if self.current_balance > 0 else 0
        
        # Performance metrics
        total_return_percent = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        daily_pnl = self.daily_pnl_history[-1] if self.daily_pnl_history else 0.0
        
        # Risk limits check
        is_within_risk_limits = (
            portfolio_risk_percentage <= self.max_portfolio_risk * 100 and
            len(active_positions) <= self.max_positions and
            margin_utilization_percent <= 80
        )
        
        return PortfolioMetrics(
            total_account_balance=self.current_balance,
            total_position_value=total_position_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_risk_amount=total_risk_amount,
            portfolio_risk_percentage=portfolio_risk_percentage,
            position_count=len(active_positions),
            long_positions=long_count,
            short_positions=short_count,
            margin_used=margin_used,
            margin_available=margin_available,
            margin_utilization_percent=margin_utilization_percent,
            total_return_percent=total_return_percent,
            daily_pnl=daily_pnl,
            max_risk_per_trade=self.risk_manager.max_risk_per_trade * 100,
            max_portfolio_risk=self.max_portfolio_risk * 100,
            is_within_risk_limits=is_within_risk_limits
        )
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        metrics = self.calculate_portfolio_metrics()
        active_positions = self.position_manager.get_active_positions()
        
        return {
            'account_info': {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_return': metrics.total_return_percent,
                'daily_pnl': metrics.daily_pnl
            },
            'portfolio_metrics': metrics.to_dict(),
            'positions': {
                symbol: pos.to_dict() for symbol, pos in active_positions.items()
            },
            'risk_limits': {
                'max_positions': self.max_positions,
                'max_portfolio_risk': self.max_portfolio_risk * 100,
                'max_correlation_exposure': self.max_correlation_exposure * 100,
                'is_within_limits': metrics.is_within_risk_limits
            },
            'trade_count': len(self.trade_history),
            'last_updated': datetime.now().isoformat()
        }
    
    def emergency_stop(self) -> Dict[str, Any]:
        """Emergency stop - close all positions."""
        logger.warning("🚨 EMERGENCY STOP TRIGGERED - Closing all positions")
        
        active_positions = self.position_manager.get_active_positions()
        closed_positions = []
        
        for symbol, position in active_positions.items():
            # In a real implementation, this would place market orders to close positions
            # For now, we'll just mark them as closed
            self.position_manager.set_position_state(symbol, PositionState.FLAT)
            closed_positions.append(symbol)
        
        logger.warning(f"Emergency stop completed - Closed {len(closed_positions)} positions")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'action': 'EMERGENCY_STOP',
            'closed_positions': closed_positions,
            'final_balance': self.current_balance
        }
    
    def update_daily_pnl(self, pnl: float):
        """Update daily PnL tracking."""
        self.daily_pnl_history.append(pnl)
        # Keep only last 30 days
        if len(self.daily_pnl_history) > 30:
            self.daily_pnl_history.pop(0)
    
    def on_order_filled(self, order_id: str, order_result):
        """
        Handle order fill events from OrderManager.
        
        This method is called when an order is filled, allowing the PortfolioManager
        to update position state and track execution details.
        
        Args:
            order_id: Order ID that was filled
            order_result: Order result with fill details
        """
        try:
            # Extract order details from the order manager
            # This assumes the order manager has the order request stored
            # The actual implementation would need to access the order request
            
            logger.info(f"PortfolioManager received order fill: {order_id}")
            
            # Update position state based on fill
            # This is handled by the LiveTradingEngine for now
            
        except Exception as e:
            logger.error(f"Error handling order fill in PortfolioManager: {e}")
    
    def save_state(self, file_path: str):
        """
        Save portfolio state to file.
        
        Args:
            file_path: Path to save the state file
        """
        try:
            state_data = {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'positions': {
                    symbol: pos.to_dict() for symbol, pos in self.position_manager.positions.items()
                },
                'trade_history': self.trade_history,
                'daily_pnl_history': self.daily_pnl_history,
                'max_positions': self.max_positions,
                'max_portfolio_risk': self.max_portfolio_risk,
                'max_correlation_exposure': self.max_correlation_exposure,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            logger.info(f"Portfolio state saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")
            raise
    
    def load_state(self, file_path: str):
        """
        Load portfolio state from file.
        
        Args:
            file_path: Path to load the state file from
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"State file not found: {file_path}. Using defaults.")
                return
            
            with open(file_path, 'r') as f:
                state_data = json.load(f)
            
            # Load basic data
            self.current_balance = state_data.get('current_balance', self.initial_balance)
            self.max_positions = state_data.get('max_positions', 5)
            self.max_portfolio_risk = state_data.get('max_portfolio_risk', 0.05)
            self.max_correlation_exposure = state_data.get('max_correlation_exposure', 0.3)
            
            # Load positions
            positions_data = state_data.get('positions', {})
            for symbol, pos_data in positions_data.items():
                position_info = PositionInfo(
                    state=PositionState(pos_data['state']),
                    symbol=pos_data['symbol'],
                    entry_price=pos_data.get('entry_price'),
                    entry_time=datetime.fromisoformat(pos_data['entry_time']) if pos_data.get('entry_time') else None,
                    quantity=pos_data.get('quantity'),
                    unrealized_pnl=pos_data.get('unrealized_pnl'),
                    stop_loss=pos_data.get('stop_loss'),
                    take_profit=pos_data.get('take_profit')
                )
                self.position_manager.positions[symbol] = position_info
            
            # Load trade history
            self.trade_history = state_data.get('trade_history', [])
            
            # Load daily PnL history
            self.daily_pnl_history = state_data.get('daily_pnl_history', [])
            
            logger.info(f"Portfolio state loaded from {file_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in state file: {e}. Using defaults.")
        except Exception as e:
            logger.error(f"Failed to load portfolio state: {e}. Using defaults.")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.trade_history:
            return {'message': 'No trades executed yet'}
        
        # Calculate win rate, average profit/loss, etc.
        profitable_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trade_history if t.get('pnl', 0) < 0]
        
        win_rate = len(profitable_trades) / len(self.trade_history) * 100 if self.trade_history else 0
        avg_profit = sum(t.get('pnl', 0) for t in profitable_trades) / len(profitable_trades) if profitable_trades else 0
        avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            'total_trades': len(self.trade_history),
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'average_profit': avg_profit,
            'average_loss': avg_loss,
            'profit_factor': abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf'),
            'total_pnl': sum(t.get('pnl', 0) for t in self.trade_history),
            'current_return': ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        }
