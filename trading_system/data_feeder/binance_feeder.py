"""
Binance Data Feeder - Fetches market data from Binance API.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

from ..core.models import MarketData


class BinanceDataFeeder:
    """Fetches market data from Binance exchange."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Binance data feeder."""
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,  # Set to True for testnet
            'rateLimit': 1200,
            'enableRateLimit': True,
        })
        
        # Default symbols to trade
        self.default_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 
            'SOL/USDT', 'XRP/USDT', 'DOT/USDT', 'AVAX/USDT'
        ]
        
        logger.info("BinanceDataFeeder initialized")
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols."""
        try:
            markets = self.exchange.load_markets()
            return [symbol for symbol in markets.keys() if '/USDT' in symbol]
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return self.default_symbols
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[MarketData]:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of MarketData objects
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            market_data = []
            for candle in ohlcv:
                timestamp = datetime.fromtimestamp(candle[0] / 1000)
                data = MarketData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5])
                )
                market_data.append(data)
            
            logger.info(f"Fetched {len(market_data)} candles for {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    def fetch_multiple_symbols(self, symbols: Optional[List[str]] = None, 
                             timeframe: str = '1m', limit: int = 100) -> Dict[str, List[MarketData]]:
        """
        Fetch OHLCV data for multiple symbols.
        
        Args:
            symbols: List of symbols to fetch (uses default if None)
            timeframe: Timeframe ('1m', '5m', '1h', '1d')
            limit: Number of candles to fetch per symbol
            
        Returns:
            Dictionary mapping symbols to their market data
        """
        if symbols is None:
            symbols = self.default_symbols
        
        all_data = {}
        for symbol in symbols:
            data = self.fetch_ohlcv(symbol, timeframe, limit)
            if data:
                all_data[symbol] = data
        
        logger.info(f"Fetched data for {len(all_data)} symbols")
        return all_data
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def get_current_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """Get current prices for multiple symbols."""
        if symbols is None:
            symbols = self.default_symbols
        
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                prices[symbol] = price
        
        return prices
    
    def to_dataframe(self, market_data: List[MarketData]) -> pd.DataFrame:
        """Convert market data to pandas DataFrame."""
        data = []
        for md in market_data:
            data.append({
                'timestamp': md.timestamp,
                'open': md.open,
                'high': md.high,
                'low': md.low,
                'close': md.close,
                'volume': md.volume
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
        
        return df
