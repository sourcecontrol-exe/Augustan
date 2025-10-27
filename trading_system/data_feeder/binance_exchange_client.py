"""
Binance Exchange Client - Unified implementation for spot and futures.

Handles both testnet and mainnet consistently using ccxt.
Uses dependency injection instead of accessing ConfigManager directly.
"""
import ccxt
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime

from .exchange_client import ExchangeClient, ExchangeConfig, ExchangeCredentials
from ..core.models import MarketData


class BinanceExchangeClient(ExchangeClient):
    """
    Unified Binance exchange client for spot and futures.
    
    Features:
    - Consistent API usage (always uses ccxt)
    - Handles testnet/mainnet differences internally
    - Dependency injection for credentials
    - Configuration-driven defaults
    - No hardcoded symbols
    
    Usage:
        credentials = ExchangeCredentials(
            api_key="...",
            secret="...",
            testnet=True
        )
        config = ExchangeConfig(
            credentials=credentials,
            default_symbols=["BTC/USDT", "ETH/USDT"]
        )
        client = BinanceExchangeClient(config, market_type='spot')
    """
    
    def __init__(
        self, 
        config: ExchangeConfig,
        market_type: str = 'spot',
        api_client: Optional[ccxt.Exchange] = None
    ):
        """
        Initialize Binance exchange client.
        
        Args:
            config: Exchange configuration with credentials and defaults
            market_type: 'spot' or 'futures'
            api_client: Optional ccxt exchange instance (for testing)
        """
        self.config = config
        self.market_type = market_type
        self.credentials = config.credentials
        
        # Initialize ccxt exchange
        if api_client is None:
            self.exchange = self._create_exchange()
        else:
            self.exchange = api_client
        
        logger.info(
            f"Binance {market_type} client initialized "
            f"(testnet={self.credentials.testnet})"
        )
    
    def _create_exchange(self) -> ccxt.Exchange:
        """Create and configure ccxt exchange instance."""
        exchange_options = {
            'apiKey': self.credentials.api_key,
            'secret': self.credentials.secret,
            'sandbox': self.credentials.testnet,
            'rateLimit': 1200,
            'enableRateLimit': True,
            'timeout': 30000,
        }
        
        # Set market type
        if self.market_type == 'futures':
            exchange_options['options'] = {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
            }
        else:
            exchange_options['options'] = {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        
        exchange = ccxt.binance(exchange_options)
        
        # Configure testnet URLs if needed
        if self.credentials.testnet:
            self._configure_testnet_urls(exchange)
        
        return exchange
    
    def _configure_testnet_urls(self, exchange: ccxt.Exchange):
        """Configure testnet API URLs."""
        if self.market_type == 'spot':
            exchange.urls['api'] = {
                'public': 'https://testnet.binance.vision/api/v3',
                'private': 'https://testnet.binance.vision/api/v3',
            }
        else:  # futures
            exchange.urls['api'] = {
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
            }
        
        # Disable SAPI endpoints for testnet
        if 'sapi' in exchange.urls['api']:
            del exchange.urls['api']['sapi']
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols."""
        try:
            # Always use ccxt for consistency
            markets = self.exchange.load_markets()
            
            # Filter by market type
            if self.market_type == 'futures':
                symbols = [
                    symbol for symbol in markets.keys() 
                    if ':USDT' in symbol and markets[symbol]['active']
                ]
            else:
                symbols = [
                    symbol for symbol in markets.keys()
                    if '/USDT' in symbol and markets[symbol]['active']
                ]
            
            if not symbols:
                logger.warning("No active symbols found, using defaults")
                return self.config.default_symbols
            
            return symbols[:50]  # Limit to top 50 for performance
            
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}, using defaults")
            return self.config.default_symbols
    
    def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = '1m', 
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch OHLCV data.
        
        Returns:
            List of dicts with market data
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            market_data = []
            for candle in ohlcv:
                market_data.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'symbol': symbol
                })
            
            logger.info(f"Fetched {len(market_data)} candles for {symbol}")
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols."""
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price:
                prices[symbol] = price
        return prices
    
    def fetch_multiple_symbols(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = '1m',
        limit: int = 100
    ) -> Dict[str, List[Dict]]:
        """Fetch OHLCV data for multiple symbols."""
        if symbols is None:
            symbols = self.config.default_symbols
        
        all_data = {}
        for symbol in symbols:
            data = self.fetch_ohlcv(symbol, timeframe, limit)
            if data:
                all_data[symbol] = data
        
        logger.info(f"Fetched data for {len(all_data)} symbols")
        return all_data
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information."""
        try:
            if not self.has_credentials():
                logger.warning("API credentials not configured")
                return None
            
            # Use ccxt for account info
            account_info = self.exchange.fetch_balance()
            return account_info
            
        except Exception as e:
            error_str = str(e).lower()
            if "sapi" in error_str or "not supported" in error_str:
                logger.warning(f"Account info not available in testnet: {e}")
                # Return mock data for testnet
                return self._get_mock_account_info()
            else:
                logger.error(f"Error fetching account info: {e}")
                return None
    
    def _get_mock_account_info(self) -> Dict:
        """Get mock account info for testnet."""
        return {
            'info': {
                'canTrade': True,
                'canWithdraw': False,
                'canDeposit': False,
            },
            'free': {
                'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0}
            },
            'used': {},
            'total': {
                'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0}
            },
            'USDT': {
                'free': 1000.0,
                'used': 0.0,
                'total': 1000.0
            }
        }
    
    def get_positions(self) -> List[Dict]:
        """Get current positions (futures only)."""
        if self.market_type != 'futures':
            logger.warning("get_positions() is only available for futures")
            return []
        
        try:
            positions = self.exchange.fetch_positions()
            return positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def is_testnet(self) -> bool:
        """Check if using testnet."""
        return self.credentials.testnet
    
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return (
            self.credentials.api_key is not None 
            and self.credentials.secret is not None
        )
    
    # Backward compatibility methods
    
    def fetch_ohlcv_for_market_data(
        self, symbol: str, timeframe: str = '1m', limit: int = 100
    ) -> List[MarketData]:
        """
        Fetch OHLCV data as MarketData objects.
        
        Backward compatibility method.
        """
        ohlcv_data = self.fetch_ohlcv(symbol, timeframe, limit)
        
        market_data = []
        for candle in ohlcv_data:
            market_data.append(MarketData(
                symbol=candle['symbol'],
                timestamp=candle['timestamp'],
                open=candle['open'],
                high=candle['high'],
                low=candle['low'],
                close=candle['close'],
                volume=candle['volume']
            ))
        
        return market_data

