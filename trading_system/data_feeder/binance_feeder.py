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
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False, config_path: Optional[str] = None):
        """Initialize Binance data feeder."""
        # If no API key provided, try to get from config
        if api_key is None or api_secret is None:
            api_key, api_secret = self._get_spot_credentials(config_path)
        
        # Configure exchange for spot testnet
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': True,
                'test': True,
                'rateLimit': 1200,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,
                }
            })
            
            # Force testnet URLs - CCXT doesn't switch properly with API keys
            self.exchange.urls['api'] = {
                'public': 'https://testnet.binance.vision/api/v3',
                'private': 'https://testnet.binance.vision/api/v3',
            }
            
            # Disable SAPI endpoints for testnet
            if 'sapi' in self.exchange.urls['api']:
                del self.exchange.urls['api']['sapi']
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': False,
                'rateLimit': 1200,
                'enableRateLimit': True,
            })
        
        # Default symbols to trade
        self.default_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 
            'SOL/USDT', 'XRP/USDT', 'DOT/USDT', 'AVAX/USDT'
        ]
        
        logger.info("BinanceDataFeeder initialized")
    
    def _get_spot_credentials(self, config_path: Optional[str] = None) -> tuple[str, str]:
        """Get spot API credentials from configuration."""
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager(config_path)
            binance_config = config_manager.get_exchange_config('binance')
            
            # Check for new structure with spot/futures separation
            if 'spot' in binance_config:
                spot_config = binance_config['spot']
                return spot_config.get('api_key'), spot_config.get('secret')
            else:
                # Fallback to old structure
                return binance_config.get('api_key'), binance_config.get('secret')
        except Exception as e:
            logger.error(f"Failed to get spot credentials: {e}")
            return None, None
    
    def get_symbols(self) -> List[str]:
        """Get available trading symbols."""
        try:
            # Use direct API call instead of load_markets() to avoid SAPI endpoints
            if self.exchange.sandbox:
                # For testnet, use direct API call
                import requests
                response = requests.get('https://testnet.binance.vision/api/v3/exchangeInfo')
                data = response.json()
                symbols = [symbol['symbol'] for symbol in data['symbols'] if symbol['status'] == 'TRADING' and symbol['symbol'].endswith('USDT')]
                # Convert to CCXT format
                ccxt_symbols = [f"{symbol[:-4]}/{symbol[-4:]}" for symbol in symbols]
                return ccxt_symbols
            else:
                # For mainnet, use CCXT
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
            # Use direct API call instead of fetch_ticker() to avoid SAPI endpoints
            if self.exchange.sandbox:
                # For testnet, use direct API call
                import requests
                # Convert CCXT symbol format to Binance format
                binance_symbol = symbol.replace('/', '')
                response = requests.get(f'https://testnet.binance.vision/api/v3/ticker/price?symbol={binance_symbol}')
                data = response.json()
                return float(data['price'])
            else:
                # For mainnet, use CCXT
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
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information including balances."""
        try:
            if not self.exchange.apiKey or not self.exchange.secret:
                logger.warning("API credentials not configured for account info")
                return None
            
            # SAPI endpoints are not available in testnet
            if self.exchange.sandbox:
                logger.info("Using mock account service for testnet (SAPI endpoints not supported)")
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
                logger.error(f"Error fetching account info: {e}")
                return None
