"""
Real-Time WebSocket Data Feeder for Live Trading
Provides continuous real-time market data streams from multiple exchanges.
"""
import asyncio
import json
import websocket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
import pandas as pd
from loguru import logger
import ccxt

from ..core.config_manager import get_config_manager
from ..core.resilient_fetcher import ResilientFetcher


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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'trades': self.trades
        }


@dataclass
class MarketData:
    """Market data container for a symbol."""
    symbol: str
    current_price: float
    price_change_24h: float
    volume_24h: float
    last_update: datetime
    candles: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000 candles
    
    def add_candle(self, candle: RealtimeCandle):
        """Add new candle to the data."""
        self.candles.append(candle)
        self.current_price = candle.close
        self.last_update = candle.timestamp
    
    def get_recent_candles(self, count: int = 100) -> List[RealtimeCandle]:
        """Get recent candles."""
        return list(self.candles)[-count:]
    
    def to_dataframe(self, count: int = 100) -> pd.DataFrame:
        """Convert recent candles to pandas DataFrame."""
        recent_candles = self.get_recent_candles(count)
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
                'volume': candle.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


class BinanceWebsocketFeeder:
    """
    Real-time WebSocket data feeder for Binance.
    
    Features:
    - Real-time ticker and kline (candlestick) data
    - Automatic reconnection on failures
    - Multiple symbol support
    - Thread-safe data access
    - Callback system for real-time updates
    """
    
    def __init__(self, symbols: List[str], timeframe: str = '1m', stream_type: str = 'ticker'):
        """
        Initialize Binance WebSocket feeder.
        
        Args:
            symbols: List of symbols to subscribe to (e.g., ['BTCUSDT', 'ETHUSDT'])
            timeframe: Timeframe for klines ('1m', '5m', '1h', etc.)
            stream_type: Type of stream ('ticker' for real-time, 'kline' for OHLCV, 'both')
        """
        self.symbols = [s.replace('/', '').upper() for s in symbols]  # Convert BTC/USDT to BTCUSDT
        self.timeframe = timeframe
        self.stream_type = stream_type
        self.market_data: Dict[str, MarketData] = {}
        self.callbacks: List[Callable[[str, RealtimeCandle], None]] = []
        
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
        for symbol in self.symbols:
            self.market_data[symbol] = MarketData(
                symbol=symbol,
                current_price=0.0,
                price_change_24h=0.0,
                volume_24h=0.0,
                last_update=datetime.now()
            )
        
        logger.info(f"BinanceWebsocketFeeder initialized for {len(self.symbols)} symbols")
    
    def add_callback(self, callback: Callable[[str, RealtimeCandle], None]):
        """Add callback function for real-time updates."""
        self.callbacks.append(callback)
        logger.info(f"Added callback: {callback.__name__}")
    
    def _get_stream_url(self) -> str:
        """Generate WebSocket stream URL for all symbols."""
        streams = []
        for symbol in self.symbols:
            if self.stream_type == 'ticker':
                # Real-time ticker updates (more frequent)
                streams.append(f"{symbol.lower()}@ticker")
            elif self.stream_type == 'kline':
                # OHLCV candlestick data
                streams.append(f"{symbol.lower()}@kline_{self.timeframe}")
            elif self.stream_type == 'both':
                # Both ticker and kline streams
                streams.append(f"{symbol.lower()}@ticker")
                streams.append(f"{symbol.lower()}@kline_{self.timeframe}")
        
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
            
            # Process ticker data (real-time price updates)
            if 'c' in stream_data and 'k' not in stream_data:
                # This is ticker data - real-time price updates
                current_price = float(stream_data['c'])  # Current price
                price_change = float(stream_data.get('P', 0))  # Price change percent
                volume = float(stream_data.get('v', 0))  # 24h volume
                
                # Create RealtimeCandle with current timestamp for real-time updates
                candle = RealtimeCandle(
                    symbol=symbol,
                    timestamp=datetime.now(),  # Use current time for real-time updates
                    open=current_price,  # Use current price as OHLC for ticker updates
                    high=current_price,
                    low=current_price,
                    close=current_price,
                    volume=volume,
                    trades=int(stream_data.get('n', 0))
                )
                
                # Update market data thread-safely
                with self.data_lock:
                    if symbol in self.market_data:
                        self.market_data[symbol].current_price = current_price
                        self.market_data[symbol].price_change_24h = price_change
                        self.market_data[symbol].volume_24h = volume
                        self.market_data[symbol].last_update = datetime.now()
                
                # Notify callbacks with real-time updates
                for callback in self.callbacks:
                    try:
                        callback(symbol, candle)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                logger.debug(f"Ticker update {symbol}: ${current_price:.4f} at {candle.timestamp.strftime('%H:%M:%S')}")
            
            # Process kline data (candlestick data)
            elif 'k' in stream_data:
                kline = stream_data['k']
                
                # Create RealtimeCandle with kline timestamp
                candle = RealtimeCandle(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(kline['t'] / 1000),
                    open=float(kline['o']),
                    high=float(kline['h']),
                    low=float(kline['l']),
                    close=float(kline['c']),
                    volume=float(kline['v']),
                    trades=int(kline['n'])
                )
                
                # Update market data thread-safely
                with self.data_lock:
                    if symbol in self.market_data:
                        self.market_data[symbol].add_candle(candle)
                        self.market_data[symbol].current_price = candle.close
                        self.market_data[symbol].last_update = datetime.now()
                
                logger.debug(f"Kline update {symbol}: OHLCV candle at {candle.timestamp.strftime('%H:%M:%S')}")
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
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
        self.reconnect_attempts = 3
    
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
                
                logger.info(f"Starting WebSocket for {len(self.symbols)} symbols...")
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
        
        self.ws_thread = threading.Thread(target=run_websocket, daemon=True)
        self.ws_thread.start()
        
        logger.info("WebSocket feeder started")
    
    def stop(self):
        """Stop the WebSocket connection."""
        self.is_running = False
        
        # Cancel any pending reconnection timers
        for timer in self._cleanup_timers:
            if timer.is_alive():
                timer.cancel()
        self._cleanup_timers.clear()
        
        # Clear any pending reconnection attempts
        self.reconnect_attempts = self.max_reconnect_attempts + 1
        
        # Close WebSocket connection
        if self.ws:
            self.ws.close()
        
        # Wait for WebSocket thread to finish
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
            if self.ws_thread.is_alive():
                logger.warning("WebSocket thread did not stop within timeout")
        
        logger.info("WebSocket feeder stopped")
    
    def cleanup(self):
        """Clean up resources and ensure all threads are terminated."""
        self.stop()
        
        # Additional cleanup if needed
        self.callbacks.clear()
        self.market_data.clear()
    
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
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get current prices for all symbols."""
        with self.data_lock:
            return {symbol: data.current_price for symbol, data in self.market_data.items()}
    
    def get_recent_candles_df(self, symbol: str, count: int = 100) -> pd.DataFrame:
        """Get recent candles as DataFrame for analysis."""
        symbol = symbol.replace('/', '').upper()
        with self.data_lock:
            if symbol in self.market_data:
                return self.market_data[symbol].to_dataframe(count)
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
                    'candle_count': len(data.candles),
                    'is_fresh': self.is_data_fresh(symbol)
                }
        
        return {
            'is_running': self.is_running,
            'connected': self.ws is not None and self.ws.sock and self.ws.sock.connected if self.ws else False,
            'reconnect_attempts': self.reconnect_attempts,
            'symbols': symbol_status
        }


class MultiExchangeRealtimeFeeder:
    """
    Multi-exchange real-time data feeder.
    
    Manages real-time data feeds from multiple exchanges and provides
    a unified interface for accessing current market data.
    """
    
    def __init__(self, watchlist: List[str], timeframe: str = '1m'):
        """
        Initialize multi-exchange feeder.
        
        Args:
            watchlist: List of symbols to watch
            timeframe: Timeframe for data
        """
        self.watchlist = watchlist
        self.timeframe = timeframe
        self.feeders: Dict[str, Any] = {}
        self.is_running = False
        
        # Initialize Binance feeder
        self.feeders['binance'] = BinanceWebsocketFeeder(watchlist, timeframe)
        
        logger.info(f"MultiExchangeRealtimeFeeder initialized for {len(watchlist)} symbols")
    
    def add_price_callback(self, callback: Callable[[str, RealtimeCandle], None]):
        """Add callback for price updates."""
        for feeder in self.feeders.values():
            if hasattr(feeder, 'add_callback'):
                feeder.add_callback(callback)
    
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
    
    def get_all_current_prices(self, exchange: str = 'binance') -> Dict[str, float]:
        """Get all current prices from specific exchange."""
        if exchange in self.feeders:
            return self.feeders[exchange].get_all_prices()
        return {}
    
    def get_recent_data(self, symbol: str, count: int = 100, exchange: str = 'binance') -> pd.DataFrame:
        """Get recent candlestick data for analysis."""
        if exchange in self.feeders:
            return self.feeders[exchange].get_recent_candles_df(symbol, count)
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
            'exchanges': {}
        }
        
        for exchange, feeder in self.feeders.items():
            if hasattr(feeder, 'get_connection_status'):
                status['exchanges'][exchange] = feeder.get_connection_status()
        
        return status
