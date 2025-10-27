"""
Binance Futures Data Feeder - Fetches futures market data from Binance API.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

from ..core.models import MarketData


class BinanceFuturesFeeder:
    """Fetches futures market data from Binance exchange."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False, config_path: Optional[str] = None):
        """Initialize Binance futures data feeder."""
        # If no API key provided, try to get from config
        if api_key is None or api_secret is None:
            api_key, api_secret = self._get_futures_credentials(config_path)
        
        # Configure exchange for futures testnet
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': True,
                'test': True,
                'options': {
                    'defaultType': 'future',  # Use futures API
                    'adjustForTimeDifference': True,
                },
                'rateLimit': 1200,
                'enableRateLimit': True,
            })
            
            # Force testnet URLs - CCXT doesn't switch properly with API keys
            self.exchange.urls['api'] = {
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
            }
            
            # Disable SAPI endpoints for testnet
            if 'sapi' in self.exchange.urls['api']:
                del self.exchange.urls['api']['sapi']
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': False,
                'options': {
                    'defaultType': 'future',  # Use futures API
                },
                'rateLimit': 1200,
                'enableRateLimit': True,
            })
        
        # Default futures symbols to trade
        self.default_symbols = [
            'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'ADA/USDT:USDT', 
            'SOL/USDT:USDT', 'XRP/USDT:USDT', 'DOT/USDT:USDT', 'AVAX/USDT:USDT'
        ]
        
        logger.info("BinanceFuturesFeeder initialized")
    
    def _get_futures_credentials(self, config_path: Optional[str] = None) -> tuple[str, str]:
        """Get futures API credentials from configuration."""
        try:
            from ..core.config_manager_refactored import ConfigManager
            
            # Create config manager
            if config_path:
                config_manager = ConfigManager.create(config_path)
            else:
                config_manager = ConfigManager.create_for_testing()
            
            # Get credentials from refactored config
            # Note: The refactored config doesn't expose exchange configs the same way
            # This will return None, None for now since credentials should come from environment variables
            logger.info("Credentials should be provided via environment variables or constructor parameters")
            return None, None
        except Exception as e:
            logger.error(f"Failed to get futures credentials: {e}")
            return None, None
    
    def get_symbols(self) -> List[str]:
        """Get available futures trading symbols."""
        try:
            # Use direct API call instead of load_markets() to avoid SAPI endpoints
            if self.exchange.sandbox:
                # For testnet, use direct API call
                import requests
                response = requests.get('https://testnet.binancefuture.com/fapi/v1/exchangeInfo')
                data = response.json()
                symbols = [symbol['symbol'] for symbol in data['symbols'] if symbol['status'] == 'TRADING' and symbol['symbol'].endswith('USDT')]
                # Convert to CCXT format
                ccxt_symbols = [f"{symbol}:USDT" for symbol in symbols]
                return ccxt_symbols
            else:
                # For mainnet, use CCXT
                markets = self.exchange.load_markets()
                return [symbol for symbol in markets.keys() if ':USDT' in symbol]
        except Exception as e:
            logger.error(f"Error fetching futures symbols: {e}")
            return self.default_symbols
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[MarketData]:
        """
        Fetch OHLCV data for a futures symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            timeframe: Timeframe ('1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of MarketData objects
        """
        try:
            # For testnet, use direct API calls to avoid SAPI endpoint issues
            if self.exchange.sandbox:
                import requests
                
                # Convert symbol format (BTC/USDT:USDT -> BTCUSDT, BTCUSDT:USDT -> BTCUSDT)
                clean_symbol = symbol.replace('/', '').replace(':USDT', '')
                if not clean_symbol.endswith('USDT'):
                    clean_symbol += 'USDT'
                
                # Map timeframe
                interval_map = {
                    '1m': '1m', '5m': '5m', '15m': '15m',
                    '1h': '1h', '4h': '4h', '1d': '1d'
                }
                interval = interval_map.get(timeframe, '1m')
                
                # Make direct API call
                url = f"https://testnet.binancefuture.com/fapi/v1/klines"
                params = {
                    'symbol': clean_symbol,
                    'interval': interval,
                    'limit': limit
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                ohlcv_data = response.json()
                
                market_data = []
                for candle in ohlcv_data:
                    timestamp = datetime.fromtimestamp(int(candle[0]) / 1000)
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
                
                logger.info(f"Fetched {len(market_data)} futures candles for {symbol} via direct API")
                return market_data
            else:
                # For mainnet, use CCXT
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
                
                logger.info(f"Fetched {len(market_data)} futures candles for {symbol}")
                return market_data
            
        except Exception as e:
            logger.error(f"Error fetching futures OHLCV for {symbol}: {e}")
            return []
    
    def fetch_multiple_symbols(self, symbols: Optional[List[str]] = None, 
                             timeframe: str = '1m', limit: int = 100) -> Dict[str, List[MarketData]]:
        """
        Fetch OHLCV data for multiple futures symbols.
        
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
        
        logger.info(f"Fetched futures data for {len(all_data)} symbols")
        return all_data
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a futures symbol."""
        try:
            # Use direct API call instead of fetch_ticker() to avoid SAPI endpoints
            if self.exchange.sandbox:
                # For testnet, use direct API call
                import requests
                # Convert CCXT symbol format to Binance format
                binance_symbol = symbol.replace('/', '').replace(':USDT', '')
                response = requests.get(f'https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol={binance_symbol}')
                data = response.json()
                if 'price' in data:
                    return float(data['price'])
                else:
                    # Try alternative endpoint
                    response = requests.get(f'https://testnet.binancefuture.com/fapi/v1/ticker/24hr?symbol={binance_symbol}')
                    data = response.json()
                    return float(data['lastPrice'])
            else:
                # For mainnet, use CCXT
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching current futures price for {symbol}: {e}")
            return None
    
    def get_current_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """Get current prices for multiple futures symbols."""
        if symbols is None:
            symbols = self.default_symbols
        
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                prices[symbol] = price
        
        return prices
    
    def get_account_info(self) -> Optional[Dict]:
        """Get futures account information including balances."""
        try:
            if not self.exchange.apiKey or not self.exchange.secret:
                logger.warning("API credentials not configured for futures account info")
                return None
            
            # Futures testnet has limited SAPI support
            if self.exchange.sandbox:
                logger.info("Using mock account service for futures testnet")
                from .mock_account_service import get_mock_account_service
                mock_service = get_mock_account_service(balance=1000.0)
                return mock_service.get_balance()
            
            account_info = self.exchange.fetch_balance()
            return account_info
        except Exception as e:
            if "sapi" in str(e).lower():
                logger.error("SAPI endpoints not available in testnet. Using mock data.")
                from .mock_account_service import get_mock_account_service
                mock_service = get_mock_account_service(balance=1000.0)
                return mock_service.get_balance()
            else:
                logger.error(f"Error fetching futures account info: {e}")
                return None
    
    def get_positions(self) -> List[Dict]:
        """Get current futures positions."""
        try:
            positions = self.exchange.fetch_positions()
            return positions
        except Exception as e:
            logger.error(f"Error fetching futures positions: {e}")
            return []
    
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
