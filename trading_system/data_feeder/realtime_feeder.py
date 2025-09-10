"""
Real-Time WebSocket Data Feeder for Live Trading
Provides continuous real-time market data streams from multiple exchanges.
"""
import asyncio
import json
import websocket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from collections import deque
import pandas as pd
from loguru import logger
import ccxt
from enum import Enum

from ..core.config_manager import get_config_manager
from ..core.resilient_fetcher import ResilientFetcher


class EventType(Enum):
    """Event types for real-time data."""
    CANDLE_TICK = "CANDLE_TICK"
    CANDLE_CLOSED = "CANDLE_CLOSED"


@dataclass
class RealtimeCandle:
    """Real-time candlestick data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int = 0
    is_final: bool = False
    timeframe: str = "1m"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'trades': self.trades,
            'is_final': self.is_final,
            'timeframe': self.timeframe
        }


@dataclass
class RealtimeEvent:
    """Real-time event with type and data."""
    event_type: EventType
    timeframe: str
    data: RealtimeCandle
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type.value,
            'timeframe': self.timeframe,
            'data': self.data.to_dict(),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class RealtimeConfig:
    """Configuration for real-time data feeder."""
    timeframes: List[str] = field(default_factory=lambda: ["1m", "3m"])
    symbol: str = "BTCUSDT"
    exchange: str = "binance"
    max_lag_ms: int = 1500
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RealtimeConfig':
        """Create config from dictionary."""
        return cls(
            timeframes=config_dict.get("timeframes", ["1m", "3m"]),
            symbol=config_dict.get("symbol", "BTCUSDT"),
            exchange=config_dict.get("exchange", "binance"),
            max_lag_ms=config_dict.get("max_lag_ms", 1500)
        )


@dataclass
class MarketData:
    """Market data container for a symbol."""
    symbol: str
    current_price: float
    price_change_24h: float
    volume_24h: float
    last_update: datetime
    candles: Dict[str, deque] = field(default_factory=dict)  # timeframe -> candles
    closed_candle_ids: Set[str] = field(default_factory=set)  # Track closed candles to prevent duplicates
    
    def add_candle(self, candle: RealtimeCandle):
        """Add new candle to the data."""
        if candle.timeframe not in self.candles:
            self.candles[candle.timeframe] = deque(maxlen=1000)
        
        self.candles[candle.timeframe].append(candle)
        self.current_price = candle.close
        self.last_update = candle.timestamp
        
        # Track closed candles to prevent duplicates
        if candle.is_final:
            candle_id = f"{candle.timeframe}_{candle.timestamp.timestamp()}"
            self.closed_candle_ids.add(candle_id)
    
    def is_candle_closed(self, timeframe: str, timestamp: datetime) -> bool:
        """Check if a candle has already been marked as closed."""
        candle_id = f"{timeframe}_{timestamp.timestamp()}"
        return candle_id in self.closed_candle_ids
    
    def get_recent_candles(self, timeframe: str, count: int = 100) -> List[RealtimeCandle]:
        """Get recent candles for a specific timeframe."""
        if timeframe not in self.candles:
            return []
        return list(self.candles[timeframe])[-count:]
    
    def to_dataframe(self, timeframe: str, count: int = 100) -> pd.DataFrame:
        """Convert recent candles to pandas DataFrame."""
        recent_candles = self.get_recent_candles(timeframe, count)
        if not recent_candles:
            return pd.DataFrame()
        
        data = []
        for candle in recent_candles:
            data.append({
                'timestamp': candle.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.volume,
                'is_final': candle.is_final
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


class BinanceWebsocketFeeder:
    """
    Real-time WebSocket data feeder for Binance with support for multiple timeframes.
    
    Features:
    - Real-time kline (candlestick) data for multiple timeframes
    - Automatic reconnection on failures
    - Event-based system with CANDLE_TICK and CANDLE_CLOSED events
    - Thread-safe data access
    - Callback system for real-time updates
    - Duplicate prevention for closed candles
    """
    
    def __init__(self, config: RealtimeConfig):
        """
        Initialize Binance WebSocket feeder.
        
        Args:
            config: Configuration for the real-time feeder
        """
        self.config = config
        self.symbol = config.symbol.replace('/', '').upper()  # Convert BTC/USDT to BTCUSDT
        self.timeframes = config.timeframes
        self.market_data: Dict[str, MarketData] = {}
        self.event_callbacks: List[Callable[[RealtimeEvent], None]] = []
        
        # WebSocket connection management
        self.ws = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        # Threading
        self.ws_thread = None
        self.data_lock = threading.Lock()
        self._cleanup_timers = []  # Track cleanup timers
        
        # Initialize market data containers
        self.market_data[self.symbol] = MarketData(
            symbol=self.symbol,
            current_price=0.0,
            price_change_24h=0.0,
            volume_24h=0.0,
            last_update=datetime.now()
        )
        
        logger.info(f"BinanceWebsocketFeeder initialized for {self.symbol} with timeframes: {self.timeframes}")
    
    def add_event_callback(self, callback: Callable[[RealtimeEvent], None]):
        """Add callback function for real-time events."""
        self.event_callbacks.append(callback)
        logger.info(f"Added event callback: {callback.__name__}")
    
    def _get_stream_url(self) -> str:
        """Generate WebSocket stream URL for all timeframes."""
        streams = []
        for timeframe in self.timeframes:
            # Convert timeframe to Binance format (1m -> 1m, 3m -> 3m)
            binance_timeframe = timeframe
            streams.append(f"{self.symbol.lower()}@kline_{binance_timeframe}")
        
        stream_names = '/'.join(streams)
        return f"wss://stream.binance.com:9443/ws/{stream_names}"
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Handle single stream format
            if 'stream' in data:
                stream_data = data['data']
                stream_name = data['stream']
                symbol = stream_data['s']  # Symbol from the message
            else:
                # Handle direct data
                stream_data = data
                symbol = data['s']
                stream_name = 'direct'
            
            # Process kline data (candlestick data)
            if 'k' in stream_data:
                kline = stream_data['k']
                
                # Extract timeframe from stream name
                timeframe = kline['i']  # Interval (1m, 3m, etc.)
                
                # Create RealtimeCandle with kline timestamp
                candle = RealtimeCandle(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(kline['t'] / 1000),
                    open=float(kline['o']),
                    high=float(kline['h']),
                    low=float(kline['l']),
                    close=float(kline['c']),
                    volume=float(kline['v']),
                    trades=int(kline['n']),
                    is_final=kline['x'],  # isFinal flag from Binance
                    timeframe=timeframe
                )
                
                # Update market data thread-safely
                with self.data_lock:
                    if symbol in self.market_data:
                        self.market_data[symbol].add_candle(candle)
                        self.market_data[symbol].current_price = candle.close
                        self.market_data[symbol].last_update = datetime.now()
                
                # Emit events
                self._emit_events(candle)
                
                logger.debug(f"Kline update {symbol} {timeframe}: {'FINAL' if candle.is_final else 'PARTIAL'} at {candle.timestamp.strftime('%H:%M:%S')}")
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _emit_events(self, candle: RealtimeCandle):
        """Emit CANDLE_TICK and CANDLE_CLOSED events."""
        # Always emit CANDLE_TICK for every update
        tick_event = RealtimeEvent(
            event_type=EventType.CANDLE_TICK,
            timeframe=candle.timeframe,
            data=candle
        )
        self._notify_callbacks(tick_event)
        
        # Emit CANDLE_CLOSED only when candle is final and not already emitted
        if candle.is_final:
            with self.data_lock:
                if symbol in self.market_data:
                    if not self.market_data[symbol].is_candle_closed(candle.timeframe, candle.timestamp):
                        closed_event = RealtimeEvent(
                            event_type=EventType.CANDLE_CLOSED,
                            timeframe=candle.timeframe,
                            data=candle
                        )
                        self._notify_callbacks(closed_event)
                        logger.info(f"CANDLE_CLOSED emitted for {candle.symbol} {candle.timeframe} at {candle.timestamp}")
    
    def _notify_callbacks(self, event: RealtimeEvent):
        """Notify all registered callbacks with the event."""
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting reconnection #{self.reconnect_attempts} in {self.reconnect_delay}s...")
            timer = threading.Timer(self.reconnect_delay, self._reconnect)
            self._cleanup_timers.append(timer)
            timer.start()
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        logger.info("WebSocket connection established")
        self.reconnect_attempts = 0
    
    def _reconnect(self):
        """Reconnect to WebSocket."""
        if self.is_running:
            logger.info("Reconnecting to WebSocket...")
            self.start()
    
    def start(self):
        """Start the WebSocket connection."""
        if self.is_running:
            logger.warning("WebSocket feeder already running")
            return
        
        self.is_running = True
        
        def run_websocket():
            try:
                websocket.enableTrace(False)  # Set to True for debugging
                self.ws = websocket.WebSocketApp(
                    self._get_stream_url(),
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                logger.info(f"Starting WebSocket for {self.symbol} with timeframes: {self.timeframes}")
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
        
        self.ws_thread = threading.Thread(target=run_websocket, daemon=True)
        self.ws_thread.start()
        
        logger.info("WebSocket feeder started")
    
    def stop(self):
        """Stop the WebSocket connection."""
        logger.info("Stopping WebSocket feeder...")
        self.is_running = False
        
        # Cancel any pending reconnection timers
        for timer in self._cleanup_timers:
            if timer.is_alive():
                timer.cancel()
        self._cleanup_timers.clear()
        
        # Clear any pending reconnection attempts
        self.reconnect_attempts = self.max_reconnect_attempts + 1
        
        # Close WebSocket connection gracefully
        if self.ws:
            try:
                # Close with proper close code
                self.ws.close(code=1000, reason="Normal closure")
                logger.debug("WebSocket close() called")
            except Exception as e:
                logger.warning(f"Error during WebSocket close: {e}")
            finally:
                self.ws = None
        
        # Wait for WebSocket thread to finish with shorter timeout
        if self.ws_thread and self.ws_thread.is_alive():
            try:
                self.ws_thread.join(timeout=3)  # Reduced timeout
                if self.ws_thread.is_alive():
                    logger.warning("WebSocket thread did not stop within timeout - forcing cleanup")
                    # Force cleanup by setting thread to None
                    self.ws_thread = None
            except Exception as e:
                logger.warning(f"Error waiting for WebSocket thread: {e}")
        
        logger.info("WebSocket feeder stopped")
    
    def cleanup(self):
        """Clean up resources and ensure all threads are terminated."""
        logger.info("Cleaning up WebSocket feeder resources...")
        self.stop()
        
        # Additional cleanup if needed
        self.event_callbacks.clear()
        self.market_data.clear()
        
        # Clear any remaining references
        self._cleanup_timers.clear()
        logger.info("WebSocket feeder cleanup completed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        logger.info("Context manager exit - cleaning up WebSocket feeder")
        self.cleanup()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        symbol = symbol.replace('/', '').upper()
        with self.data_lock:
            if symbol in self.market_data:
                return self.market_data[symbol].current_price
        return None
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get complete market data for a symbol."""
        symbol = symbol.replace('/', '').upper()
        with self.data_lock:
            return self.market_data.get(symbol)
    
    def get_recent_candles_df(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        """Get recent candles as DataFrame for analysis."""
        symbol = symbol.replace('/', '').upper()
        with self.data_lock:
            if symbol in self.market_data:
                return self.market_data[symbol].to_dataframe(timeframe, count)
        return pd.DataFrame()
    
    def is_data_fresh(self, symbol: str, max_age_seconds: int = 60) -> bool:
        """Check if data for symbol is fresh (updated recently)."""
        symbol = symbol.replace('/', '').upper()
        with self.data_lock:
            if symbol in self.market_data:
                age = (datetime.now() - self.market_data[symbol].last_update).total_seconds()
                return age <= max_age_seconds
        return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status and statistics."""
        with self.data_lock:
            symbol_status = {}
            for symbol, data in self.market_data.items():
                symbol_status[symbol] = {
                    'current_price': data.current_price,
                    'last_update': data.last_update.isoformat(),
                    'timeframes': {tf: len(candles) for tf, candles in data.candles.items()},
                    'is_fresh': self.is_data_fresh(symbol)
                }
        
        return {
            'is_running': self.is_running,
            'connected': self.ws is not None and self.ws.sock and self.ws.sock.connected if self.ws else False,
            'reconnect_attempts': self.reconnect_attempts,
            'symbols': symbol_status,
            'timeframes': self.timeframes
        }


class RealtimeFeeder:
    """
    Main real-time data feeder that manages WebSocket connections and events.
    
    Features:
    - Configurable timeframes (1m, 3m, etc.)
    - Event-based system with CANDLE_TICK and CANDLE_CLOSED events
    - Automatic reconnection and error handling
    - Thread-safe data access
    - Duplicate prevention for closed candles
    """
    
    def __init__(self, config: RealtimeConfig):
        """
        Initialize real-time feeder.
        
        Args:
            config: Configuration for the real-time feeder
        """
        self.config = config
        self.feeders: Dict[str, BinanceWebsocketFeeder] = {}
        self.event_callbacks: List[Callable[[RealtimeEvent], None]] = []
        self.is_running = False
        
        # Initialize Binance feeder
        self.feeders['binance'] = BinanceWebsocketFeeder(config)
        
        logger.info(f"RealtimeFeeder initialized with config: {config}")
    
    def add_event_callback(self, callback: Callable[[RealtimeEvent], None]):
        """Add callback for real-time events."""
        self.event_callbacks.append(callback)
        
        # Forward callbacks to underlying feeders
        for feeder in self.feeders.values():
            feeder.add_event_callback(callback)
    
    def start(self):
        """Start all feeders."""
        if self.is_running:
            return
        
        self.is_running = True
        
        for exchange, feeder in self.feeders.items():
            try:
                feeder.start()
                logger.info(f"Started {exchange} feeder")
            except Exception as e:
                logger.error(f"Failed to start {exchange} feeder: {e}")
    
    def stop(self):
        """Stop all feeders."""
        self.is_running = False
        
        for exchange, feeder in self.feeders.items():
            try:
                feeder.stop()
                logger.info(f"Stopped {exchange} feeder")
            except Exception as e:
                logger.error(f"Failed to stop {exchange} feeder: {e}")
    
    def get_current_price(self, symbol: str, exchange: str = 'binance') -> Optional[float]:
        """Get current price from specific exchange."""
        if exchange in self.feeders:
            return self.feeders[exchange].get_current_price(symbol)
        return None
    
    def get_recent_data(self, symbol: str, timeframe: str, count: int = 100, exchange: str = 'binance') -> pd.DataFrame:
        """Get recent candlestick data for analysis."""
        if exchange in self.feeders:
            return self.feeders[exchange].get_recent_candles_df(symbol, timeframe, count)
        return pd.DataFrame()
    
    def is_symbol_active(self, symbol: str, exchange: str = 'binance') -> bool:
        """Check if symbol data is actively updating."""
        if exchange in self.feeders:
            return self.feeders[exchange].is_data_fresh(symbol)
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        status = {
            'is_running': self.is_running,
            'config': {
                'timeframes': self.config.timeframes,
                'symbol': self.config.symbol,
                'exchange': self.config.exchange,
                'max_lag_ms': self.config.max_lag_ms
            },
            'exchanges': {}
        }
        
        for exchange, feeder in self.feeders.items():
            if hasattr(feeder, 'get_connection_status'):
                status['exchanges'][exchange] = feeder.get_connection_status()
        
        return status


# Factory function for easy creation
def create_realtime_feeder(config_dict: Dict[str, Any]) -> RealtimeFeeder:
    """Create a real-time feeder from configuration dictionary."""
    config = RealtimeConfig.from_dict(config_dict)
    return RealtimeFeeder(config)


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    config = {
        "timeframes": ["1m", "3m"],
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "max_lag_ms": 1500
    }
    
    # Create feeder
    feeder = create_realtime_feeder(config)
    
    # Add event callback
    def on_event(event: RealtimeEvent):
        print(f"Event: {event.event_type.value} - {event.timeframe} - {event.data.symbol}")
    
    feeder.add_event_callback(on_event)
    
    # Start feeder
    feeder.start()
    
    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        feeder.stop()
        print("Feeder stopped")
