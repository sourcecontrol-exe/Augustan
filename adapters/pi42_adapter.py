# ==============================================================================
# File: adapters/pi42_adapter.py
# Description: A custom adapter for the Pi42 exchange, aligned with the
#              standard BaseAdapter interface.
# ==============================================================================
import pandas as pd
import requests
import time
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional
from .base_adapter import BaseAdapter
from exceptions import ExchangeAPIError, ExchangeConnectionError, DataFetchError

# Configure logging
logger = logging.getLogger(__name__)

class Pi42Adapter(BaseAdapter):
    """
    Pi42-specific adapter for cryptocurrency trading.
    This class translates the standard bot commands into API calls for Pi42.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Pi42 adapter with configuration.
        
        Args:
            config: Configuration dictionary containing API credentials and settings
        """
        super().__init__(config)
        
        # Extract configuration
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.base_url = config.get('base_url', 'https://api.pi42.com')
        self.sandbox = config.get('testnet', False)
        
        # Use sandbox URL if testnet is enabled
        if self.sandbox:
            self.base_url = config.get('sandbox_url', 'https://sandbox-api.pi42.com')
        
        # Validate required credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("Pi42 API key and secret are required")
        
        logger.info(f"Pi42Adapter initialized with base URL: {self.base_url}")
        logger.info(f"Testnet mode: {self.sandbox}")

    def connect(self) -> bool:
        """
        Connect to Pi42 exchange and verify connectivity.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test connection by fetching exchange info
            response = requests.get(f"{self.base_url}/api/v1/exchangeInfo", timeout=10)
            response.raise_for_status()
            
            self.is_connected = True
            self.exchange = "Pi42"
            logger.info("Successfully connected to Pi42 exchange")
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
        Get list of available market symbols.
        
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
        Fetch OHLCV data from Pi42.
        
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
            # Convert symbol format if needed (e.g., 'BTC/INR' -> 'BTCINR')
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
        Get current ticker information for a symbol.
        
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
                'change': float(data.get('priceChange', 0)),
                'change_percent': float(data.get('priceChangePercent', 0)),
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

    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """
        Get account balance information.
        
        Args:
            currency: Specific currency to fetch (optional)
            
        Returns:
            Dictionary with balance information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/account"
            path = "/api/v1/account"
            url = f"{self.base_url}{endpoint}"
            
            headers = self._get_headers('GET', path)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            balances = {}
            for balance in data.get('balances', []):
                asset = balance.get('asset')
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked
                
                if total > 0:  # Only include non-zero balances
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            if currency:
                return balances.get(currency, {'free': 0, 'locked': 0, 'total': 0})
            
            return balances
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch balance: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error fetching balance: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def place_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None) -> Dict[str, Any]:
        """
        Place an order on Pi42.
        
        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            order_type: 'MARKET' or 'LIMIT'
            amount: Order quantity
            price: Order price (required for LIMIT orders)
            
        Returns:
            Dictionary with order information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            # Convert symbol format
            formatted_symbol = symbol.replace('/', '')
            
            endpoint = "/api/v1/order"
            path = "/api/v1/order"
            url = f"{self.base_url}{endpoint}"

            # Prepare order payload
            order_data = {
                "symbol": formatted_symbol,
                "side": side.upper(),
                "type": order_type.upper(),
                "quantity": str(amount),
            }
            
            # Add price for limit orders
            if order_type.upper() == 'LIMIT':
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                order_data['price'] = str(price)

            body = json.dumps(order_data)
            headers = self._get_headers('POST', path, body)

            logger.info(f"Placing {side} {order_type} order for {amount} {symbol}")
            
            response = requests.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
            order_response = response.json()
            
            # Format response to match standard structure
            order = {
                'id': order_response.get('orderId'),
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'amount': amount,
                'price': price,
                'status': order_response.get('status', 'PENDING'),
                'timestamp': int(time.time() * 1000),
                'info': order_response
            }
            
            logger.info(f"Order placed successfully: {order['id']}")
            return order
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to place order for {symbol}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error placing order for {symbol}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Get the status of an order.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol
            
        Returns:
            Dictionary with order status information
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = f"/api/v1/order"
            path = f"/api/v1/order"
            url = f"{self.base_url}{endpoint}"
            
            params = {
                'orderId': order_id,
                'symbol': symbol.replace('/', '')
            }
            
            headers = self._get_headers('GET', path)
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'id': data.get('orderId'),
                'symbol': symbol,
                'side': data.get('side'),
                'type': data.get('type'),
                'amount': float(data.get('origQty', 0)),
                'filled': float(data.get('executedQty', 0)),
                'price': float(data.get('price', 0)),
                'status': data.get('status'),
                'timestamp': int(time.time() * 1000),
                'info': data
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get order status for {order_id}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error getting order status for {order_id}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            
        Returns:
            Dictionary with cancellation result
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/order"
            path = "/api/v1/order"
            url = f"{self.base_url}{endpoint}"
            
            # Convert symbol format
            formatted_symbol = symbol.replace('/', '')
            
            params = {
                'orderId': order_id,
                'symbol': formatted_symbol
            }
            
            headers = self._get_headers('DELETE', path)
            
            logger.info(f"Cancelling order {order_id} for {symbol}")
            
            response = requests.delete(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'id': order_id,
                'symbol': symbol,
                'status': 'CANCELLED',
                'timestamp': int(time.time() * 1000),
                'info': data
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to cancel order {order_id}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error cancelling order {order_id}: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information and trading rules.
        
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

    # --- Private Helper Methods for Authentication ---

    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Create authentication headers for private endpoints.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API endpoint path
            body: Request body for POST requests
            
        Returns:
            Dictionary with authentication headers
        """
        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path + body
        
        signature = hmac.new(
            bytes(self.api_secret, 'latin-1'),
            msg=bytes(message, 'latin-1'),
            digestmod=hashlib.sha256
        ).hexdigest()

        return {
            'X-Api-Key': self.api_key,
            'X-Timestamp': timestamp,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }

    def fetch_markets(self) -> Dict[str, Any]:
        """
        Fetch all available markets from Pi42.
        
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
                    # Convert back to standard format (e.g., 'BTCINR' -> 'BTC/INR')
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

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get open orders for a specific symbol or all symbols.
        
        Args:
            symbol: Trading symbol (optional, if None returns all open orders)
            
        Returns:
            List of open orders
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            endpoint = "/api/v1/openOrders"
            path = "/api/v1/openOrders"
            url = f"{self.base_url}{endpoint}"
            
            params = {}
            if symbol:
                params['symbol'] = symbol.replace('/', '')
            
            headers = self._get_headers('GET', path)
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            orders = []
            for order in data:
                # Convert symbol format back to standard
                order_symbol = order.get('symbol', '')
                if order_symbol:
                    # Try to convert back to standard format (e.g., 'BTCINR' -> 'BTC/INR')
                    # This is a simplified conversion - you might need to adjust based on Pi42's format
                    if len(order_symbol) >= 6:  # Minimum length for base/quote
                        base = order_symbol[:3]  # Assume first 3 chars are base
                        quote = order_symbol[3:]  # Rest are quote
                        standard_symbol = f"{base}/{quote}"
                    else:
                        standard_symbol = order_symbol
                else:
                    standard_symbol = symbol or 'UNKNOWN'
                
                orders.append({
                    'id': order.get('orderId'),
                    'symbol': standard_symbol,
                    'side': order.get('side'),
                    'type': order.get('type'),
                    'amount': float(order.get('origQty', 0)),
                    'filled': float(order.get('executedQty', 0)),
                    'price': float(order.get('price', 0)),
                    'status': order.get('status'),
                    'timestamp': int(time.time() * 1000),
                    'info': order
                })
            
            return orders
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch open orders: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error fetching open orders: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current trading positions.
        
        Returns:
            List of current positions
        """
        if not self.is_healthy():
            raise ExchangeConnectionError("Pi42 adapter is not connected")
        
        try:
            # Pi42 might not have a direct positions endpoint
            # We'll try to get account information and derive positions
            endpoint = "/api/v1/account"
            path = "/api/v1/account"
            url = f"{self.base_url}{endpoint}"
            
            headers = self._get_headers('GET', path)
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            positions = []
            for balance in data.get('balances', []):
                asset = balance.get('asset')
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked
                
                # Only include positions with non-zero balances
                if total > 0:
                    positions.append({
                        'symbol': asset,
                        'size': total,
                        'free': free,
                        'locked': locked,
                        'timestamp': int(time.time() * 1000),
                        'info': balance
                    })
            
            return positions
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch positions: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")
        except Exception as e:
            error_msg = f"Unexpected error fetching positions: {e}"
            logger.error(error_msg)
            raise ExchangeAPIError(error_msg, exchange="Pi42")