"""
Event-Driven Scalping Trading Engine
High-speed trading engine optimized for scalping strategies.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from loguru import logger

from ..data_feeder.realtime_feeder import RealtimeFeeder, create_realtime_feeder
from ..risk_manager.scalping_risk_manager import ScalpingRiskManager, ScalpingRiskConfig
from ..strategy_engine.scalping_strategies import ScalpingStrategyManager, ScalpingConfig
from ..core.position_state import EnhancedSignal, SignalType
from ..core.config_manager import ConfigManager
from .order_manager import OrderManager, OrderRequest, OrderType, OrderStatus
from .freqtrade_paper_engine import FreqtradePaperEngine, PaperTradingConfig


class ScalpingTradingEngine:
    """
    Event-Driven Scalping Trading Engine
    
    Features:
    - Event-driven architecture for ultra-fast execution
    - Multiple scalping strategies running simultaneously
    - ATR-based dynamic risk management
    - Trailing stops and position management
    - Real-time market data processing
    """
    
    def __init__(self, watchlist: List[str], initial_balance: float, 
                 config_path: Optional[str] = None, paper_trading: bool = True,
                 config_manager: Optional[ConfigManager] = None):
        """
        Initialize Scalping Trading Engine.
        
        Args:
            watchlist: List of symbols to trade
            initial_balance: Starting account balance
            config_path: Configuration file path (deprecated, use config_manager)
            paper_trading: If True, simulate trades without real execution
            config_manager: Configuration manager instance
        """
        self.watchlist = watchlist
        self.initial_balance = initial_balance
        self.paper_trading = paper_trading
        
        # Use dependency injection if provided
        if config_manager is None:
            if config_path:
                self.config_manager = ConfigManager.create(config_path)
            else:
                self.config_manager = ConfigManager.create_for_testing()
        else:
            self.config_manager = config_manager
        
        # Initialize components
        self.realtime_feeder = None
        self.risk_manager = ScalpingRiskManager()
        self.strategy_manager = ScalpingStrategyManager()
        
        # Use Freqtrade paper engine for paper trading
        if paper_trading:
            paper_config = PaperTradingConfig(initial_balance=initial_balance)
            self.paper_engine = FreqtradePaperEngine(paper_config)
            self.order_manager = None  # Not needed for paper trading
        else:
            self.order_manager = OrderManager(paper_trading=False)
            self.paper_engine = None
        
        # State tracking
        self.is_running = False
        self.account_balance = initial_balance
        self.positions: Dict[str, Dict] = {}
        self.pending_orders: Dict[str, List] = {}
        
        # Performance tracking
        self.trades_executed = 0
        self.total_pnl = 0.0
        self.start_time = None
        
        # Subscribe to events
        self._setup_event_subscriptions()
        
        logger.info(f"Scalping Trading Engine initialized for {len(watchlist)} symbols")
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions."""
        from ..core.event_system import EventType
        
        # Subscribe to candle closed events for all symbols
        for symbol in self.watchlist:
            self.subscribe(EventType.CANDLE_CLOSED, self.handle_candle_closed, symbol)
        
        # Subscribe to signal generated events
        self.subscribe(EventType.SIGNAL_GENERATED, self.handle_signal_generated)
        
        # Subscribe to order filled events
        self.subscribe(EventType.ORDER_FILLED, self.handle_order_filled)
    
    async def start(self):
        """Start the scalping trading engine."""
        if self.is_running:
            logger.warning("Scalping engine is already running")
            return
        
        logger.info("Starting Scalping Trading Engine...")
        
        try:
            # Event bus startup removed - deprecated global event system
            
            # Initialize realtime feeder
            self.realtime_feeder = create_realtime_feeder(
                symbols=self.watchlist,
                timeframes=['1m', '3m', '5m'],  # Scalping timeframes
                config_path=None  # Use default config
            )
            
            # Start realtime feeder
            feeder_task = asyncio.create_task(self.realtime_feeder.start())
            
            # Start order manager
            order_task = asyncio.create_task(self.order_manager.start())
            
            self.is_running = True
            self.start_time = datetime.now()
            
            logger.info("Scalping Trading Engine started successfully")
            
            # Wait for tasks
            await asyncio.gather(event_task, feeder_task, order_task)
            
        except Exception as e:
            logger.error(f"Error starting scalping engine: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the scalping trading engine."""
        if not self.is_running:
            return
        
        logger.info("Stopping Scalping Trading Engine...")
        
        self.is_running = False
        
        # Stop components
        if self.realtime_feeder:
            await self.realtime_feeder.stop()
        
        if self.order_manager:
            await self.order_manager.stop()
        
        # Event bus stopped - deprecated global event system
        
        # Cleanup
        self.cleanup()
        
        logger.info("Scalping Trading Engine stopped")
    
    async def handle_candle_closed(self, event: CandleClosedEvent):
        """Handle candle closed events."""
        if not self.is_running:
            return
        
        # Update market data for strategies
        symbol = event.symbol
        candle_data = event.candle_data
        
        logger.debug(f"Processing candle closed: {symbol} {event.timeframe} @ {candle_data.close}")
        
        # Strategies will automatically process this event through their subscriptions
    
    async def handle_signal_generated(self, event: SignalGeneratedEvent):
        """Handle signal generated events."""
        if not self.is_running:
            return
        
        symbol = event.symbol
        signal_data = event.signal_data
        strategy_name = event.strategy_name
        confidence = event.confidence
        
        logger.info(f"Signal received: {strategy_name} {signal_data['signal_type']} {symbol} @ {signal_data['entry_price']} (confidence: {confidence:.2f})")
        
        # Convert signal data back to EnhancedSignal
        signal = EnhancedSignal.from_dict(signal_data)
        
        # Check if we should process this signal
        if not self._should_process_signal(signal, confidence):
            logger.debug(f"Signal rejected for {symbol}: insufficient confidence or filters")
            return
        
        # Get recent market data for risk calculation
        market_data = await self._get_market_data(symbol)
        if market_data is None:
            logger.warning(f"No market data available for {symbol}")
            return
        
        # Calculate risk parameters
        risk_result = self.risk_manager.calculate_risk(
            signal=signal,
            current_price=signal_data['entry_price'],
            account_balance=self.account_balance,
            market_data=market_data
        )
        
        # Check if trade is safe
        if not risk_result.is_safe_to_trade:
            logger.warning(f"Trade rejected for {symbol}: {risk_result.rejection_reasons}")
            return
        
        # Log warnings
        if risk_result.safety_warnings:
            logger.warning(f"Trade warnings for {symbol}: {risk_result.safety_warnings}")
        
        # Execute trade
        await self._execute_trade(signal, risk_result)
    
    async def handle_order_filled(self, event: OrderFilledEvent):
        """Handle order filled events."""
        symbol = event.symbol
        side = event.side
        quantity = event.quantity
        price = event.price
        commission = event.commission
        
        logger.info(f"Order filled: {side} {quantity} {symbol} @ {price}")
        
        # Update position tracking
        if symbol not in self.positions:
            self.positions[symbol] = {
                'side': side,
                'quantity': quantity,
                'entry_price': price,
                'entry_time': event.timestamp,
                'stop_loss': None,
                'take_profit': None,
                'trailing_stop': None
            }
        else:
            # Update existing position
            pos = self.positions[symbol]
            if side != pos['side']:
                # Closing position - calculate P&L
                pnl = self._calculate_pnl(pos, price, quantity)
                self.total_pnl += pnl
                self.account_balance += pnl
                
                logger.info(f"Position closed for {symbol}: PnL ${pnl:.2f}, Total PnL ${self.total_pnl:.2f}")
                
                # Remove position
                del self.positions[symbol]
            else:
                # Adding to position
                pos['quantity'] += quantity
                pos['entry_price'] = (pos['entry_price'] * (pos['quantity'] - quantity) + price * quantity) / pos['quantity']
        
        self.trades_executed += 1
    
    def _should_process_signal(self, signal: EnhancedSignal, confidence: float) -> bool:
        """Check if signal should be processed."""
        # Minimum confidence threshold
        min_confidence = 0.6
        if confidence < min_confidence:
            return False
        
        # Check if we already have a position in this symbol
        if signal.symbol in self.positions:
            return False
        
        # Check if we have pending orders for this symbol
        if signal.symbol in self.pending_orders and len(self.pending_orders[signal.symbol]) > 0:
            return False
        
        return True
    
    async def _get_market_data(self, symbol: str) -> Optional[Any]:
        """Get recent market data for a symbol."""
        if not self.realtime_feeder:
            return None
        
        # Get market data from realtime feeder
        market_data = self.realtime_feeder.get_market_data(symbol)
        if not market_data:
            return None
        
        # Convert to DataFrame for risk calculations
        import pandas as pd
        
        candles = []
        for candle in market_data.recent_candles:
            candles.append({
                'timestamp': candle.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume
            })
        
        return pd.DataFrame(candles) if candles else None
    
    async def _execute_trade(self, signal: EnhancedSignal, risk_result):
        """Execute a trade based on signal and risk parameters."""
        symbol = signal.symbol
        side = 'buy' if signal.signal_type in [SignalType.BUY_OPEN, SignalType.BUY_CLOSE] else 'sell'
        
        if self.paper_trading:
            # Use Freqtrade paper engine
            try:
                order_id = await self.paper_engine.submit_order(
                    symbol=symbol,
                    side=side,
                    order_type='market',
                    quantity=risk_result.position_size
                )
                
                # Track pending order
                if symbol not in self.pending_orders:
                    self.pending_orders[symbol] = []
                self.pending_orders[symbol].append(order_id)
                
                logger.info(f"Paper order submitted: {order_id} {side} {risk_result.position_size} {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to submit paper order for {symbol}: {e}")
        else:
            # Use real order manager
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=risk_result.position_size,
                price=None,  # Market order
                stop_loss=risk_result.calculated_stop_loss,
                take_profit=risk_result.calculated_take_profit,
                trailing_stop=risk_result.trailing_stop_price if risk_result.trailing_stop_active else None
            )
            
            # Submit order
            order_id = await self.order_manager.submit_order(order_request)
            
            if order_id:
                # Track pending order
                if symbol not in self.pending_orders:
                    self.pending_orders[symbol] = []
                self.pending_orders[symbol].append(order_id)
                
                logger.info(f"Order submitted: {order_id} {side} {risk_result.position_size} {symbol}")
            else:
                logger.error(f"Failed to submit order for {symbol}")
    
    def _calculate_pnl(self, position: Dict, exit_price: float, exit_quantity: float) -> float:
        """Calculate P&L for a position."""
        if position['side'] == 'buy':
            return (exit_price - position['entry_price']) * exit_quantity
        else:
            return (position['entry_price'] - exit_price) * exit_quantity
    
    async def update_trailing_stops(self):
        """Update trailing stops for all active positions."""
        if not self.positions:
            return
        
        # Get current prices
        current_prices = {}
        for symbol in self.positions.keys():
            if self.realtime_feeder:
                market_data = self.realtime_feeder.get_market_data(symbol)
                if market_data:
                    current_prices[symbol] = market_data.current_price
        
        # Update trailing stops
        updated_stops = self.risk_manager.update_trailing_stops(current_prices)
        
        # Submit stop orders
        for symbol, stop_data in updated_stops.items():
            order_request = OrderRequest(
                symbol=symbol,
                side=stop_data['side'],
                order_type=OrderType.STOP_MARKET,
                quantity=stop_data['quantity'],
                price=None,
                stop_price=stop_data['stop_price']
            )
            
            order_id = await self.order_manager.submit_order(order_request)
            if order_id:
                logger.info(f"Trailing stop updated for {symbol}: {stop_data['stop_price']}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        runtime = datetime.now() - self.start_time if self.start_time else None
        
        if self.paper_trading and self.paper_engine:
            # Use paper engine data
            account_summary = self.paper_engine.get_account_summary()
            return {
                'runtime': str(runtime) if runtime else None,
                'trades_executed': account_summary['total_trades'],
                'total_pnl': account_summary['total_pnl'],
                'unrealized_pnl': account_summary['unrealized_pnl'],
                'account_balance': account_summary['balance'],
                'available_balance': account_summary['available_balance'],
                'active_positions': len(account_summary['positions']),
                'positions': account_summary['positions'],
                'win_rate': account_summary['win_rate'],
                'max_drawdown': account_summary['max_drawdown'],
                'risk_summary': self.risk_manager.get_risk_summary(),
                'is_running': self.is_running,
                'paper_trading': True
            }
        else:
            # Use live trading data
            return {
                'runtime': str(runtime) if runtime else None,
                'trades_executed': self.trades_executed,
                'total_pnl': self.total_pnl,
                'account_balance': self.account_balance,
                'active_positions': len(self.positions),
                'positions': self.positions.copy(),
                'risk_summary': self.risk_manager.get_risk_summary(),
                'is_running': self.is_running,
                'paper_trading': False
            }
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get strategy performance summary."""
        # This would track performance by strategy
        # For now, return basic info
        return {
            'strategies_active': len(self.strategy_manager.get_all_strategies()),
            'strategy_names': list(self.strategy_manager.get_all_strategies().keys())
        }
