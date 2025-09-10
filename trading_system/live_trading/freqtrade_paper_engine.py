"""
Freqtrade-Style Paper Trading Engine
Implements realistic paper trading without requiring exchange API keys.
Uses real market data but simulates order execution with realistic slippage and fees.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger
import uuid
import random

from ..core.event_system import EventHandler, OrderFilledEvent, event_bus
from ..core.models import MarketData
from ..core.position_state import SignalType, PositionState


@dataclass
class PaperOrder:
    """Paper trading order."""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop'
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str = 'pending'  # 'pending', 'filled', 'cancelled', 'rejected'
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    commission: float = 0.0
    slippage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'filled_price': self.filled_price,
            'filled_quantity': self.filled_quantity,
            'commission': self.commission,
            'slippage': self.slippage
        }


@dataclass
class PaperPosition:
    """Paper trading position."""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    
    def update_price(self, current_price: float):
        """Update current price and calculate unrealized P&L."""
        self.current_price = current_price
        
        if self.side == 'long':
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'trailing_stop': self.trailing_stop
        }


@dataclass
class PaperTradingConfig:
    """Configuration for paper trading."""
    initial_balance: float = 10000.0
    commission_rate: float = 0.001  # 0.1% commission
    slippage_rate: float = 0.0005   # 0.05% slippage
    min_order_size: float = 0.001   # Minimum order size
    max_order_size: float = 1000.0  # Maximum order size
    enable_slippage: bool = True
    enable_commission: bool = True
    realistic_execution_delay: bool = True  # Simulate execution delays
    max_execution_delay_ms: int = 100  # Max delay in milliseconds


class FreqtradePaperEngine(EventHandler):
    """
    Freqtrade-Style Paper Trading Engine
    
    Features:
    - Real market data with simulated execution
    - Realistic slippage and commission simulation
    - Order book simulation for limit orders
    - Position tracking and P&L calculation
    - Trade history and performance metrics
    - No API keys required
    """
    
    def __init__(self, config: PaperTradingConfig = None):
        """Initialize paper trading engine."""
        super().__init__()
        self.config = config or PaperTradingConfig()
        
        # Account state
        self.balance = self.config.initial_balance
        self.initial_balance = self.config.initial_balance
        self.available_balance = self.balance
        
        # Trading state
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.trade_history: List[Dict] = []
        
        # Market data
        self.current_prices: Dict[str, float] = {}
        self.order_books: Dict[str, Dict] = {}
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = self.initial_balance
        
        # Subscribe to market data events
        from ..core.event_system import EventType
        self.subscribe(EventType.CANDLE_CLOSED, self.handle_market_data)
        
        logger.info(f"Freqtrade Paper Engine initialized with ${self.balance:,.2f}")
    
    async def handle_market_data(self, event):
        """Handle new market data."""
        symbol = event.symbol
        candle_data = event.candle_data
        
        # Update current price
        self.current_prices[symbol] = candle_data.close
        
        # Update positions
        if symbol in self.positions:
            self.positions[symbol].update_price(candle_data.close)
        
        # Process pending orders
        await self._process_pending_orders(symbol, candle_data)
        
        # Update trailing stops
        await self._update_trailing_stops(symbol, candle_data.close)
    
    async def submit_order(self, symbol: str, side: str, order_type: str, 
                          quantity: float, price: Optional[float] = None,
                          stop_price: Optional[float] = None) -> str:
        """
        Submit a paper trading order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop'
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            Order ID
        """
        # Validate order
        if not self._validate_order(symbol, side, quantity, price):
            raise ValueError("Invalid order parameters")
        
        # Create order
        order_id = str(uuid.uuid4())
        order = PaperOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        self.orders[order_id] = order
        
        # Process order immediately for market orders
        if order_type == 'market':
            await self._execute_market_order(order)
        elif order_type == 'limit':
            await self._queue_limit_order(order)
        elif order_type == 'stop':
            await self._queue_stop_order(order)
        
        logger.info(f"Order submitted: {order_id} {side} {quantity} {symbol}")
        return order_id
    
    def _validate_order(self, symbol: str, side: str, quantity: float, price: Optional[float]) -> bool:
        """Validate order parameters."""
        # Check quantity limits
        if quantity < self.config.min_order_size or quantity > self.config.max_order_size:
            logger.warning(f"Order quantity {quantity} outside limits")
            return False
        
        # Check available balance for buy orders
        if side == 'buy':
            required_balance = quantity * (price or self.current_prices.get(symbol, 0))
            if required_balance > self.available_balance:
                logger.warning(f"Insufficient balance: need ${required_balance:.2f}, have ${self.available_balance:.2f}")
                return False
        
        # Check position for sell orders
        if side == 'sell':
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                logger.warning(f"Insufficient position: need {quantity}, have {self.positions.get(symbol, {}).get('quantity', 0)}")
                return False
        
        return True
    
    async def _execute_market_order(self, order: PaperOrder):
        """Execute a market order."""
        symbol = order.symbol
        current_price = self.current_prices.get(symbol, 0)
        
        if current_price == 0:
            logger.error(f"No price data for {symbol}")
            order.status = 'rejected'
            return
        
        # Calculate execution price with slippage
        execution_price = self._calculate_execution_price(current_price, order.side, order.order_type)
        
        # Calculate commission
        commission = self._calculate_commission(order.quantity, execution_price)
        
        # Calculate slippage
        slippage = abs(execution_price - current_price)
        
        # Update order
        order.status = 'filled'
        order.filled_at = datetime.now()
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.slippage = slippage
        
        # Update account
        await self._update_account(order)
        
        # Update position
        await self._update_position(order)
        
        # Emit order filled event
        await self._emit_order_filled(order)
        
        logger.info(f"Market order executed: {order.id} @ {execution_price:.4f}")
    
    async def _queue_limit_order(self, order: PaperOrder):
        """Queue a limit order for execution."""
        # Limit orders are executed when price reaches the limit
        logger.info(f"Limit order queued: {order.id} @ {order.price:.4f}")
    
    async def _queue_stop_order(self, order: PaperOrder):
        """Queue a stop order for execution."""
        # Stop orders are executed when price reaches the stop price
        logger.info(f"Stop order queued: {order.id} @ {order.stop_price:.4f}")
    
    async def _process_pending_orders(self, symbol: str, candle_data: MarketData):
        """Process pending limit and stop orders."""
        current_price = candle_data.close
        
        for order_id, order in self.orders.items():
            if order.status != 'pending' or order.symbol != symbol:
                continue
            
            # Check limit orders
            if order.order_type == 'limit':
                if self._should_execute_limit_order(order, current_price):
                    await self._execute_limit_order(order, current_price)
            
            # Check stop orders
            elif order.order_type == 'stop':
                if self._should_execute_stop_order(order, current_price):
                    await self._execute_stop_order(order, current_price)
    
    def _should_execute_limit_order(self, order: PaperOrder, current_price: float) -> bool:
        """Check if limit order should be executed."""
        if order.side == 'buy':
            return current_price <= order.price  # Buy when price drops to limit
        else:
            return current_price >= order.price  # Sell when price rises to limit
    
    def _should_execute_stop_order(self, order: PaperOrder, current_price: float) -> bool:
        """Check if stop order should be executed."""
        if order.side == 'buy':
            return current_price >= order.stop_price  # Buy stop when price rises
        else:
            return current_price <= order.stop_price  # Sell stop when price drops
    
    async def _execute_limit_order(self, order: PaperOrder, execution_price: float):
        """Execute a limit order."""
        # Calculate commission
        commission = self._calculate_commission(order.quantity, execution_price)
        
        # Update order
        order.status = 'filled'
        order.filled_at = datetime.now()
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.slippage = 0.0  # No slippage for limit orders
        
        # Update account and position
        await self._update_account(order)
        await self._update_position(order)
        await self._emit_order_filled(order)
        
        logger.info(f"Limit order executed: {order.id} @ {execution_price:.4f}")
    
    async def _execute_stop_order(self, order: PaperOrder, execution_price: float):
        """Execute a stop order."""
        # Calculate commission
        commission = self._calculate_commission(order.quantity, execution_price)
        
        # Update order
        order.status = 'filled'
        order.filled_at = datetime.now()
        order.filled_price = execution_price
        order.filled_quantity = order.quantity
        order.commission = commission
        order.slippage = 0.0  # Stop orders execute at market
        
        # Update account and position
        await self._update_account(order)
        await self._update_position(order)
        await self._emit_order_filled(order)
        
        logger.info(f"Stop order executed: {order.id} @ {execution_price:.4f}")
    
    def _calculate_execution_price(self, current_price: float, side: str, order_type: str) -> float:
        """Calculate execution price with slippage."""
        if not self.config.enable_slippage:
            return current_price
        
        # Calculate slippage
        slippage_amount = current_price * self.config.slippage_rate
        
        if side == 'buy':
            # Buy orders execute at slightly higher price
            return current_price + slippage_amount
        else:
            # Sell orders execute at slightly lower price
            return current_price - slippage_amount
    
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculate commission."""
        if not self.config.enable_commission:
            return 0.0
        
        trade_value = quantity * price
        return trade_value * self.config.commission_rate
    
    async def _update_account(self, order: PaperOrder):
        """Update account balance."""
        trade_value = order.filled_quantity * order.filled_price
        total_cost = trade_value + order.commission
        
        if order.side == 'buy':
            self.available_balance -= total_cost
        else:
            self.available_balance += trade_value - order.commission
        
        # Update total balance
        self.balance = self.available_balance + self._calculate_position_value()
        
        # Update peak balance and drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        
        current_drawdown = (self.peak_balance - self.balance) / self.peak_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
    
    async def _update_position(self, order: PaperOrder):
        """Update position."""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # Create new position
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                side='long' if order.side == 'buy' else 'short',
                quantity=order.filled_quantity,
                entry_price=order.filled_price,
                entry_time=order.filled_at
            )
        else:
            # Update existing position
            position = self.positions[symbol]
            
            if position.side == order.side:
                # Add to position
                total_quantity = position.quantity + order.filled_quantity
                total_value = (position.quantity * position.entry_price) + (order.filled_quantity * order.filled_price)
                position.quantity = total_quantity
                position.entry_price = total_value / total_quantity
            else:
                # Close or reduce position
                if order.filled_quantity >= position.quantity:
                    # Close position
                    await self._close_position(symbol, order)
                else:
                    # Reduce position
                    position.quantity -= order.filled_quantity
    
    async def _close_position(self, symbol: str, order: PaperOrder):
        """Close a position."""
        position = self.positions[symbol]
        
        # Calculate P&L
        if position.side == 'long':
            pnl = (order.filled_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - order.filled_price) * position.quantity
        
        # Update trade statistics
        self.total_trades += 1
        self.total_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Add to trade history
        trade_record = {
            'symbol': symbol,
            'side': position.side,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'exit_price': order.filled_price,
            'entry_time': position.entry_time.isoformat(),
            'exit_time': order.filled_at.isoformat(),
            'pnl': pnl,
            'commission': order.commission,
            'duration': (order.filled_at - position.entry_time).total_seconds()
        }
        self.trade_history.append(trade_record)
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"Position closed: {symbol} P&L ${pnl:.2f}")
    
    def _calculate_position_value(self) -> float:
        """Calculate total position value."""
        total_value = 0.0
        for symbol, position in self.positions.items():
            current_price = self.current_prices.get(symbol, position.entry_price)
            position.update_price(current_price)
            total_value += position.unrealized_pnl
        return total_value
    
    async def _update_trailing_stops(self, symbol: str, current_price: float):
        """Update trailing stops."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        if not position.trailing_stop:
            return
        
        # Update trailing stop based on price movement
        if position.side == 'long':
            if current_price > position.entry_price:
                new_trailing_stop = current_price * 0.98  # 2% trailing stop
                if new_trailing_stop > position.trailing_stop:
                    position.trailing_stop = new_trailing_stop
        else:
            if current_price < position.entry_price:
                new_trailing_stop = current_price * 1.02  # 2% trailing stop
                if new_trailing_stop < position.trailing_stop:
                    position.trailing_stop = new_trailing_stop
    
    async def _emit_order_filled(self, order: PaperOrder):
        """Emit order filled event."""
        event = OrderFilledEvent(
            symbol=order.symbol,
            order_id=order.id,
            side=order.side,
            quantity=order.filled_quantity,
            price=order.filled_price,
            commission=order.commission
        )
        await event_bus.emit(event)
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        position_value = self._calculate_position_value()
        
        return {
            'balance': self.balance,
            'available_balance': self.available_balance,
            'initial_balance': self.initial_balance,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': position_value,
            'max_drawdown': self.max_drawdown,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / max(self.total_trades, 1),
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
            'active_orders': len([o for o in self.orders.values() if o.status == 'pending'])
        }
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get trade history."""
        return self.trade_history.copy()
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status != 'pending':
            return False
        
        order.status = 'cancelled'
        logger.info(f"Order cancelled: {order_id}")
        return True
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get open orders."""
        return [order.to_dict() for order in self.orders.values() if order.status == 'pending']
