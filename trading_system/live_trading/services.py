"""
Trading Services - Decomposed services for focused responsibilities.

Replaces the monolithic LiveTradingEngine with smaller, focused services:
- MarketDataStreamer: Real-time data streaming
- SignalGeneratorService: Signal generation from data
- TradeExecutionService: Trade execution and management
- MonitoringService: Health monitoring and metrics
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from loguru import logger

from .interfaces import (
    IMarketDataStreamer,
    ISignalGeneratorService,
    ITradeExecutionService,
    IMonitoringService,
    IRealtimeFeeder
)


class IRealtimeFeeder:
    """Interface for realtime data feeder."""
    def start(self):
        """Start the data feed."""
        ...
    
    def stop(self):
        """Stop the data feed."""
        ...
    
    def add_event_callback(self, callback: Callable):
        """Add callback for data events."""
        ...
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        ...


class MarketDataStreamer(IMarketDataStreamer):
    """
    Service for streaming real-time market data.
    
    Responsibilities:
    - Manage realtime data feeds
    - Route data to subscribers
    - Handle connection lifecycle
    """
    
    def __init__(self, feeder: IRealtimeFeeder, watchlist: List[str]):
        """
        Initialize market data streamer.
        
        Args:
            feeder: Realtime data feeder implementation
            watchlist: Symbols to stream
        """
        self.feeder = feeder
        self.watchlist = watchlist
        self._callbacks: List[Callable] = []
        self._is_running = False
        
        logger.info(f"MarketDataStreamer initialized for {len(watchlist)} symbols")
    
    def start(self):
        """Start streaming market data."""
        if self._is_running:
            return
        
        self.feeder.add_event_callback(self._on_data_event)
        self.feeder.start()
        self._is_running = True
        logger.info("MarketDataStreamer started")
    
    def stop(self):
        """Stop streaming market data."""
        if not self._is_running:
            return
        
        self.feeder.stop()
        self._is_running = False
        logger.info("MarketDataStreamer stopped")
    
    def add_data_callback(self, callback: Callable):
        """Add callback for market data events."""
        self._callbacks.append(callback)
    
    def _on_data_event(self, event):
        """Handle incoming data event and notify subscribers."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error in MarketDataStreamer: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from feeder."""
        return self.feeder.get_current_price(symbol)
    
    def is_running(self) -> bool:
        """Check if streamer is running."""
        return self._is_running


