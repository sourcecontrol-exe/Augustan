"""
Paper Trading Mode - Simulated trading environment for strategy validation.

This module provides a complete paper trading system that runs live against
real market data but executes simulated trades, allowing for comprehensive
strategy testing without financial risk.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import pandas as pd
from loguru import logger

from .models import MarketData, TradingSignal, SignalType
from .orderbook import OrderBook
from .exchange_manager import ExchangeManager, ExchangeConfig
from .data_handler import DataHandler


class OrderStatus(Enum):
    """Paper trading order status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class PaperOrder:
    """Paper trading order."""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    commission: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'commission': self.commission,
            'created_at': self.created_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None
        }


@dataclass
class Position:
    """Paper trading position."""
    symbol: str
    side: OrderSide
    quantity: float
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'average_price': self.average_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class Trade:
    """Paper trading trade execution."""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'commission': self.commission,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PaperTradingConfig:
    """Paper trading configuration."""
    initial_balance: float = 10000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005  # 0.05%
    max_position_size: float = 0.1  # 10% of balance
    enable_slippage: bool = True
    enable_commission: bool = True
    enable_latency: bool = True
    latency_ms: int = 50
    enable_partial_fills: bool = True
    partial_fill_probability: float = 0.3


class PaperTradingEngine:
    """
    Paper trading engine for strategy validation.
    
    Features:
    - Real-time market data processing
    - Simulated order execution with realistic conditions
    - Position and portfolio management
    - Performance tracking and analytics
    - Risk management controls
    - Strategy signal processing
    """
    
    def __init__(self, exchange_manager: ExchangeManager, 
                 data_handler: DataHandler, 
                 config: Optional[PaperTradingConfig] = None):
        """
        Initialize paper trading engine.
        
        Args:
            exchange_manager: Exchange manager for market data
            data_handler: Data handler for processing market data
            config: Paper trading configuration
        """
        self.exchange_manager = exchange_manager
        self.data_handler = data_handler
        self.config = config or PaperTradingConfig()
        
        # Trading state
        self.balance = self.config.initial_balance
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.trades: List[Trade] = []
        self.order_counter = 0
        self.trade_counter = 0
        
        # Market data tracking
        self.current_prices: Dict[str, float] = {}
        self.orderbooks: Dict[str, OrderBook] = {}
        
        # Performance tracking
        self.start_balance = self.config.initial_balance
        self.start_time = datetime.now()
        self.daily_returns: List[float] = []
        self.max_drawdown = 0.0
        self.peak_balance = self.config.initial_balance
        
        # Strategy callbacks
        self.signal_callbacks: List[Callable[[TradingSignal], None]] = []
        self.order_callbacks: List[Callable[[PaperOrder], None]] = []
        self.trade_callbacks: List[Callable[[Trade], None]] = []
        self.position_callbacks: List[Callable[[str, Position], None]] = []
        
        # Risk management
        self.max_daily_loss = 0.05  # 5% max daily loss
        self.max_position_count = 10
        self.emergency_stop = False
        
        logger.info(f"PaperTradingEngine initialized with ${self.balance:.2f} balance")
    
    def add_signal_callback(self, callback: Callable[[TradingSignal], None]):
        """Add signal callback."""
        self.signal_callbacks.append(callback)
    
    def add_order_callback(self, callback: Callable[[PaperOrder], None]):
        """Add order callback."""
        self.order_callbacks.append(callback)
    
    def add_trade_callback(self, callback: Callable[[Trade], None]):
        """Add trade callback."""
        self.trade_callbacks.append(callback)
    
    def add_position_callback(self, callback: Callable[[str, Position], None]):
        """Add position callback."""
        self.position_callbacks.append(callback)
    
    async def start(self):
        """Start paper trading engine."""
        logger.info("Starting paper trading engine")
        
        # Connect to exchanges
        await self.exchange_manager.connect_all()
        
        # Start data processing
        await self._start_data_processing()
        
        # Start order processing
        await self._start_order_processing()
        
        logger.info("Paper trading engine started")
    
    async def stop(self):
        """Stop paper trading engine."""
        logger.info("Stopping paper trading engine")
        
        # Cancel all pending orders
        await self._cancel_all_orders()
        
        # Close all positions
        await self._close_all_positions()
        
        logger.info("Paper trading engine stopped")
    
    async def _start_data_processing(self):
        """Start processing market data."""
        # Add data callbacks
        self.exchange_manager.add_data_callback(self._on_market_data)
        self.data_handler.add_market_data_callback(self._on_processed_market_data)
        self.data_handler.add_orderbook_callback(self._on_orderbook_update)
    
    async def _start_order_processing(self):
        """Start order processing loop."""
        while not self.emergency_stop:
            try:
                await self._process_pending_orders()
                await asyncio.sleep(0.1)  # Process orders every 100ms
            except Exception as e:
                logger.error(f"Error in order processing: {e}")
                await asyncio.sleep(1)
    
    def _on_market_data(self, exchange_name: str, symbol: str, data: Dict):
        """Handle incoming market data."""
        try:
            # Update current prices
            if 'last' in data:
                self.current_prices[symbol] = float(data['last'])
            elif 'close' in data:
                self.current_prices[symbol] = float(data['close'])
            
            # Update positions with current prices
            self._update_position_pnl(symbol)
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    def _on_processed_market_data(self, symbol: str, market_data: MarketData):
        """Handle processed market data."""
        try:
            # Update current price
            self.current_prices[symbol] = market_data.close
            
            # Update position PnL
            self._update_position_pnl(symbol)
            
            # Check for strategy signals
            self._check_strategy_signals(symbol, market_data)
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    def _on_orderbook_update(self, exchange_name: str, symbol: str, orderbook: OrderBook):
        """Handle orderbook updates."""
        try:
            self.orderbooks[symbol] = orderbook
            
            # Update current prices from orderbook
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            
            if best_bid and best_ask:
                mid_price = (best_bid[0] + best_ask[0]) / 2
                self.current_prices[symbol] = mid_price
            
        except Exception as e:
            logger.error(f"Error processing orderbook update: {e}")
    
    def _check_strategy_signals(self, symbol: str, market_data: MarketData):
        """Check for strategy signals and generate trading signals."""
        # This would integrate with your strategy engine
        # For now, we'll implement a simple example
        
        # Example: Simple momentum strategy
        if symbol in self.data_handler.market_data:
            historical_data = list(self.data_handler.market_data[symbol])[-20:]  # Last 20 candles
            
            if len(historical_data) >= 20:
                # Calculate simple moving average
                closes = [md.close for md in historical_data]
                sma_short = sum(closes[-5:]) / 5  # 5-period SMA
                sma_long = sum(closes[-20:]) / 20  # 20-period SMA
                
                # Generate signal
                if sma_short > sma_long and closes[-1] > closes[-2]:
                    signal = TradingSignal(
                        symbol=symbol,
                        strategy=StrategyType.SMA_CROSSOVER,
                        signal_type=SignalType.BUY,
                        confidence=0.7,
                        price=market_data.close,
                        timestamp=market_data.timestamp
                    )
                    self._process_signal(signal)
                elif sma_short < sma_long and closes[-1] < closes[-2]:
                    signal = TradingSignal(
                        symbol=symbol,
                        strategy=StrategyType.SMA_CROSSOVER,
                        signal_type=SignalType.SELL,
                        confidence=0.7,
                        price=market_data.close,
                        timestamp=market_data.timestamp
                    )
                    self._process_signal(signal)
    
    def _process_signal(self, signal: TradingSignal):
        """Process trading signal."""
        try:
            # Notify signal callbacks
            for callback in self.signal_callbacks:
                callback(signal)
            
            # Convert signal to order (schedule async execution)
            if signal.signal_type == SignalType.BUY:
                asyncio.create_task(self._place_buy_order(signal))
            elif signal.signal_type == SignalType.SELL:
                asyncio.create_task(self._place_sell_order(signal))
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _place_buy_order(self, signal: TradingSignal):
        """Place buy order from signal."""
        # Calculate position size based on risk management
        position_size = self._calculate_position_size(signal.symbol, signal.price)
        
        if position_size > 0:
            order = await self.place_order(
                symbol=signal.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=position_size
            )
            
            if order:
                logger.info(f"Placed BUY order: {signal.symbol} {position_size} @ {signal.price}")
    
    async def _place_sell_order(self, signal: TradingSignal):
        """Place sell order from signal."""
        # Check if we have position to sell
        if signal.symbol in self.positions:
            position = self.positions[signal.symbol]
            if position.side == OrderSide.BUY and position.quantity > 0:
                order = await self.place_order(
                    symbol=signal.symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position.quantity
                )
                
                if order:
                    logger.info(f"Placed SELL order: {signal.symbol} {position.quantity} @ {signal.price}")
    
    def _calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on risk management."""
        try:
            # Risk management: max 10% of balance per position
            max_position_value = self.balance * self.config.max_position_size
            max_quantity = max_position_value / price
            
            # Check existing position
            if symbol in self.positions:
                existing_position = self.positions[symbol]
                if existing_position.side == OrderSide.BUY:
                    # Already long, don't add more
                    return 0.0
                elif existing_position.side == OrderSide.SELL:
                    # Short position, calculate how much to cover
                    return min(max_quantity, existing_position.quantity)
            
            return max_quantity
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    async def place_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                         quantity: float, price: Optional[float] = None,
                         stop_price: Optional[float] = None) -> Optional[PaperOrder]:
        """
        Place a paper trading order.
        
        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            order_type: Order type (market/limit/stop)
            quantity: Order quantity
            price: Order price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            PaperOrder if successful, None otherwise
        """
        try:
            # Validate order
            if not self._validate_order(symbol, side, order_type, quantity, price):
                return None
            
            # Check risk limits
            if not self._check_risk_limits(symbol, side, quantity, price):
                return None
            
            # Create order
            order_id = f"paper_{self.order_counter:06d}"
            self.order_counter += 1
            
            order = PaperOrder(
                id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price
            )
            
            # Store order
            self.orders[order_id] = order
            
            # Notify callbacks
            for callback in self.order_callbacks:
                callback(order)
            
            logger.info(f"Placed order: {order_id} {symbol} {side.value} {quantity} @ {price or 'MARKET'}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def _validate_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                       quantity: float, price: Optional[float]) -> bool:
        """Validate order parameters."""
        if quantity <= 0:
            logger.error("Invalid quantity")
            return False
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and price is None:
            logger.error("Price required for limit orders")
            return False
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and price is None:
            logger.error("Stop price required for stop orders")
            return False
        
        return True
    
    def _check_risk_limits(self, symbol: str, side: OrderSide, quantity: float,
                          price: Optional[float]) -> bool:
        """Check risk management limits."""
        try:
            # Check daily loss limit
            current_pnl = self._calculate_total_pnl()
            if current_pnl < -self.balance * self.max_daily_loss:
                logger.warning("Daily loss limit exceeded")
                return False
            
            # Check position count limit
            if len(self.positions) >= self.max_position_count:
                logger.warning("Maximum position count exceeded")
                return False
            
            # Check position size limit
            if price:
                position_value = quantity * price
                if position_value > self.balance * self.config.max_position_size:
                    logger.warning("Position size limit exceeded")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return False
    
    async def _process_pending_orders(self):
        """Process pending orders."""
        for order_id, order in list(self.orders.items()):
            if order.status == OrderStatus.PENDING:
                await self._try_fill_order(order)
    
    async def _try_fill_order(self, order: PaperOrder):
        """Try to fill an order."""
        try:
            current_price = self.current_prices.get(order.symbol)
            if not current_price:
                return
            
            # Check if order can be filled
            can_fill = False
            fill_price = current_price
            
            if order.order_type == OrderType.MARKET:
                can_fill = True
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and order.price >= current_price:
                    can_fill = True
                    fill_price = min(order.price, current_price)
                elif order.side == OrderSide.SELL and order.price <= current_price:
                    can_fill = True
                    fill_price = max(order.price, current_price)
            
            if can_fill:
                await self._fill_order(order, fill_price)
            
        except Exception as e:
            logger.error(f"Error trying to fill order: {e}")
    
    async def _fill_order(self, order: PaperOrder, fill_price: float):
        """Fill an order."""
        try:
            # Apply slippage
            if self.config.enable_slippage:
                slippage = fill_price * self.config.slippage_rate
                if order.side == OrderSide.BUY:
                    fill_price += slippage
                else:
                    fill_price -= slippage
            
            # Calculate commission
            commission = 0.0
            if self.config.enable_commission:
                commission = order.quantity * fill_price * self.config.commission_rate
            
            # Check if we have enough balance
            required_balance = order.quantity * fill_price + commission
            if order.side == OrderSide.BUY and required_balance > self.balance:
                logger.warning(f"Insufficient balance for order {order.id}")
                order.status = OrderStatus.REJECTED
                return
            
            # Create trade
            trade_id = f"trade_{self.trade_counter:06d}"
            self.trade_counter += 1
            
            trade = Trade(
                id=trade_id,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=fill_price,
                commission=commission
            )
            
            # Update order
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_fill_price = fill_price
            order.commission = commission
            order.filled_at = datetime.now()
            
            # Update balance
            if order.side == OrderSide.BUY:
                self.balance -= required_balance
            else:
                self.balance += order.quantity * fill_price - commission
            
            # Update position
            self._update_position(order, trade)
            
            # Store trade
            self.trades.append(trade)
            
            # Notify callbacks
            for callback in self.trade_callbacks:
                callback(trade)
            
            logger.info(f"Filled order: {order.id} {order.symbol} {order.quantity} @ {fill_price}")
            
        except Exception as e:
            logger.error(f"Error filling order: {e}")
    
    def _update_position(self, order: PaperOrder, trade: Trade):
        """Update position based on trade."""
        try:
            symbol = order.symbol
            
            if symbol not in self.positions:
                # Create new position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    side=order.side,
                    quantity=order.quantity,
                    average_price=trade.price
                )
            else:
                # Update existing position
                position = self.positions[symbol]
                
                if position.side == order.side:
                    # Same side - add to position
                    total_value = (position.quantity * position.average_price + 
                                 order.quantity * trade.price)
                    total_quantity = position.quantity + order.quantity
                    position.average_price = total_value / total_quantity
                    position.quantity = total_quantity
                else:
                    # Opposite side - reduce or close position
                    if order.quantity >= position.quantity:
                        # Close position and potentially reverse
                        remaining_quantity = order.quantity - position.quantity
                        
                        # Calculate realized PnL
                        if position.side == OrderSide.BUY:
                            realized_pnl = (trade.price - position.average_price) * position.quantity
                        else:
                            realized_pnl = (position.average_price - trade.price) * position.quantity
                        
                        position.realized_pnl += realized_pnl
                        
                        if remaining_quantity > 0:
                            # Reverse position
                            position.side = order.side
                            position.quantity = remaining_quantity
                            position.average_price = trade.price
                        else:
                            # Close position
                            del self.positions[symbol]
                            return
                    else:
                        # Partial close
                        if position.side == OrderSide.BUY:
                            realized_pnl = (trade.price - position.average_price) * order.quantity
                        else:
                            realized_pnl = (position.average_price - trade.price) * order.quantity
                        
                        position.realized_pnl += realized_pnl
                        position.quantity -= order.quantity
                
                position.updated_at = datetime.now()
            
            # Notify position callbacks
            if symbol in self.positions:
                for callback in self.position_callbacks:
                    callback(symbol, self.positions[symbol])
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")
    
    def _update_position_pnl(self, symbol: str):
        """Update unrealized PnL for position."""
        if symbol in self.positions and symbol in self.current_prices:
            position = self.positions[symbol]
            current_price = self.current_prices[symbol]
            
            if position.side == OrderSide.BUY:
                position.unrealized_pnl = (current_price - position.average_price) * position.quantity
            else:
                position.unrealized_pnl = (position.average_price - current_price) * position.quantity
            
            position.updated_at = datetime.now()
    
    def _calculate_total_pnl(self) -> float:
        """Calculate total PnL (realized + unrealized)."""
        total_pnl = 0.0
        
        for position in self.positions.values():
            total_pnl += position.realized_pnl + position.unrealized_pnl
        
        return total_pnl
    
    async def _cancel_all_orders(self):
        """Cancel all pending orders."""
        for order in self.orders.values():
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.now()
    
    async def _close_all_positions(self):
        """Close all positions at market price."""
        for symbol, position in list(self.positions.items()):
            if position.quantity > 0:
                opposite_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
                
                await self.place_order(
                    symbol=symbol,
                    side=opposite_side,
                    order_type=OrderType.MARKET,
                    quantity=position.quantity
                )
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        total_pnl = self._calculate_total_pnl()
        current_balance = self.balance + total_pnl
        
        # Calculate performance metrics
        total_return = (current_balance - self.start_balance) / self.start_balance
        
        # Update max drawdown
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        return {
            'initial_balance': self.start_balance,
            'current_balance': current_balance,
            'cash_balance': self.balance,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'max_drawdown': self.max_drawdown,
            'position_count': len(self.positions),
            'total_trades': len(self.trades),
            'active_orders': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING]),
            'start_time': self.start_time.isoformat(),
            'current_time': datetime.now().isoformat()
        }
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all positions."""
        return self.positions.copy()
    
    def get_orders(self) -> Dict[str, PaperOrder]:
        """Get all orders."""
        return self.orders.copy()
    
    def get_trades(self) -> List[Trade]:
        """Get all trades."""
        return self.trades.copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        portfolio_summary = self.get_portfolio_summary()
        
        # Calculate additional metrics
        if len(self.trades) > 0:
            winning_trades = [t for t in self.trades if self._get_trade_pnl(t) > 0]
            losing_trades = [t for t in self.trades if self._get_trade_pnl(t) < 0]
            
            win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
            
            avg_win = sum(self._get_trade_pnl(t) for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(self._get_trade_pnl(t) for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        return {
            **portfolio_summary,
            'win_rate': win_rate,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_commission': sum(t.commission for t in self.trades)
        }
    
    def _get_trade_pnl(self, trade: Trade) -> float:
        """Calculate PnL for a trade."""
        # This is a simplified calculation
        # In reality, you'd need to track the position that was closed
        return 0.0  # Placeholder
    
    def export_trades(self, format: str = 'json') -> Optional[str]:
        """Export trades in specified format."""
        try:
            trades_data = [trade.to_dict() for trade in self.trades]
            
            if format.lower() == 'json':
                return json.dumps(trades_data, indent=2)
            elif format.lower() == 'csv':
                df = pd.DataFrame(trades_data)
                return df.to_csv(index=False)
            else:
                logger.error(f"Unsupported export format: {format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting trades: {e}")
            return None
