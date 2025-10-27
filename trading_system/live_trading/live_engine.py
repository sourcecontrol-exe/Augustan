"""
Live Trading Engine - Integration of Real-Time Data and Risk Management

This is where real-time data meets intelligent risk management for live trading.
"""
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from loguru import logger

from ..data_feeder.realtime_feeder import RealtimeFeeder, RealtimeCandle, create_realtime_feeder
from ..risk_manager.portfolio_manager import PortfolioManager
from ..core.position_state import PositionManager, EnhancedSignal, SignalType, PositionState
from ..core.config_manager_refactored import ConfigManager
from ..core.exceptions import OrderError, NetworkError, handle_exception
from ..core.logging_config import StructuredLogger
from .signal_processor import LiveSignalProcessor
from .order_manager import OrderManager, OrderRequest, OrderType, OrderStatus


class LiveTradingEngine:
    """
    Live Trading Engine - The Heart of Real-Time Trading
    
    Integrates:
    1. Real-time WebSocket data feeds
    2. Signal generation from live data
    3. Risk management and position sizing
    4. Portfolio management
    5. Trade execution
    
    This engine runs continuously, processing real-time market data
    and making trading decisions based on configured strategies.
    """
    
    def __init__(self, watchlist: List[str] = None, initial_balance: float = None, 
                 config_path: Optional[str] = None, paper_trading: bool = None,
                 config_manager: Optional[ConfigManager] = None):
        """
        Initialize Live Trading Engine.
        
        Args:
            watchlist: List of symbols to trade (defaults to environment config)
            initial_balance: Starting account balance (defaults to environment config)
            config_path: Configuration file path (deprecated, use config_manager)
            paper_trading: If True, simulate trades without real execution (defaults to environment config)
            config_manager: Configuration manager instance (preferred over config_path)
        """
        # Initialize configuration - use dependency injection if provided
        if config_manager is None:
            # Backward compatibility: create from config_path or use testing config
            if config_path:
                self.config_manager = ConfigManager.create(config_path)
            else:
                self.config_manager = ConfigManager.create_for_testing(
                    overrides={'risk_management': {'default_budget': initial_balance or 10000.0}}
                )
        else:
            self.config_manager = config_manager
        
        # Extract configuration values
        self.watchlist = watchlist or ['BTC/USDT', 'ETH/USDT']  # Default watchlist
        self.initial_balance = initial_balance or self.config_manager.risk_management.default_budget
        self.paper_trading = paper_trading if paper_trading is not None else self.config_manager.is_paper_trading
        self.signal_config = self.config_manager.signal_generation
        
        # Initialize core components
        # Create realtime config for first symbol in watchlist
        realtime_config = {
            "timeframes": ["1m"],
            "symbol": watchlist[0] if watchlist else "BTCUSDT",
            "exchange": "binance",
            "max_lag_ms": 1500
        }
        self.realtime_feeder = create_realtime_feeder(realtime_config)
        self.portfolio_manager = PortfolioManager(initial_balance, config_path)
        self.signal_processor = LiveSignalProcessor(config_path)
        self.order_manager = OrderManager(config_path, testnet=paper_trading)
        
        # State management
        self.is_running = False
        self.last_signal_time: Dict[str, datetime] = {}
        self.trade_callbacks: List[Callable] = []
        
        # Performance tracking
        self.signals_generated = 0
        self.trades_executed = 0
        self.total_pnl = 0.0
        
        logger.info(f"LiveTradingEngine initialized - Watchlist: {len(watchlist)} symbols, "
                   f"Balance: ${initial_balance:.2f}, Paper Trading: {paper_trading}")
    
    def add_trade_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for trade events."""
        self.trade_callbacks.append(callback)
    
    def start(self):
        """Start the live trading engine."""
        if self.is_running:
            logger.warning("Trading engine already running")
            return
        
        logger.info("🚀 Starting Live Trading Engine...")
        self.is_running = True
        
        # Set up real-time data callback
        self.realtime_feeder.add_event_callback(self._on_price_update)
        
        # Set up order manager callbacks
        self.order_manager.add_fill_callback(self._on_order_filled)
        
        # Connect PortfolioManager to OrderManager
        self.order_manager.add_fill_callback(self.portfolio_manager.on_order_filled)
        
        # Start real-time data feeds
        self.realtime_feeder.start()
        
        # Start order monitoring
        self.order_manager.start_order_monitoring()
        
        # Start monitoring loop in separate thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("✅ Live Trading Engine started successfully")
    
    def stop(self):
        """Stop the live trading engine."""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping Live Trading Engine...")
        self.is_running = False
        
        # Stop real-time feeds
        self.realtime_feeder.stop()
        
        # Stop order monitoring
        self.order_manager.stop_order_monitoring()
        
        # Close all positions if in paper trading mode
        if self.paper_trading:
            self.portfolio_manager.emergency_stop()
        
        logger.info("✅ Live Trading Engine stopped")
    
    def _on_price_update(self, event):
        """
        Handle real-time price updates.
        
        This is called every time a new candlestick is received from the WebSocket.
        """
        # Extract symbol and candle from the event
        candle = event.data
        symbol = candle.symbol
        try:
            # Check if we should process signals for this symbol
            if not self._should_process_signal(symbol):
                return
            
            # Get recent data for signal generation
            recent_data = self.realtime_feeder.get_recent_data(symbol, candle.timeframe, count=100)
            if recent_data.empty:
                return
            
            # Generate signals from live data
            signals = self.signal_processor.process_live_data(symbol, recent_data, candle.close)
            
            for signal in signals:
                self._process_signal(signal, candle.close)
                
        except Exception as e:
            trading_error = handle_exception(e, context={'symbol': symbol, 'operation': 'price_update'})
            StructuredLogger.log_error(trading_error)
    
    def _should_process_signal(self, symbol: str) -> bool:
        """Check if we should process signals for this symbol (cooldown logic)."""
        cooldown_minutes = self.signal_config.signal_cooldown_minutes
        
        if symbol in self.last_signal_time:
            time_since_last = datetime.now() - self.last_signal_time[symbol]
            if time_since_last.total_seconds() < cooldown_minutes * 60:
                return False
        
        return True
    
    def _process_signal(self, signal: EnhancedSignal, current_price: float):
        """
        Process a trading signal through risk management.
        
        Args:
            signal: Generated trading signal
            current_price: Current market price
        """
        logger.info(f"📈 Processing signal: {signal.symbol} {signal.signal_type.value} "
                   f"at ${current_price:.4f} (confidence: {signal.confidence:.2f})")
        
        self.signals_generated += 1
        self.last_signal_time[signal.symbol] = datetime.now()
        
        # Skip non-actionable signals
        if not signal.is_actionable():
            logger.debug(f"Skipping non-actionable signal: {signal.signal_type.value}")
            return
        
        # Evaluate trade through portfolio manager (includes risk management)
        risk_result = self.portfolio_manager.evaluate_new_trade(
            signal, current_price, leverage=5  # Default 5x leverage
        )
        
        if not risk_result.is_safe_to_trade:
            logger.warning(f"❌ Trade rejected: {risk_result.rejection_reason}")
            return
        
        # Execute trade
        if self._execute_trade(risk_result):
            self.trades_executed += 1
            
            # Notify callbacks
            trade_event = {
                'timestamp': datetime.now().isoformat(),
                'symbol': signal.symbol,
                'signal_type': signal.signal_type.value,
                'price': current_price,
                'position_size': risk_result.position_size,
                'risk_amount': risk_result.risk_amount,
                'confidence': signal.confidence,
                'paper_trading': self.paper_trading
            }
            
            for callback in self.trade_callbacks:
                try:
                    callback(trade_event)
                except Exception as e:
                    logger.error(f"Trade callback error: {e}")
    
    def _execute_trade(self, risk_result) -> bool:
        """
        Execute a trade using OrderManager with enhanced error handling and retry logic.
        
        Args:
            risk_result: Risk calculation result
            
        Returns:
            True if trade executed successfully
        """
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                # Create order request with enhanced parameters
                order_request = OrderRequest(
                    symbol=risk_result.signal.symbol,
                    side='buy' if risk_result.signal.signal_type == SignalType.LONG else 'sell',
                    order_type=OrderType.MARKET,  # Use market orders for immediate execution
                    quantity=risk_result.position_size,
                    leverage=risk_result.leverage,
                    test=self.paper_trading,
                    client_order_id=f"{risk_result.signal.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{attempt}"
                )
                
                # Add stop loss and take profit if available
                if hasattr(risk_result, 'stop_loss_price') and risk_result.stop_loss_price:
                    order_request.stop_loss_price = risk_result.stop_loss_price
                
                if hasattr(risk_result, 'take_profit_price') and risk_result.take_profit_price:
                    order_request.take_profit_price = risk_result.take_profit_price
                
                # Place order through OrderManager
                order_result = self.order_manager.place_order(order_request)
                
                if order_result.success:
                    logger.info(f"✅ ORDER PLACED: {risk_result.signal.symbol} "
                               f"{risk_result.signal.signal_type.value} - "
                               f"Size: {risk_result.position_size:.6f}, "
                               f"Value: ${risk_result.position_value:.2f} "
                               f"(Order ID: {order_result.order_id}, Attempt: {attempt + 1})")
                    
                    # Update portfolio state immediately for paper trading
                    if self.paper_trading:
                        self.portfolio_manager.execute_trade(risk_result)
                    
                    # Track successful trade
                    self._track_trade_execution(risk_result, order_result)
                    
                    return True
                else:
                    logger.warning(f"⚠️ ORDER FAILED (Attempt {attempt + 1}/{max_retries}): "
                                  f"{risk_result.signal.symbol} - {order_result.error_message}")
                    
                    # Retry logic
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying order in {retry_delay} seconds...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"❌ ORDER FAILED AFTER {max_retries} ATTEMPTS: "
                                    f"{risk_result.signal.symbol} - {order_result.error_message}")
                        return False
                        
            except Exception as e:
                logger.error(f"Error executing trade (Attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return False
        
        return False
    
    def _track_trade_execution(self, risk_result, order_result):
        """Track trade execution for analytics and monitoring."""
        try:
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': risk_result.signal.symbol,
                'signal_type': risk_result.signal.signal_type.value,
                'signal_confidence': risk_result.signal.confidence,
                'position_size': risk_result.position_size,
                'position_value': risk_result.position_value,
                'risk_amount': risk_result.risk_amount,
                'leverage': risk_result.leverage,
                'order_id': order_result.order_id,
                'order_status': order_result.status.value,
                'filled_quantity': order_result.filled_quantity,
                'average_price': order_result.average_price,
                'commission': order_result.commission,
                'paper_trading': self.paper_trading,
                'execution_time_ms': (datetime.now() - risk_result.signal.timestamp).total_seconds() * 1000
            }
            
            # Store trade record (could be saved to database in production)
            if not hasattr(self, 'trade_records'):
                self.trade_records = []
            self.trade_records.append(trade_record)
            
            logger.debug(f"Trade execution tracked: {trade_record}")
            
        except Exception as e:
            logger.error(f"Error tracking trade execution: {e}")
    
    def _monitoring_loop(self):
        """Background monitoring loop for portfolio health and risk management."""
        import time
        
        while self.is_running:
            try:
                # Update portfolio metrics
                metrics = self.portfolio_manager.calculate_portfolio_metrics()
                
                # Check for risk limit violations
                if not metrics.is_within_risk_limits:
                    logger.warning(f"⚠️ Risk limits exceeded - Portfolio risk: {metrics.portfolio_risk_percentage:.2f}%")
                
                # Check for emergency stop conditions
                if metrics.total_return_percent < -10:  # 10% drawdown
                    logger.error("🚨 Emergency stop triggered - 10% drawdown exceeded")
                    if self.paper_trading:
                        self.portfolio_manager.emergency_stop()
                
                # Log periodic status
                if self.signals_generated > 0 and self.signals_generated % 10 == 0:
                    logger.info(f"📊 Status: {self.signals_generated} signals, "
                               f"{self.trades_executed} trades, "
                               f"Portfolio: ${metrics.total_account_balance:.2f}")
                
                # Update position PnLs with current prices
                self._update_position_pnls()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _on_order_filled(self, order_id: str, order_result):
        """
        Handle order fill events from OrderManager with enhanced portfolio synchronization.
        
        Args:
            order_id: Order ID that was filled
            order_result: Order result with fill details
        """
        try:
            # Get order details
            order_info = self.order_manager.active_orders.get(order_id)
            if not order_info:
                logger.warning(f"Order {order_id} not found in active orders")
                return
            
            order_request = order_info['order_request']
            symbol = order_request.symbol
            
            logger.info(f"🎯 ORDER FILLED: {symbol} - "
                       f"Quantity: {order_result.filled_quantity}, "
                       f"Price: ${order_result.average_price:.4f}, "
                       f"Commission: ${order_result.commission:.4f}")
            
            # Update portfolio state for both paper and real trading
            self._update_portfolio_on_fill(order_request, order_result)
            
            # Update trade records with fill information
            self._update_trade_record_on_fill(order_id, order_result)
            
            # Notify trade callbacks
            fill_event = {
                'timestamp': datetime.now().isoformat(),
                'order_id': order_id,
                'symbol': symbol,
                'side': order_request.side,
                'filled_quantity': order_result.filled_quantity,
                'average_price': order_result.average_price,
                'commission': order_result.commission,
                'paper_trading': self.paper_trading
            }
            
            for callback in self.trade_callbacks:
                try:
                    callback(fill_event)
                except Exception as e:
                    logger.error(f"Fill callback error: {e}")
            
        except Exception as e:
            logger.error(f"Error handling order fill: {e}")
    
    def _update_portfolio_on_fill(self, order_request, order_result):
        """Update portfolio state when an order is filled."""
        try:
            # Determine position state based on order side
            if order_request.side == 'buy':
                position_state = PositionState.LONG
            else:
                position_state = PositionState.SHORT
            
            # Update position in portfolio manager
            self.portfolio_manager.position_manager.set_position_state(
                order_request.symbol, 
                position_state
            )
            
            # Update position details
            if order_result.average_price:
                self.portfolio_manager.position_manager.update_position_entry_price(
                    order_request.symbol, 
                    order_result.average_price
                )
            
            if order_result.filled_quantity:
                self.portfolio_manager.position_manager.update_position_quantity(
                    order_request.symbol, 
                    order_result.filled_quantity
                )
            
            logger.info(f"✅ Portfolio updated for filled order: {order_request.symbol}")
            
        except Exception as e:
            logger.error(f"Error updating portfolio on fill: {e}")
    
    def _update_trade_record_on_fill(self, order_id: str, order_result):
        """Update trade record with fill information."""
        try:
            if hasattr(self, 'trade_records'):
                # Find the most recent trade record for this order
                for trade_record in reversed(self.trade_records):
                    if trade_record.get('order_id') == order_id:
                        trade_record.update({
                            'fill_timestamp': datetime.now().isoformat(),
                            'filled_quantity': order_result.filled_quantity,
                            'average_price': order_result.average_price,
                            'commission': order_result.commission,
                            'order_status': order_result.status.value
                        })
                        logger.debug(f"Updated trade record for order {order_id}")
                        break
        except Exception as e:
            logger.error(f"Error updating trade record on fill: {e}")
    
    def _update_position_pnls(self):
        """Update unrealized PnL for all positions."""
        active_positions = self.portfolio_manager.position_manager.get_active_positions()
        
        for symbol, position in active_positions.items():
            current_price = self.realtime_feeder.get_current_price(symbol)
            if current_price:
                self.portfolio_manager.position_manager.update_position_pnl(symbol, current_price)
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status."""
        portfolio_metrics = self.portfolio_manager.calculate_portfolio_metrics()
        realtime_status = self.realtime_feeder.get_system_status()
        order_manager_status = self.order_manager.get_system_status()
        
        # Get trade analytics
        trade_analytics = self.get_trade_analytics()
        
        return {
            'engine_info': {
                'is_running': self.is_running,
                'paper_trading': self.paper_trading,
                'watchlist_size': len(self.watchlist),
                'signals_generated': self.signals_generated,
                'trades_executed': self.trades_executed
            },
            'portfolio': portfolio_metrics.to_dict(),
            'realtime_feeds': realtime_status,
            'order_manager': order_manager_status,
            'performance': self.portfolio_manager.get_performance_stats(),
            'trade_analytics': trade_analytics,
            'last_updated': datetime.now().isoformat()
        }
    
    def force_close_position(self, symbol: str) -> bool:
        """Force close a position (emergency use)."""
        current_price = self.realtime_feeder.get_current_price(symbol)
        if not current_price:
            logger.error(f"Cannot close {symbol} - no current price available")
            return False
        
        result = self.portfolio_manager.close_position(symbol, current_price)
        if result:
            logger.info(f"✅ Force closed position: {symbol} - PnL: ${result.get('pnl', 0):.2f}")
            return True
        
        return False
    
    def get_trade_analytics(self) -> Dict[str, Any]:
        """Get trade analytics and performance metrics."""
        try:
            if not hasattr(self, 'trade_records') or not self.trade_records:
                return {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'failed_trades': 0,
                    'average_execution_time_ms': 0,
                    'total_commission': 0.0,
                    'symbols_traded': [],
                    'signal_types': {}
                }
            
            total_trades = len(self.trade_records)
            successful_trades = sum(1 for trade in self.trade_records if trade.get('order_status') == 'filled')
            failed_trades = total_trades - successful_trades
            
            # Calculate average execution time
            execution_times = [trade.get('execution_time_ms', 0) for trade in self.trade_records if trade.get('execution_time_ms')]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            # Calculate total commission
            total_commission = sum(trade.get('commission', 0) for trade in self.trade_records)
            
            # Get unique symbols traded
            symbols_traded = list(set(trade.get('symbol') for trade in self.trade_records))
            
            # Count signal types
            signal_types = {}
            for trade in self.trade_records:
                signal_type = trade.get('signal_type', 'unknown')
                signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
            
            return {
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'failed_trades': failed_trades,
                'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                'average_execution_time_ms': avg_execution_time,
                'total_commission': total_commission,
                'symbols_traded': symbols_traded,
                'signal_types': signal_types,
                'last_trade_time': max(trade.get('timestamp', '') for trade in self.trade_records) if self.trade_records else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade analytics: {e}")
            return {}
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get detailed portfolio summary."""
        return self.portfolio_manager.get_portfolio_summary()
    
    def set_emergency_stop(self):
        """Trigger emergency stop."""
        logger.warning("🚨 MANUAL EMERGENCY STOP TRIGGERED")
        self.portfolio_manager.emergency_stop()
    
    async def run_async(self, duration_minutes: Optional[int] = None):
        """
        Run the trading engine asynchronously.
        
        Args:
            duration_minutes: How long to run (None = indefinitely)
        """
        self.start()
        
        try:
            if duration_minutes:
                logger.info(f"Running trading engine for {duration_minutes} minutes...")
                await asyncio.sleep(duration_minutes * 60)
            else:
                logger.info("Running trading engine indefinitely...")
                while self.is_running:
                    await asyncio.sleep(10)
        finally:
            self.stop()
    
    def run_sync(self, duration_minutes: Optional[int] = None):
        """
        Run the trading engine synchronously.
        
        Args:
            duration_minutes: How long to run (None = indefinitely)
        """
        asyncio.run(self.run_async(duration_minutes))
