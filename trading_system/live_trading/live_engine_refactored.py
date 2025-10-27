"""
Refactored Live Trading Engine - Decomposed architecture with dependency injection.

Uses focused services:
- MarketDataStreamer: Data streaming
- SignalGeneratorService: Signal generation
- TradeExecutionService: Trade execution
- MonitoringService: Health monitoring

Benefits:
- Lower coupling, higher cohesion
- Testable components
- Proper async design
- Clear interfaces
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from loguru import logger

from .services import (
    MarketDataStreamer,
    SignalGeneratorService,
    TradeExecutionService,
    MonitoringService
)
from .signal_processor import LiveSignalProcessor
from .order_manager import OrderManager, OrderRequest, OrderType
from ..risk_manager.portfolio_manager import PortfolioManager
from ..core.position_state import EnhancedSignal, SignalType
from ..core.config_manager_refactored import ConfigManager


class LiveTradingEngineRefactored:
    """
    Refactored Live Trading Engine with decomposed architecture.
    
    Uses focused services with dependency injection:
    - MarketDataStreamer: Handles data streaming
    - SignalGeneratorService: Generates signals
    - TradeExecutionService: Executes trades
    - MonitoringService: Monitors health
    
    Benefits over old system:
    - Lower coupling between components
    - Easier to test (can mock services)
    - Proper async throughout
    - Clear separation of responsibilities
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        watchlist: List[str],
        initial_balance: float,
        paper_trading: bool = True,
        # Dependencies (injectable)
        market_streamer: Optional[MarketDataStreamer] = None,
        signal_service: Optional[SignalGeneratorService] = None,
        execution_service: Optional[TradeExecutionService] = None,
        monitoring_service: Optional[MonitoringService] = None
    ):
        """
        Initialize refactored trading engine.
        
        Args:
            config_manager: Configuration manager
            watchlist: Trading symbols
            initial_balance: Starting balance
            paper_trading: Paper trading mode
            market_streamer: Optional pre-configured streamer
            signal_service: Optional pre-configured signal service
            execution_service: Optional pre-configured execution service
            monitoring_service: Optional pre-configured monitoring service
        """
        self.config_manager = config_manager
        self.watchlist = watchlist
        self.initial_balance = initial_balance
        self.paper_trading = paper_trading
        self.signal_config = config_manager.signal_generation
        
        # Initialize services with dependency injection
        self._initialize_services(
            market_streamer,
            signal_service,
            execution_service,
            monitoring_service
        )
        
        # State
        self._is_running = False
        self._signals_generated = 0
        self._trades_executed = 0
        self._callbacks: List[Callable] = []
        
        logger.info(f"LiveTradingEngine initialized: {len(watchlist)} symbols, "
                   f"${initial_balance:.2f}, paper={paper_trading}")
    
    def _initialize_services(
        self,
        market_streamer: Optional[MarketDataStreamer],
        signal_service: Optional[SignalGeneratorService],
        execution_service: Optional[TradeExecutionService],
        monitoring_service: Optional[MonitoringService]
    ):
        """Initialize services with dependency injection."""
        # Create dependencies for services
        from ..data_feeder.realtime_feeder import create_realtime_feeder
        from ..data_feeder.realtime_feeder import RealtimeFeeder
        
        # Market data streamer
        if market_streamer is None:
            realtime_config = {
                "timeframes": ["1m"],
                "symbol": self.watchlist[0] if self.watchlist else "BTCUSDT",
                "exchange": "binance",
                "max_lag_ms": 1500
            }
            feeder = create_realtime_feeder(realtime_config)
            self.market_streamer = MarketDataStreamer(feeder, self.watchlist)
        else:
            self.market_streamer = market_streamer
        
        # Signal generator service
        if signal_service is None:
            signal_processor = LiveSignalProcessor()
            self.signal_service = SignalGeneratorService(signal_processor)
            self.signal_service.set_cooldown(self.signal_config.signal_cooldown_minutes)
        else:
            self.signal_service = signal_service
        
        # Trade execution service
        if execution_service is None:
            portfolio_manager = PortfolioManager(self.initial_balance)
            order_manager = OrderManager(testnet=self.paper_trading)
            self.execution_service = TradeExecutionService(
                order_manager,
                portfolio_manager,
                self.paper_trading
            )
        else:
            self.execution_service = execution_service
        
        # Monitoring service
        if monitoring_service is None:
            self.monitoring_service = MonitoringService(
                self.execution_service.portfolio_manager
            )
        else:
            self.monitoring_service = monitoring_service
        
        # Connect services
        self._connect_services()
    
    def _connect_services(self):
        """Connect services together."""
        # Data streamer -> Signal generator
        self.market_streamer.add_data_callback(self._on_data_event)
        
        # Signal generator -> Trade executor
        self.signal_service.add_signal_callback(self._on_signal)
        
        # Monitoring alerts
        self.monitoring_service.add_alert_callback(self._on_alert)
    
    def add_trade_callback(self, callback: Callable):
        """Add callback for trade events."""
        self._callbacks.append(callback)
        self.execution_service.add_execution_callback(callback)
    
    async def start(self):
        """Start the trading engine."""
        if self._is_running:
            logger.warning("Engine already running")
            return
        
        logger.info("🚀 Starting Live Trading Engine (Refactored)...")
        self._is_running = True
        
        # Start all services
        self.market_streamer.start()
        self.monitoring_service.start()
        
        # Start order monitoring
        self.execution_service.order_manager.start_order_monitoring()
        
        logger.info("✅ Live Trading Engine started successfully")
    
    async def stop(self):
        """Stop the trading engine."""
        if not self._is_running:
            return
        
        logger.info("🛑 Stopping Live Trading Engine...")
        self._is_running = False
        
        # Stop all services
        self.market_streamer.stop()
        self.monitoring_service.stop()
        self.execution_service.order_manager.stop_order_monitoring()
        
        logger.info("✅ Live Trading Engine stopped")
    
    async def _on_data_event(self, event):
        """Handle data events from market streamer."""
        try:
            candle = event.data
            symbol = candle.symbol
            
            # Get recent data
            recent_data = self.market_streamer.feeder.get_recent_data(
                symbol, candle.timeframe, count=100
            )
            
            if recent_data.empty:
                return
            
            # Process through signal service
            signals = await self.signal_service.process_market_data(
                symbol,
                recent_data,
                candle.close
            )
            
            self._signals_generated += len(signals)
            
        except Exception as e:
            logger.error(f"Error processing data event: {e}")
    
    async def _on_signal(self, signal: EnhancedSignal):
        """Handle signal from signal service."""
        try:
            # Get current price
            current_price = self.market_streamer.get_current_price(signal.symbol)
            if not current_price:
                return
            
            # Evaluate through portfolio manager
            risk_result = self.execution_service.portfolio_manager.evaluate_new_trade(
                signal, current_price, leverage=5
            )
            
            if not risk_result.is_safe_to_trade:
                logger.warning(f"❌ Trade rejected: {risk_result.rejection_reason}")
                return
            
            # Execute trade
            success = await self.execution_service.execute_trade(risk_result)
            if success:
                self._trades_executed += 1
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def _on_alert(self, alert: Dict):
        """Handle alerts from monitoring service."""
        logger.warning(f"Alert: {alert['message']}")
        
        if alert['type'] == 'emergency':
            logger.error("🚨 Emergency stop triggered")
            if self.paper_trading:
                self.execution_service.portfolio_manager.emergency_stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            'is_running': self._is_running,
            'paper_trading': self.paper_trading,
            'watchlist_size': len(self.watchlist),
            'signals_generated': self._signals_generated,
            'trades_executed': self._trades_executed,
            'portfolio_metrics': self.monitoring_service.get_metrics()
        }
    
    async def run(self, duration_minutes: Optional[int] = None):
        """
        Run the engine for a specified duration.
        
        Args:
            duration_minutes: Duration in minutes (None = indefinite)
        """
        await self.start()
        
        try:
            if duration_minutes:
                logger.info(f"Running for {duration_minutes} minutes...")
                await asyncio.sleep(duration_minutes * 60)
            else:
                # Run indefinitely
                while self._is_running:
                    await asyncio.sleep(10)
        finally:
            await self.stop()

