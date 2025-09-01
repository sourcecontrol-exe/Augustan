"""
Position State Management for Signal Generation
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from loguru import logger


class PositionState(Enum):
    """Current position state."""
    FLAT = "FLAT"      # No position
    LONG = "LONG"      # Long position open
    SHORT = "SHORT"    # Short position open


class SignalType(Enum):
    """Enhanced signal types with position context."""
    BUY_OPEN = "BUY_OPEN"      # Open long position (from FLAT)
    SELL_CLOSE = "SELL_CLOSE"  # Close long position (from LONG to FLAT)
    SELL_OPEN = "SELL_OPEN"    # Open short position (from FLAT)
    BUY_CLOSE = "BUY_CLOSE"    # Close short position (from SHORT to FLAT)
    HOLD = "HOLD"              # No action recommended
    INVALID = "INVALID"        # Invalid signal (e.g., BUY when already LONG)


@dataclass
class PositionInfo:
    """Information about current position."""
    state: PositionState
    symbol: str
    entry_price: Optional[float] = None
    entry_time: Optional[datetime] = None
    quantity: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "quantity": self.quantity,
            "unrealized_pnl": self.unrealized_pnl,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit
        }


@dataclass
class EnhancedSignal:
    """Enhanced trading signal with position context."""
    symbol: str
    signal_type: SignalType
    current_position: PositionState
    target_position: PositionState
    price: float
    timestamp: datetime
    strategy: str
    confidence: float
    reason: str
    
    # Additional metadata
    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None
    macd_signal: Optional[float] = None
    volume_rank: Optional[int] = None
    
    def is_valid(self) -> bool:
        """Check if signal is valid given current position state."""
        return self.signal_type != SignalType.INVALID
    
    def is_actionable(self) -> bool:
        """Check if signal requires action."""
        return self.signal_type in [SignalType.BUY_OPEN, SignalType.SELL_CLOSE, 
                                   SignalType.SELL_OPEN, SignalType.BUY_CLOSE]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "current_position": self.current_position.value,
            "target_position": self.target_position.value,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "strategy": self.strategy,
            "confidence": self.confidence,
            "reason": self.reason,
            "rsi_value": self.rsi_value,
            "macd_value": self.macd_value,
            "macd_signal": self.macd_signal,
            "volume_rank": self.volume_rank,
            "is_valid": self.is_valid(),
            "is_actionable": self.is_actionable()
        }


class PositionManager:
    """
    Manages position states and validates signal generation.
    
    This class tracks the current position state for each symbol and ensures
    that only valid signals are generated based on the current state.
    """
    
    def __init__(self):
        """Initialize position manager."""
        self.positions: Dict[str, PositionInfo] = {}
        self.signal_cooldowns: Dict[str, datetime] = {}
        
    def get_position_state(self, symbol: str) -> PositionState:
        """Get current position state for a symbol."""
        if symbol not in self.positions:
            return PositionState.FLAT
        return self.positions[symbol].state
    
    def set_position_state(self, symbol: str, state: PositionState, 
                          entry_price: Optional[float] = None,
                          quantity: Optional[float] = None):
        """Set position state for a symbol."""
        if symbol not in self.positions:
            self.positions[symbol] = PositionInfo(state=state, symbol=symbol)
        else:
            self.positions[symbol].state = state
        
        if entry_price is not None:
            self.positions[symbol].entry_price = entry_price
            self.positions[symbol].entry_time = datetime.now()
        
        if quantity is not None:
            self.positions[symbol].quantity = quantity
        
        # Clear position info when going flat
        if state == PositionState.FLAT:
            self.positions[symbol].entry_price = None
            self.positions[symbol].entry_time = None
            self.positions[symbol].quantity = None
            self.positions[symbol].unrealized_pnl = None
    
    def update_position_pnl(self, symbol: str, current_price: float):
        """Update unrealized PnL for a position."""
        if symbol not in self.positions or self.positions[symbol].state == PositionState.FLAT:
            return
        
        position = self.positions[symbol]
        if position.entry_price is None or position.quantity is None:
            return
        
        if position.state == PositionState.LONG:
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        elif position.state == PositionState.SHORT:
            position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
    
    def is_signal_allowed(self, symbol: str, cooldown_minutes: int = 15) -> bool:
        """Check if signal generation is allowed (not in cooldown)."""
        if symbol not in self.signal_cooldowns:
            return True
        
        cooldown_until = self.signal_cooldowns[symbol] + timedelta(minutes=cooldown_minutes)
        return datetime.now() > cooldown_until
    
    def set_signal_cooldown(self, symbol: str):
        """Set signal cooldown for a symbol."""
        self.signal_cooldowns[symbol] = datetime.now()
    
    def validate_and_create_signal(self, symbol: str, raw_signal_type: str,
                                 price: float, strategy: str, confidence: float,
                                 reason: str, **kwargs) -> EnhancedSignal:
        """
        Validate raw signal and create enhanced signal with position context.
        
        Args:
            symbol: Trading symbol
            raw_signal_type: Raw signal type ("BUY", "SELL", "HOLD")
            price: Current price
            strategy: Strategy name
            confidence: Signal confidence (0-1)
            reason: Reason for signal
            **kwargs: Additional signal metadata
            
        Returns:
            EnhancedSignal with proper position context
        """
        current_state = self.get_position_state(symbol)
        
        # Determine enhanced signal type based on current position and raw signal
        if raw_signal_type == "BUY":
            if current_state == PositionState.FLAT:
                signal_type = SignalType.BUY_OPEN
                target_state = PositionState.LONG
            elif current_state == PositionState.SHORT:
                signal_type = SignalType.BUY_CLOSE
                target_state = PositionState.FLAT
            else:  # Already LONG
                signal_type = SignalType.INVALID
                target_state = current_state
                reason = f"Invalid BUY signal - already in LONG position"
                
        elif raw_signal_type == "SELL":
            if current_state == PositionState.FLAT:
                signal_type = SignalType.SELL_OPEN
                target_state = PositionState.SHORT
            elif current_state == PositionState.LONG:
                signal_type = SignalType.SELL_CLOSE
                target_state = PositionState.FLAT
            else:  # Already SHORT
                signal_type = SignalType.INVALID
                target_state = current_state
                reason = f"Invalid SELL signal - already in SHORT position"
                
        else:  # HOLD or unknown
            signal_type = SignalType.HOLD
            target_state = current_state
        
        # Create enhanced signal
        signal = EnhancedSignal(
            symbol=symbol,
            signal_type=signal_type,
            current_position=current_state,
            target_position=target_state,
            price=price,
            timestamp=datetime.now(),
            strategy=strategy,
            confidence=confidence,
            reason=reason,
            **kwargs
        )
        
        # Log signal validation
        if signal.is_valid() and signal.is_actionable():
            logger.info(f"Valid signal: {symbol} {signal_type.value} at ${price:.4f} "
                       f"(confidence: {confidence:.2f})")
        elif not signal.is_valid():
            logger.warning(f"Invalid signal rejected: {symbol} {raw_signal_type} "
                          f"from {current_state.value} state")
        
        return signal
    
    def execute_signal(self, signal: EnhancedSignal) -> bool:
        """
        Execute signal and update position state.
        
        Args:
            signal: Enhanced signal to execute
            
        Returns:
            True if signal was executed, False otherwise
        """
        if not signal.is_valid() or not signal.is_actionable():
            logger.warning(f"Cannot execute invalid/non-actionable signal: {signal.signal_type.value}")
            return False
        
        # Update position state based on signal
        if signal.signal_type == SignalType.BUY_OPEN:
            self.set_position_state(signal.symbol, PositionState.LONG, signal.price)
            
        elif signal.signal_type == SignalType.SELL_CLOSE:
            self.set_position_state(signal.symbol, PositionState.FLAT)
            
        elif signal.signal_type == SignalType.SELL_OPEN:
            self.set_position_state(signal.symbol, PositionState.SHORT, signal.price)
            
        elif signal.signal_type == SignalType.BUY_CLOSE:
            self.set_position_state(signal.symbol, PositionState.FLAT)
        
        # Set cooldown to prevent rapid signal generation
        self.set_signal_cooldown(signal.symbol)
        
        logger.info(f"Executed signal: {signal.symbol} {signal.signal_type.value} -> "
                   f"{signal.target_position.value}")
        
        return True
    
    def get_all_positions(self) -> Dict[str, PositionInfo]:
        """Get all current positions."""
        return self.positions.copy()
    
    def get_active_positions(self) -> Dict[str, PositionInfo]:
        """Get only active (non-FLAT) positions."""
        return {symbol: pos for symbol, pos in self.positions.items() 
                if pos.state != PositionState.FLAT}
    
    def clear_all_positions(self):
        """Clear all positions (emergency stop)."""
        for symbol in self.positions:
            self.set_position_state(symbol, PositionState.FLAT)
        logger.warning("All positions cleared (emergency stop)")
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions."""
        active_positions = self.get_active_positions()
        
        return {
            "total_positions": len(self.positions),
            "active_positions": len(active_positions),
            "long_positions": sum(1 for pos in active_positions.values() 
                                if pos.state == PositionState.LONG),
            "short_positions": sum(1 for pos in active_positions.values() 
                                 if pos.state == PositionState.SHORT),
            "positions": {symbol: pos.to_dict() for symbol, pos in active_positions.items()}
        }
