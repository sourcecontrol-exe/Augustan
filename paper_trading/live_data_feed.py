"""
Live Data Feed Manager for Paper Trading

Provides real-time market data feeds using multiple sources:
- WebSocket streams for real-time prices
- REST API fallback for reliability
- Multiple exchange support with failover
"""

import asyncio
import websockets
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor

from data_service import DataService


class FeedStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MarketData:
    """Real-time market data structure"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    timestamp: datetime
    source: str


@dataclass
class FeedConfig:
    """Configuration for live data feeds"""
    symbols: List[str] = field(default_factory=list)
    update_interval_ms: int = 1000  # 1 second
    reconnect_attempts: int = 5
    reconnect_delay_seconds: int = 5
    enable_websocket: bool = True
    enable_rest_fallback: bool = True
    rest_poll_interval_seconds: int = 5
    max_price_age_seconds: int = 30


class LiveDataFeed:
    """Manages live market data feeds for paper trading"""
    
    def __init__(self, config: FeedConfig, data_service: DataService):
        self.config = config
        self.data_service = data_service
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self.latest_prices: Dict[str, MarketData] = {}
        self.price_callbacks: List[Callable[[MarketData], None]] = []
        
        # Connection management
        self.status = FeedStatus.DISCONNECTED
        self.websocket_connection = None
        self.is_running = False
        self.reconnect_count = 0
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.websocket_task = None
        self.rest_task = None
        
    def add_price_callback(self, callback: Callable[[MarketData], None]):
        """Add callback to receive price updates"""
        self.price_callbacks.append(callback)
        
    def remove_price_callback(self, callback: Callable[[MarketData], None]):
        """Remove price callback"""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)
    
    def get_latest_price(self, symbol: str) -> Optional[MarketData]:
        """Get latest price for a symbol"""
        data = self.latest_prices.get(symbol)
        if data and self._is_data_fresh(data):
            return data
        return None
    
    def get_latest_prices(self) -> Dict[str, MarketData]:
        """Get all latest prices"""
        fresh_prices = {}
        for symbol, data in self.latest_prices.items():
            if self._is_data_fresh(data):
                fresh_prices[symbol] = data
        return fresh_prices
    
    def _is_data_fresh(self, data: MarketData) -> bool:
        """Check if market data is fresh enough"""
        age = (datetime.now() - data.timestamp).total_seconds()
        return age <= self.config.max_price_age_seconds
    
    def _notify_callbacks(self, market_data: MarketData):
        """Notify all callbacks of new price data"""
        for callback in self.price_callbacks:
            try:
                callback(market_data)
            except Exception as e:
                self.logger.error(f"Error in price callback: {e}")
    
    def _update_price(self, symbol: str, price: float, bid: float = None, 
                     ask: float = None, volume: float = None, source: str = "unknown"):
        """Update price data and notify callbacks"""
        market_data = MarketData(
            symbol=symbol,
            price=price,
            bid=bid or price,
            ask=ask or price,
            volume=volume or 0,
            timestamp=datetime.now(),
            source=source
        )
        
        self.latest_prices[symbol] = market_data
        self._notify_callbacks(market_data)
        
        self.logger.debug(f"Updated {symbol}: ${price:.4f} from {source}")
    
    async def start_feed(self):
        """Start the live data feed"""
        if self.is_running:
            self.logger.warning("Feed is already running")
            return
            
        self.is_running = True
        self.status = FeedStatus.CONNECTING
        
        self.logger.info(f"Starting live data feed for {len(self.config.symbols)} symbols")
        
        try:
            # Start WebSocket feed if enabled
            if self.config.enable_websocket:
                self.websocket_task = asyncio.create_task(self._websocket_feed())
            
            # Start REST fallback if enabled
            if self.config.enable_rest_fallback:
                self.rest_task = asyncio.create_task(self._rest_feed())
            
            self.status = FeedStatus.CONNECTED
            self.logger.info("Live data feed started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting live feed: {e}")
            self.status = FeedStatus.ERROR
            raise
    
    async def stop_feed(self):
        """Stop the live data feed"""
        self.is_running = False
        
        # Cancel tasks
        if self.websocket_task:
            self.websocket_task.cancel()
        if self.rest_task:
            self.rest_task.cancel()
        
        # Close WebSocket connection
        if self.websocket_connection:
            await self.websocket_connection.close()
            
        self.status = FeedStatus.DISCONNECTED
        self.logger.info("Live data feed stopped")
    
    async def _websocket_feed(self):
        """WebSocket-based real-time feed"""
        while self.is_running:
            try:
                await self._connect_websocket()
                await self._websocket_listen()
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                await self._handle_websocket_reconnect()
    
    async def _connect_websocket(self):
        """Connect to WebSocket feed"""
        # Binance WebSocket example (you can add more exchanges)
        if self.data_service.exchange_name == 'ccxt':
            await self._connect_binance_websocket()
        else:
            self.logger.warning(f"WebSocket not implemented for {self.data_service.exchange_name}")
            raise NotImplementedError(f"WebSocket for {self.data_service.exchange_name}")
    
    async def _connect_binance_websocket(self):
        """Connect to Binance WebSocket stream"""
        # Create stream names for all symbols
        streams = []
        for symbol in self.config.symbols:
            # Convert BTC/USDT to btcusdt format
            binance_symbol = symbol.replace('/', '').lower()
            streams.append(f"{binance_symbol}@ticker")
        
        stream_names = '/'.join(streams)
        ws_url = f"wss://stream.binance.com:9443/ws/{stream_names}"
        
        self.logger.info(f"Connecting to Binance WebSocket: {ws_url}")
        self.websocket_connection = await websockets.connect(ws_url)
        self.logger.info("Connected to Binance WebSocket")
    
    async def _websocket_listen(self):
        """Listen to WebSocket messages"""
        async for message in self.websocket_connection:
            try:
                data = json.loads(message)
                await self._process_websocket_message(data)
            except Exception as e:
                self.logger.error(f"Error processing WebSocket message: {e}")
    
    async def _process_websocket_message(self, data: Dict):
        """Process incoming WebSocket message"""
        try:
            if 'stream' in data and 'data' in data:
                # Binance stream format
                stream_data = data['data']
                symbol_raw = stream_data.get('s', '')
                
                # Convert back to standard format (BTCUSDT -> BTC/USDT)
                if len(symbol_raw) >= 6:
                    if symbol_raw.endswith('USDT'):
                        base = symbol_raw[:-4]
                        symbol = f"{base}/USDT"
                    else:
                        # Handle other quote currencies if needed
                        symbol = symbol_raw
                else:
                    symbol = symbol_raw
                
                if symbol in self.config.symbols:
                    price = float(stream_data.get('c', 0))  # Current price
                    bid = float(stream_data.get('b', price))  # Best bid
                    ask = float(stream_data.get('a', price))  # Best ask
                    volume = float(stream_data.get('v', 0))   # Volume
                    
                    self._update_price(symbol, price, bid, ask, volume, "websocket")
                    
        except Exception as e:
            self.logger.error(f"Error processing WebSocket data: {e}")
    
    async def _handle_websocket_reconnect(self):
        """Handle WebSocket reconnection"""
        if self.reconnect_count >= self.config.reconnect_attempts:
            self.logger.error("Max reconnection attempts reached")
            self.status = FeedStatus.ERROR
            return
        
        self.reconnect_count += 1
        self.logger.info(f"Reconnecting WebSocket (attempt {self.reconnect_count})")
        
        await asyncio.sleep(self.config.reconnect_delay_seconds)
        
        if self.websocket_connection:
            await self.websocket_connection.close()
            self.websocket_connection = None
    
    async def _rest_feed(self):
        """REST API fallback feed"""
        while self.is_running:
            try:
                await self._fetch_rest_prices()
                await asyncio.sleep(self.config.rest_poll_interval_seconds)
            except Exception as e:
                self.logger.error(f"REST feed error: {e}")
                await asyncio.sleep(self.config.rest_poll_interval_seconds)
    
    async def _fetch_rest_prices(self):
        """Fetch prices via REST API"""
        for symbol in self.config.symbols:
            try:
                # Check if we have fresh WebSocket data
                if symbol in self.latest_prices and self._is_data_fresh(self.latest_prices[symbol]):
                    continue  # Skip if WebSocket data is fresh
                
                # Fetch via REST API
                ticker = self.data_service.get_ticker(symbol)
                if ticker:
                    price = ticker.get('last', 0)
                    bid = ticker.get('bid', price)
                    ask = ticker.get('ask', price)
                    volume = ticker.get('baseVolume', 0)
                    
                    if price > 0:
                        self._update_price(symbol, price, bid, ask, volume, "rest_api")
                        
            except Exception as e:
                self.logger.error(f"Error fetching REST price for {symbol}: {e}")


class LiveDataManager:
    """High-level manager for live data feeds"""
    
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.logger = logging.getLogger(__name__)
        self.feeds: Dict[str, LiveDataFeed] = {}
        
    def create_feed(self, symbols: List[str], feed_name: str = "default") -> LiveDataFeed:
        """Create a new live data feed"""
        config = FeedConfig(symbols=symbols)
        feed = LiveDataFeed(config, self.data_service)
        self.feeds[feed_name] = feed
        
        self.logger.info(f"Created live feed '{feed_name}' for {len(symbols)} symbols")
        return feed
    
    def get_feed(self, feed_name: str = "default") -> Optional[LiveDataFeed]:
        """Get an existing feed"""
        return self.feeds.get(feed_name)
    
    async def start_all_feeds(self):
        """Start all feeds"""
        for name, feed in self.feeds.items():
            try:
                await feed.start_feed()
                self.logger.info(f"Started feed: {name}")
            except Exception as e:
                self.logger.error(f"Failed to start feed {name}: {e}")
    
    async def stop_all_feeds(self):
        """Stop all feeds"""
        for name, feed in self.feeds.items():
            try:
                await feed.stop_feed()
                self.logger.info(f"Stopped feed: {name}")
            except Exception as e:
                self.logger.error(f"Error stopping feed {name}: {e}")
    
    def get_all_latest_prices(self) -> Dict[str, MarketData]:
        """Get latest prices from all feeds"""
        all_prices = {}
        for feed in self.feeds.values():
            all_prices.update(feed.get_latest_prices())
        return all_prices


# Convenience functions for easy integration
def create_simple_feed(symbols: List[str], data_service: DataService) -> LiveDataFeed:
    """Create a simple live data feed with default settings"""
    config = FeedConfig(
        symbols=symbols,
        update_interval_ms=1000,
        enable_websocket=True,
        enable_rest_fallback=True
    )
    return LiveDataFeed(config, data_service)


async def test_live_feed():
    """Test function for live data feed"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize data service
    data_service = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
    
    # Create feed
    symbols = ['BTC/USDT', 'ETH/USDT']
    feed = create_simple_feed(symbols, data_service)
    
    # Add callback to print prices
    def price_callback(data: MarketData):
        print(f"{data.symbol}: ${data.price:.2f} ({data.source})")
    
    feed.add_price_callback(price_callback)
    
    try:
        # Start feed
        await feed.start_feed()
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
    finally:
        await feed.stop_feed()


if __name__ == "__main__":
    asyncio.run(test_live_feed())
