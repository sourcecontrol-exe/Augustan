"""
Paper Trading Engine for Augustan Trading Bot

Provides virtual trading capabilities with real-time market data,
realistic order execution, and comprehensive performance tracking.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np

from ...data.services.data_service import DataService
from ...core.risk_management.risk_manager import RiskManager
from ...core.strategy.strategy import Strategy
from ...backtesting.metrics.performance_metrics import PerformanceAnalyzer
from ...data.feeds.live_data_feed import LiveDataManager, create_simple_feed


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class VirtualOrder:
    """Represents a virtual order in paper trading"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    commission: float = 0.0


@dataclass
class VirtualPosition:
    """Represents a virtual position in paper trading"""
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PaperTradingConfig:
    """Configuration for paper trading"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    execution_delay_ms: int = 100   # Realistic execution delay
    max_orders_per_minute: int = 10
    enable_partial_fills: bool = True
    min_order_size: float = 10.0
    max_position_size_pct: float = 0.1  # 10% of portfolio


class VirtualPortfolio:
    """Manages virtual portfolio state for paper trading"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, VirtualPosition] = {}
        self.equity_history: List[Tuple[datetime, float]] = []
        self.trade_history: List[Dict] = []
        
    def get_total_equity(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio equity"""
        equity = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                market_value = position.quantity * current_prices[symbol]
                equity += market_value
                
        return equity
    
    def get_position_value(self, symbol: str, current_price: float) -> float:
        """Get current value of a position"""
        if symbol not in self.positions:
            return 0.0
        return self.positions[symbol].quantity * current_price
    
    def update_unrealized_pnl(self, current_prices: Dict[str, float]):
        """Update unrealized PnL for all positions"""
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_value = position.quantity * current_prices[symbol]
                cost_basis = position.quantity * position.avg_price
                position.unrealized_pnl = current_value - cost_basis


class PaperTradingEngine:
    """Main paper trading engine"""
    
    def __init__(self, config: PaperTradingConfig, data_service: DataService, 
                 strategy: Strategy, risk_manager: RiskManager):
        self.config = config
        self.data_service = data_service
        self.strategy = strategy
        self.risk_manager = risk_manager
        
        self.portfolio = VirtualPortfolio(config.initial_capital)
        self.orders: Dict[str, VirtualOrder] = {}
        self.order_counter = 0
        
        self.is_running = False
        self.last_order_time = {}
        
        self.logger = logging.getLogger(__name__)
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Live data feed manager
        self.live_data_manager = LiveDataManager(data_service)
        self.live_feed = None
        
    def generate_order_id(self) -> str:
        """Generate unique order ID"""
        self.order_counter += 1
        return f"paper_{int(time.time())}_{self.order_counter}"
    
    def can_place_order(self, symbol: str) -> bool:
        """Check if we can place an order (rate limiting)"""
        now = datetime.now()
        last_time = self.last_order_time.get(symbol, now - timedelta(minutes=1))
        
        if (now - last_time).total_seconds() < 60 / self.config.max_orders_per_minute:
            return False
            
        return True
    
    def place_market_order(self, symbol: str, side: OrderSide, quantity: float) -> Optional[str]:
        """Place a market order"""
        if not self.can_place_order(symbol):
            self.logger.warning(f"Rate limit exceeded for {symbol}")
            return None
            
        if quantity < self.config.min_order_size:
            self.logger.warning(f"Order size {quantity} below minimum {self.config.min_order_size}")
            return None
            
        order_id = self.generate_order_id()
        order = VirtualOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity
        )
        
        self.orders[order_id] = order
        self.last_order_time[symbol] = datetime.now()
        
        # Try to fill immediately
        self._try_fill_order(order)
        
        return order_id
    
    def place_limit_order(self, symbol: str, side: OrderSide, quantity: float, price: float) -> Optional[str]:
        """Place a limit order"""
        if not self.can_place_order(symbol):
            return None
            
        order_id = self.generate_order_id()
        order = VirtualOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price
        )
        
        self.orders[order_id] = order
        self.last_order_time[symbol] = datetime.now()
        
        return order_id
    
    def _try_fill_order(self, order: VirtualOrder) -> bool:
        """Attempt to fill an order"""
        try:
            # Get current market price
            ticker = self.data_service.get_ticker(order.symbol)
            if not ticker:
                return False
                
            current_price = ticker.get('last', 0)
            if current_price <= 0:
                return False
            
            # Check if order can be filled
            can_fill = False
            fill_price = current_price
            
            if order.order_type == OrderType.MARKET:
                can_fill = True
                # Apply slippage
                if order.side == OrderSide.BUY:
                    fill_price *= (1 + self.config.slippage_rate)
                else:
                    fill_price *= (1 - self.config.slippage_rate)
                    
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    can_fill = True
                    fill_price = order.price
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    can_fill = True
                    fill_price = order.price
            
            if not can_fill:
                return False
                
            # Check if we have sufficient funds/position
            if not self._validate_order_execution(order, fill_price):
                order.status = OrderStatus.REJECTED
                return False
            
            # Execute the fill
            self._execute_fill(order, fill_price, order.quantity)
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling order {order.id}: {e}")
            return False
    
    def _validate_order_execution(self, order: VirtualOrder, fill_price: float) -> bool:
        """Validate if order can be executed"""
        if order.side == OrderSide.BUY:
            required_cash = order.quantity * fill_price * (1 + self.config.commission_rate)
            if self.portfolio.cash < required_cash:
                self.logger.warning(f"Insufficient cash for order {order.id}")
                return False
                
        elif order.side == OrderSide.SELL:
            position = self.portfolio.positions.get(order.symbol)
            if not position or position.quantity < order.quantity:
                self.logger.warning(f"Insufficient position for order {order.id}")
                return False
                
        return True
    
    def _execute_fill(self, order: VirtualOrder, fill_price: float, fill_quantity: float):
        """Execute order fill and update portfolio"""
        commission = fill_quantity * fill_price * self.config.commission_rate
        
        if order.side == OrderSide.BUY:
            # Update cash
            total_cost = fill_quantity * fill_price + commission
            self.portfolio.cash -= total_cost
            
            # Update position
            if order.symbol in self.portfolio.positions:
                position = self.portfolio.positions[order.symbol]
                total_quantity = position.quantity + fill_quantity
                total_cost_basis = (position.quantity * position.avg_price + 
                                  fill_quantity * fill_price)
                position.avg_price = total_cost_basis / total_quantity
                position.quantity = total_quantity
            else:
                self.portfolio.positions[order.symbol] = VirtualPosition(
                    symbol=order.symbol,
                    quantity=fill_quantity,
                    avg_price=fill_price
                )
                
        elif order.side == OrderSide.SELL:
            # Update cash
            proceeds = fill_quantity * fill_price - commission
            self.portfolio.cash += proceeds
            
            # Update position
            position = self.portfolio.positions[order.symbol]
            realized_pnl = fill_quantity * (fill_price - position.avg_price)
            position.realized_pnl += realized_pnl
            position.quantity -= fill_quantity
            
            # Remove position if fully closed
            if position.quantity <= 0:
                del self.portfolio.positions[order.symbol]
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_price = fill_price
        order.filled_quantity = fill_quantity
        order.commission = commission
        
        # Record trade
        self.portfolio.trade_history.append({
            'timestamp': order.filled_at,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': fill_quantity,
            'price': fill_price,
            'commission': commission,
            'order_id': order.id
        })
        
        self.logger.info(f"Order {order.id} filled: {order.side.value} {fill_quantity} {order.symbol} @ {fill_price}")
    
    async def run_paper_trading(self, symbols: List[str], duration_minutes: int = 60, use_live_feed: bool = True):
        """Run paper trading session with optional live data feed"""
        self.is_running = True
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        self.logger.info(f"Starting paper trading session for {duration_minutes} minutes")
        self.logger.info(f"Trading symbols: {symbols}")
        self.logger.info(f"Initial capital: ${self.config.initial_capital:,.2f}")
        self.logger.info(f"Live feed enabled: {use_live_feed}")
        
        # Setup live data feed if requested
        if use_live_feed:
            try:
                self.live_feed = create_simple_feed(symbols, self.data_service)
                await self.live_feed.start_feed()
                self.logger.info("Live data feed started")
            except Exception as e:
                self.logger.warning(f"Failed to start live feed, falling back to REST: {e}")
                use_live_feed = False
        
        try:
            while self.is_running and datetime.now() < end_time:
                # Get current prices (live feed or REST API)
                current_prices = {}
                if use_live_feed and self.live_feed:
                    # Use live feed data
                    live_prices = self.live_feed.get_latest_prices()
                    for symbol, market_data in live_prices.items():
                        current_prices[symbol] = market_data.price
                    
                    # Fallback to REST for missing symbols
                    for symbol in symbols:
                        if symbol not in current_prices:
                            ticker = self.data_service.get_ticker(symbol)
                            if ticker:
                                current_prices[symbol] = ticker.get('last', 0)
                else:
                    # Use REST API only
                    for symbol in symbols:
                        ticker = self.data_service.get_ticker(symbol)
                        if ticker:
                            current_prices[symbol] = ticker.get('last', 0)
                
                # Update portfolio metrics
                self.portfolio.update_unrealized_pnl(current_prices)
                total_equity = self.portfolio.get_total_equity(current_prices)
                self.portfolio.equity_history.append((datetime.now(), total_equity))
                
                # Process pending orders
                self._process_pending_orders()
                
                # Generate trading signals
                for symbol in symbols:
                    await self._process_trading_signals(symbol, current_prices.get(symbol, 0))
                
                # Wait before next iteration (shorter if using live feed)
                sleep_time = 2 if use_live_feed else 5
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("Paper trading session interrupted by user")
        except Exception as e:
            self.logger.error(f"Error in paper trading session: {e}")
        finally:
            # Stop live feed
            if self.live_feed:
                try:
                    await self.live_feed.stop_feed()
                    self.logger.info("Live data feed stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping live feed: {e}")
            
            self.is_running = False
            self._generate_session_report(current_prices)
    
    def _process_pending_orders(self):
        """Process all pending orders"""
        pending_orders = [order for order in self.orders.values() 
                         if order.status == OrderStatus.PENDING]
        
        for order in pending_orders:
            self._try_fill_order(order)
    
    async def _process_trading_signals(self, symbol: str, current_price: float):
        """Process trading signals for a symbol"""
        try:
            # Get recent data for strategy
            df = self.data_service.get_ohlcv(symbol, '1m', 100)
            if df is None or df.empty:
                return
            
            # Generate signal
            signal = self.strategy.generate_signal(df)
            
            if signal == 'BUY':
                # Calculate position size using risk manager
                trade_details = self.risk_manager.calculate_trade_details(df, signal)
                if trade_details and trade_details.get('position_size', 0) > 0:
                    # Check position size limits
                    max_position_value = self.portfolio.get_total_equity({symbol: current_price}) * self.config.max_position_size_pct
                    position_value = trade_details['position_size'] * current_price
                    
                    if position_value <= max_position_value:
                        self.place_market_order(symbol, OrderSide.BUY, trade_details['position_size'])
            
            elif signal == 'SELL':
                # Close existing position
                if symbol in self.portfolio.positions:
                    position = self.portfolio.positions[symbol]
                    if position.quantity > 0:
                        self.place_market_order(symbol, OrderSide.SELL, position.quantity)
                        
        except Exception as e:
            self.logger.error(f"Error processing signals for {symbol}: {e}")
    
    def _generate_session_report(self, current_prices: Dict[str, float]):
        """Generate comprehensive session report"""
        final_equity = self.portfolio.get_total_equity(current_prices)
        total_return = (final_equity - self.config.initial_capital) / self.config.initial_capital
        
        self.logger.info("=== PAPER TRADING SESSION REPORT ===")
        self.logger.info(f"Initial Capital: ${self.config.initial_capital:,.2f}")
        self.logger.info(f"Final Equity: ${final_equity:,.2f}")
        self.logger.info(f"Total Return: {total_return:.2%}")
        self.logger.info(f"Total Trades: {len(self.portfolio.trade_history)}")
        
        # Calculate performance metrics
        if len(self.portfolio.equity_history) > 1:
            equity_df = pd.DataFrame(self.portfolio.equity_history, columns=['timestamp', 'equity'])
            equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)
            
            if not equity_df['returns'].empty:
                metrics = self.performance_analyzer.calculate_metrics(
                    equity_df['equity'].values,
                    equity_df['returns'].values
                )
                
                self.logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.3f}")
                self.logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 'N/A'):.2%}")
                self.logger.info(f"Win Rate: {metrics.get('win_rate', 'N/A'):.2%}")
        
        # Show current positions
        if self.portfolio.positions:
            self.logger.info("\nCurrent Positions:")
            for symbol, position in self.portfolio.positions.items():
                current_price = current_prices.get(symbol, 0)
                market_value = position.quantity * current_price
                pnl = market_value - (position.quantity * position.avg_price)
                pnl_pct = pnl / (position.quantity * position.avg_price) if position.avg_price > 0 else 0
                
                self.logger.info(f"  {symbol}: {position.quantity:.4f} @ ${position.avg_price:.2f} "
                               f"(Current: ${current_price:.2f}, PnL: ${pnl:.2f} / {pnl_pct:.2%})")
    
    def stop_trading(self):
        """Stop paper trading session"""
        self.is_running = False
        self.logger.info("Paper trading session stopped")
    
    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict:
        """Get current portfolio summary"""
        total_equity = self.portfolio.get_total_equity(current_prices)
        
        return {
            'cash': self.portfolio.cash,
            'total_equity': total_equity,
            'total_return': (total_equity - self.config.initial_capital) / self.config.initial_capital,
            'positions': len(self.portfolio.positions),
            'total_trades': len(self.portfolio.trade_history),
            'pending_orders': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING])
        }