class SignalGeneratorService(ISignalGeneratorService):
    """
    Service for generating trading signals from market data.
    
    Responsibilities:
    - Process market data
    - Generate trading signals
    - Manage signal cooldowns
    - Route signals to subscribers
    """
    
    def __init__(self, signal_processor):
        """
        Initialize signal generator service.
        
        Args:
            signal_processor: Signal processor implementation
        """
        self.signal_processor = signal_processor
        self._callbacks: List[Callable] = []
        self._last_signal_time: Dict[str, datetime] = {}
        self._cooldown_minutes = 15
        
        logger.info("SignalGeneratorService initialized")
    
    def set_cooldown(self, minutes: int):
        """Set signal cooldown period."""
        self._cooldown_minutes = minutes
    
    def add_signal_callback(self, callback: Callable):
        """Add callback for signals."""
        self._callbacks.append(callback)
    
    async def process_market_data(self, symbol: str, candle_data, current_price: float):
        """
        Process market data and generate signals.
        
        Args:
            symbol: Trading symbol
            candle_data: Candle data
            current_price: Current price
        """
        try:
            # Check cooldown
            if not self._should_process(symbol):
                return []
            
            # Generate signals
            signals = self.signal_processor.process_live_data(
                symbol, 
                candle_data, 
                current_price
            )
            
            if signals:
                self._last_signal_time[symbol] = datetime.now()
                await self._notify_signals(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            return []
    
    def _should_process(self, symbol: str) -> bool:
        """Check if we should process signals (cooldown logic)."""
        if symbol in self._last_signal_time:
            elapsed = (datetime.now() - self._last_signal_time[symbol]).total_seconds()
            if elapsed < self._cooldown_minutes * 60:
                return False
        return True
    
    async def _notify_signals(self, signals: List):
        """Notify subscribers about signals."""
        for signal in signals:
            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(signal)
                    else:
                        callback(signal)
                except Exception as e:
                    logger.error(f"Signal callback error: {e}")


class TradeExecutionService(ITradeExecutionService):
    """
    Service for executing trades.
    
    Responsibilities:
    - Execute trades through order manager
    - Handle retries and errors
    - Track execution state
    - Notify subscribers
    """
    
    def __init__(self, order_manager, portfolio_manager, paper_trading: bool = True):
        """
        Initialize trade execution service.
        
        Args:
            order_manager: Order manager implementation
            portfolio_manager: Portfolio manager
            paper_trading: Paper trading mode
        """
        self.order_manager = order_manager
        self.portfolio_manager = portfolio_manager
        self.paper_trading = paper_trading
        self._callbacks: List[Callable] = []
        self._max_retries = 3
        
        logger.info("TradeExecutionService initialized")
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for trade execution events."""
        self._callbacks.append(callback)
    
    async def execute_trade(self, risk_result) -> bool:
        """
        Execute a trade with retry logic.
        
        Args:
            risk_result: Risk calculation result
            
        Returns:
            True if trade executed successfully
        """
        retry_delay = 1.0
        
        for attempt in range(self._max_retries):
            try:
                # Create order request
                from .order_manager import OrderRequest, OrderType
                from ..core.position_state import SignalType
                
                order_request = OrderRequest(
                    symbol=risk_result.signal.symbol,
                    side='buy' if risk_result.signal.signal_type == SignalType.LONG else 'sell',
                    order_type=OrderType.MARKET,
                    quantity=risk_result.position_size,
                    leverage=risk_result.leverage,
                    test=self.paper_trading,
                    client_order_id=f"{risk_result.signal.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{attempt}"
                )
                
                # Add stop loss and take profit
                if hasattr(risk_result, 'stop_loss_price') and risk_result.stop_loss_price:
                    order_request.stop_loss_price = risk_result.stop_loss_price
                
                if hasattr(risk_result, 'take_profit_price') and risk_result.take_profit_price:
                    order_request.take_profit_price = risk_result.take_profit_price
                
                # Place order
                order_result = self.order_manager.place_order(order_request)
                
                if order_result.success:
                    logger.info(f"✅ Trade executed: {risk_result.signal.symbol}")
                    
                    # Update portfolio for paper trading
                    if self.paper_trading:
                        self.portfolio_manager.execute_trade(risk_result)
                    
                    await self._notify_execution(risk_result, order_result)
                    return True
                else:
                    logger.warning(f"⚠️ Trade failed (attempt {attempt + 1}): {order_result.error_message}")
                    
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(retry_delay)  # ✅ Use asyncio.sleep
                        retry_delay *= 2
                        continue
                    else:
                        return False
                        
            except Exception as e:
                logger.error(f"Trade execution error (attempt {attempt + 1}): {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(retry_delay)  # ✅ Use asyncio.sleep
                    retry_delay *= 2
                    continue
                else:
                    return False
        
        return False
    
    async def _notify_execution(self, risk_result, order_result):
        """Notify subscribers about trade execution."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'symbol': risk_result.signal.symbol,
            'signal_type': risk_result.signal.signal_type.value,
            'price': risk_result.current_price,
            'position_size': risk_result.position_size,
            'order_id': order_result.order_id,
            'paper_trading': self.paper_trading
        }
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")


class MonitoringService(IMonitoringService):
    """
    Service for monitoring system health and metrics.
    
    Responsibilities:
    - Monitor portfolio health
    - Check risk limits
    - Track performance metrics
    - Detect emergency conditions
    """
    
    def __init__(self, portfolio_manager, check_interval: int = 30):
        """
        Initialize monitoring service.
        
        Args:
            portfolio_manager: Portfolio manager
            check_interval: Monitoring interval in seconds
        """
        self.portfolio_manager = portfolio_manager
        self.check_interval = check_interval
        self._is_running = False
        self._callbacks: List[Callable] = []
        
        logger.info(f"MonitoringService initialized (interval: {check_interval}s)")
    
    def start(self):
        """Start monitoring."""
        self._is_running = True
        # Start as async task instead of thread
        asyncio.create_task(self._monitoring_loop())
        logger.info("MonitoringService started")
    
    def stop(self):
        """Stop monitoring."""
        self._is_running = False
        logger.info("MonitoringService stopped")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alerts."""
        self._callbacks.append(callback)
    
    async def _monitoring_loop(self):
        """Async monitoring loop."""
        while self._is_running:
            try:
                # Update portfolio metrics
                metrics = self.portfolio_manager.calculate_portfolio_metrics()
                
                # Check risk limits
                if not metrics.is_within_risk_limits:
                    await self._notify_alert({
                        'type': 'risk_limit',
                        'message': f"Risk limits exceeded: {metrics.portfolio_risk_percentage:.2f}%",
                        'metrics': metrics.to_dict()
                    })
                
                # Check emergency stop conditions
                if metrics.total_return_percent < -10:
                    await self._notify_alert({
                        'type': 'emergency',
                        'message': 'Emergency stop: 10% drawdown',
                        'metrics': metrics.to_dict()
                    })
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)  # ✅ Use asyncio.sleep
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # ✅ Use asyncio.sleep
    
    async def _notify_alert(self, alert: Dict):
        """Notify subscribers about alerts."""
        logger.warning(f"Alert: {alert['message']}")
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current portfolio metrics."""
        return self.portfolio_manager.calculate_portfolio_metrics().to_dict()

