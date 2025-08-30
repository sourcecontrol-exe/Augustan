# ==============================================================================
# File: adapters/pi42_mock_adapter.py
# Description: Mock Pi42 adapter for paper trading demonstration
# ==============================================================================
import pandas as pd
import time
import logging
import random
from typing import Dict, Any, List, Optional
from .base_adapter import BaseAdapter
from ...utils.exceptions import ExchangeAPIError, ExchangeConnectionError, DataFetchError

# Configure logging
logger = logging.getLogger(__name__)

class Pi42MockAdapter(BaseAdapter):
    """
    Mock Pi42 adapter for paper trading demonstration.
    Simulates Pi42 market data without requiring actual API access.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Pi42 mock adapter.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # Mock configuration
        self.base_url = config.get('base_url', 'https://api.pi42.com')
        self.sandbox = config.get('testnet', False)
        
        # Mock market data
        self.mock_prices = {
            'BTC/INR': 2800000.0,  # ~$33,500 * 84 INR/USD
            'ETH/INR': 210000.0,   # ~$2,500 * 84 INR/USD
            'BTC/USDT': 33500.0,
            'ETH/USDT': 2500.0,
            'BNB/INR': 25000.0,
            'ADA/INR': 35.0,
            'DOT/INR': 420.0,
            'SOL/INR': 8400.0
        }
        
        # Price volatility simulation
        self.price_changes = {}
        for symbol in self.mock_prices:
            self.price_changes[symbol] = 0.0
        
        logger.info(f"Pi42MockAdapter initialized (simulation mode)")
        logger.info(f"Available symbols: {list(self.mock_prices.keys())}")

    def connect(self) -> bool:
        """
        Connect to Pi42 mock exchange.
        
        Returns:
            True (always successful for mock)
        """
        try:
            # Simulate connection delay
            time.sleep(0.1)
            
            self.is_connected = True
            self.exchange = "Pi42 (Mock)"
            logger.info("Successfully connected to Pi42 mock exchange")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error in mock connection: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from Pi42 mock exchange."""
        self.is_connected = False
        self.exchange = None
        logger.info("Disconnected from Pi42 mock exchange")
        return True

    def get_markets(self) -> List[str]:
        """
        Get list of available market symbols.
        
        Returns:
            List of mock market symbols
        """
        return list(self.mock_prices.keys())

    def _simulate_price_movement(self, symbol: str) -> float:
        """Simulate realistic price movement"""
        base_price = self.mock_prices[symbol]
        
        # Get current change or initialize
        current_change = self.price_changes.get(symbol, 0.0)
        
        # Random walk with mean reversion
        random_change = random.gauss(0, 0.001)  # 0.1% volatility
        mean_reversion = -current_change * 0.1  # Slight mean reversion
        
        new_change = current_change + random_change + mean_reversion
        
        # Limit extreme movements
        new_change = max(-0.05, min(0.05, new_change))  # ±5% max
        
        self.price_changes[symbol] = new_change
        return base_price * (1 + new_change)

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get mock ticker information.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with mock ticker data
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 mock adapter is not connected")
        
        if symbol not in self.mock_prices:
            raise DataFetchError(f"Symbol {symbol} not available in mock data", symbol=symbol)
        
        try:
            # Simulate current price with movement
            current_price = self._simulate_price_movement(symbol)
            
            # Generate realistic bid/ask spread
            spread_pct = random.uniform(0.001, 0.005)  # 0.1-0.5% spread
            spread = current_price * spread_pct
            
            bid = current_price - spread / 2
            ask = current_price + spread / 2
            
            # Generate 24h stats
            change_pct = random.gauss(0, 0.03)  # 3% daily volatility
            change = current_price * change_pct
            
            high_24h = current_price * (1 + abs(change_pct) + random.uniform(0, 0.02))
            low_24h = current_price * (1 - abs(change_pct) - random.uniform(0, 0.02))
            
            volume_24h = random.uniform(1000, 50000)
            
            ticker = {
                'symbol': symbol,
                'last': current_price,
                'bid': bid,
                'ask': ask,
                'high': high_24h,
                'low': low_24h,
                'volume': volume_24h,
                'quoteVolume': volume_24h * current_price,
                'change': change,
                'percentage': change_pct * 100,
                'timestamp': int(time.time() * 1000)
            }
            
            return ticker
            
        except Exception as e:
            error_msg = f"Error generating mock ticker for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol)

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Generate mock OHLCV data.
        
        Args:
            symbol: Trading symbol
            timeframe: Time interval
            limit: Number of candles
            
        Returns:
            DataFrame with mock OHLCV data
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 mock adapter is not connected")
        
        if symbol not in self.mock_prices:
            raise DataFetchError(f"Symbol {symbol} not available in mock data", symbol=symbol)
        
        try:
            # Generate timestamps
            now = pd.Timestamp.now()
            if timeframe == '1m':
                freq = '1min'
            elif timeframe == '5m':
                freq = '5min'
            elif timeframe == '1h':
                freq = '1h'
            elif timeframe == '1d':
                freq = '1d'
            else:
                freq = '1h'  # Default
            
            timestamps = pd.date_range(
                end=now, 
                periods=limit, 
                freq=freq
            )
            
            # Generate realistic OHLCV data
            base_price = self.mock_prices[symbol]
            data = []
            
            for i, ts in enumerate(timestamps):
                # Simulate price movement
                price = base_price * (1 + random.gauss(0, 0.02))  # 2% volatility
                
                # Generate OHLC around the price
                volatility = random.uniform(0.005, 0.02)  # 0.5-2% intrabar volatility
                high = price * (1 + volatility)
                low = price * (1 - volatility)
                open_price = price * (1 + random.gauss(0, 0.005))
                close_price = price * (1 + random.gauss(0, 0.005))
                
                # Ensure OHLC logic
                high = max(high, open_price, close_price)
                low = min(low, open_price, close_price)
                
                # Generate volume
                volume = random.uniform(10, 1000)
                
                data.append({
                    'timestamp': ts,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            logger.debug(f"Generated mock OHLCV data for {symbol}: {df.shape}")
            return df
            
        except Exception as e:
            error_msg = f"Error generating mock OHLCV for {symbol}: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg, symbol=symbol, timeframe=timeframe)

    def get_all_tickers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all mock tickers.
        
        Returns:
            Dictionary with all mock ticker information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 mock adapter is not connected")
        
        try:
            tickers = {}
            for symbol in self.mock_prices:
                tickers[symbol] = self.get_ticker(symbol)
            
            logger.debug(f"Generated {len(tickers)} mock tickers")
            return tickers
            
        except Exception as e:
            error_msg = f"Error generating mock tickers: {e}"
            logger.error(error_msg)
            raise DataFetchError(error_msg)

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get mock exchange information.
        
        Returns:
            Dictionary with mock exchange information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 mock adapter is not connected")
        
        return {
            'name': 'Pi42 (Mock)',
            'timezone': 'UTC',
            'rateLimits': [
                {'rateLimitType': 'REQUEST_WEIGHT', 'interval': 'MINUTE', 'intervalNum': 1, 'limit': 1200},
                {'rateLimitType': 'ORDERS', 'interval': 'SECOND', 'intervalNum': 10, 'limit': 50}
            ],
            'symbols': [
                {
                    'symbol': symbol.replace('/', ''),
                    'baseAsset': symbol.split('/')[0],
                    'quoteAsset': symbol.split('/')[1],
                    'status': 'TRADING'
                }
                for symbol in self.mock_prices
            ],
            'exchangeFilters': [],
            'info': {'mock': True, 'description': 'Mock Pi42 adapter for demonstration'}
        }

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch mock market information.
        
        Returns:
            Dictionary with mock market information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 mock adapter is not connected")
        
        try:
            markets = {}
            for symbol in self.mock_prices:
                base_asset = symbol.split('/')[0]
                quote_asset = symbol.split('/')[1]
                
                markets[symbol] = {
                    'id': symbol.replace('/', ''),
                    'symbol': symbol,
                    'base': base_asset,
                    'quote': quote_asset,
                    'active': True,
                    'precision': {
                        'amount': 8,
                        'price': 2 if quote_asset == 'INR' else 8
                    },
                    'limits': {
                        'amount': {
                            'min': 0.001 if base_asset == 'BTC' else 0.01,
                            'max': 1000000
                        },
                        'price': {
                            'min': 0.01 if quote_asset == 'INR' else 0.0001,
                            'max': 10000000
                        }
                    },
                    'info': {'mock': True}
                }
            
            logger.debug(f"Generated {len(markets)} mock markets")
            return markets
            
        except Exception as e:
            error_msg = f"Error generating mock markets: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42Mock")

    # --- Placeholder methods for private endpoints (not used in paper trading) ---
    
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Balance information not available in mock adapter")

    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None) -> Dict[str, Any]:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Order placement not available in mock adapter")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Order cancellation not available in mock adapter")

    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Order status not available in mock adapter")

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Open orders not available in mock adapter")

    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Not available in mock adapter - placeholder for interface compliance"""
        raise NotImplementedError("Positions not available in mock adapter")
