# ==============================================================================
# File: adapters/pi42_public_adapter.py
# Description: Pi42 public API adapter for paper trading (no authentication required)
# ==============================================================================
import pandas as pd
import requests
import time
import logging
from typing import Dict, Any, List, Optional
from .base_adapter import BaseAdapter
from ...utils.exceptions import ExchangeAPIError, ExchangeConnectionError, DataFetchError

# Configure logging
logger = logging.getLogger(__name__)

class Pi42PublicAdapter(BaseAdapter):
    """
    Pi42 public API adapter for paper trading.
    Uses only public endpoints that don't require authentication.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Pi42 public adapter.
        
        Args:
            config: Configuration dictionary (no API keys needed for public endpoints)
        """
        super().__init__(config)
        
        # Pi42 public API base URL
        self.base_url = config.get('base_url', 'https://api.pi42.com')
        self.sandbox = config.get('testnet', False)
        
        # Use sandbox URL if testnet is enabled
        if self.sandbox:
            self.base_url = config.get('sandbox_url', 'https://sandbox-api.pi42.com')
        
        logger.info(f"Pi42PublicAdapter initialized with base URL: {self.base_url}")
        logger.info(f"Testnet mode: {self.sandbox}")

    def connect(self) -> bool:
        """
        Connect to Pi42 exchange using public endpoints.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test connection by fetching ticker data (public endpoint)
            # Pi42 might not have exchangeInfo endpoint, so we'll test with ticker
            response = requests.get(f"{self.base_url}/api/v1/ticker/24hr", timeout=10)
            response.raise_for_status()
            
            self.is_connected = True
            self.exchange = "Pi42"
            logger.info("Successfully connected to Pi42 exchange (public endpoints)")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Pi42: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Pi42: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from Pi42 exchange."""
        self.is_connected = False
        self.exchange = None
        logger.info("Disconnected from Pi42 exchange")
        return True

    def get_markets(self) -> List[str]:
        """
        Get list of available market symbols using public endpoint.
        
        Returns:
            List of market symbols
        """
        try:
            markets_data = self.fetch_markets()
            return list(markets_data.keys())
        except Exception as e:
            logger.error(f"Error getting markets: {e}")
            return []

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV data from Pi42 public endpoint.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/INR')
            timeframe: Time interval (e.g., '1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            # Convert symbol format (e.g., 'BTC/INR' -> 'BTCINR')
            formatted_symbol = symbol.replace('/', '')
            
            endpoint = "/api/v1/historical_klines"
            params = {
                'symbol': formatted_symbol, 
                'interval': timeframe, 
                'limit': limit
            }
            url = f"{self.base_url}{endpoint}"
            
            logger.debug(f"Fetching OHLCV for {symbol} with params: {params}")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"No OHLCV data received for {symbol}")
                return pd.DataFrame()

            # Format the data into standard DataFrame
            # Pi42 klines format: [timestamp, open, high, low, close, volume, ...]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Select and format required columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert columns to numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any rows with NaN values
            df = df.dropna()
            
            logger.debug(f"Successfully fetched OHLCV data for {symbol}: {df.shape}")
            return df
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch OHLCV data for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol, timeframe=timeframe)
        except Exception as e:
            error_msg = f"Unexpected error fetching OHLCV for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol, timeframe=timeframe)

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker information using public endpoint.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with ticker information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            # Convert symbol format
            formatted_symbol = symbol.replace('/', '')
            
            endpoint = "/api/v1/ticker/24hr"
            params = {'symbol': formatted_symbol}
            url = f"{self.base_url}{endpoint}"
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Format response to match standard structure
            ticker = {
                'symbol': symbol,
                'last': float(data.get('lastPrice', 0)),
                'bid': float(data.get('bidPrice', 0)),
                'ask': float(data.get('askPrice', 0)),
                'high': float(data.get('highPrice', 0)),
                'low': float(data.get('lowPrice', 0)),
                'volume': float(data.get('volume', 0)),
                'quoteVolume': float(data.get('quoteVolume', 0)),
                'change': float(data.get('priceChange', 0)),
                'percentage': float(data.get('priceChangePercent', 0)),
                'timestamp': int(time.time() * 1000)
            }
            
            return ticker
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch ticker for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol)
        except Exception as e:
            error_msg = f"Unexpected error fetching ticker for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol)

    def get_all_tickers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tickers using public endpoint.
        
        Returns:
            Dictionary with all ticker information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/ticker/24hr"
            url = f"{self.base_url}{endpoint}"
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            tickers = {}
            for ticker_data in data:
                # Convert symbol format back to standard (e.g., 'BTCINR' -> 'BTC/INR')
                raw_symbol = ticker_data.get('symbol', '')
                if raw_symbol:
                    # Try to parse the symbol - this is a simplified approach
                    # You might need to adjust based on Pi42's actual symbol format
                    if 'INR' in raw_symbol:
                        base = raw_symbol.replace('INR', '')
                        symbol = f"{base}/INR"
                    elif 'USDT' in raw_symbol:
                        base = raw_symbol.replace('USDT', '')
                        symbol = f"{base}/USDT"
                    else:
                        symbol = raw_symbol
                else:
                    continue
                
                ticker = {
                    'symbol': symbol,
                    'last': float(ticker_data.get('lastPrice', 0)),
                    'bid': float(ticker_data.get('bidPrice', 0)),
                    'ask': float(ticker_data.get('askPrice', 0)),
                    'high': float(ticker_data.get('highPrice', 0)),
                    'low': float(ticker_data.get('lowPrice', 0)),
                    'volume': float(ticker_data.get('volume', 0)),
                    'quoteVolume': float(ticker_data.get('quoteVolume', 0)),
                    'change': float(ticker_data.get('priceChange', 0)),
                    'percentage': float(ticker_data.get('priceChangePercent', 0)),
                    'timestamp': int(time.time() * 1000)
                }
                
                tickers[symbol] = ticker
            
            logger.debug(f"Successfully fetched {len(tickers)} tickers from Pi42")
            return tickers
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch all tickers: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error fetching all tickers: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg)

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information using public endpoint.
        
        Returns:
            Dictionary with exchange information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/exchangeInfo"
            url = f"{self.base_url}{endpoint}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'name': 'Pi42',
                'timezone': 'UTC',
                'rateLimits': data.get('rateLimits', []),
                'symbols': data.get('symbols', []),
                'exchangeFilters': data.get('exchangeFilters', []),
                'info': data
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch exchange info: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error fetching exchange info: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available markets from Pi42 public endpoint.
        
        Returns:
            Dictionary with market information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/exchangeInfo"
            url = f"{self.base_url}{endpoint}"
            
            logger.debug("Fetching markets from Pi42...")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Format response to match standard structure
            markets = {}
            for market in data.get('symbols', []):
                symbol = market.get('symbol')
                if symbol:
                    # Convert to standard format (e.g., 'BTCINR' -> 'BTC/INR')
                    base_asset = market.get('baseAsset', '')
                    quote_asset = market.get('quoteAsset', '')
                    standard_symbol = f"{base_asset}/{quote_asset}"
                    
                    markets[standard_symbol] = {
                        'id': symbol,
                        'symbol': standard_symbol,
                        'base': base_asset,
                        'quote': quote_asset,
                        'active': market.get('status') == 'TRADING',
                        'precision': {
                            'amount': market.get('baseAssetPrecision', 8),
                            'price': market.get('quotePrecision', 8)
                        },
                        'limits': {
                            'amount': {
                                'min': float(market.get('minQty', 0)),
                                'max': float(market.get('maxQty', float('inf')))
                            },
                            'price': {
                                'min': float(market.get('minPrice', 0)),
                                'max': float(market.get('maxPrice', float('inf')))
                            }
                        },
                        'info': market
                    }
            
            logger.debug(f"Successfully fetched {len(markets)} markets from Pi42")
            return markets
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch markets from Pi42: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error fetching markets from Pi42: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    # --- Placeholder methods for private endpoints (not used in paper trading) ---
    
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Balance information requires authenticated API access")

    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None) -> Dict[str, Any]:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Order placement requires authenticated API access")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Order cancellation requires authenticated API access")

    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Order status requires authenticated API access")

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Open orders require authenticated API access")

    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Not available in public API - placeholder for interface compliance"""
        raise NotImplementedError("Positions require authenticated API access")
