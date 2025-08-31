"""
CCXT Adapter

This adapter implements the BaseAdapter interface for all CCXT-supported exchanges.
It provides a unified interface to interact with various cryptocurrency exchanges.
"""

import ccxt
import pandas as pd
from typing import Dict, List, Any
from .base_adapter import BaseAdapter

class CCXTAdapter(BaseAdapter):
    """CCXT-based adapter for cryptocurrency exchanges"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.exchange_name = config.get('exchange', 'binance')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.sandbox = config.get('testnet', False)
        self.exchange_type = config.get('default_type', 'spot')
        
    def connect(self) -> bool:
        """Establish connection to the exchange"""
        try:
            # Dynamically create exchange instance
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': self.sandbox,
                'options': {
                    'defaultType': self.exchange_type
                }
            })
            
            # Test connection
            self.exchange.load_markets()
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to {self.exchange_name}: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from the exchange"""
        try:
            if self.exchange:
                self.exchange.close()
            self.exchange = None
            self.is_connected = False
            return True
        except Exception as e:
            print(f"Error disconnecting: {e}")
            return False
    
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Get account balance"""
        if not self.is_healthy():
            return {}
        
        try:
            balance = self.exchange.fetch_balance()
            if currency:
                return {currency: balance.get(currency, {}).get('free', 0.0)}
            else:
                return {curr: bal.get('free', 0.0) for curr, bal in balance.items() if bal.get('free', 0.0) > 0}
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {}
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information"""
        if not self.is_healthy():
            return {}
        
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            return {}
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data"""
        if not self.is_healthy():
            return pd.DataFrame()
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   amount: float, price: float = None) -> Dict[str, Any]:
        """Place an order"""
        if not self.is_healthy():
            return {}
        
        try:
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount
            }
            
            if price and order_type != 'market':
                order_params['price'] = price
                
            return self.exchange.create_order(**order_params)
        except Exception as e:
            print(f"Error placing order: {e}")
            return {}
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        if not self.is_healthy():
            return False
        
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            return result.get('status') == 'canceled'
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get order status"""
        if not self.is_healthy():
            return {}
        
        try:
            return self.exchange.fetch_order(order_id, symbol)
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return {}
    
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get open orders"""
        if not self.is_healthy():
            return []
        
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []
    
    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get current positions"""
        if not self.is_healthy():
            return []
        
        try:
            if hasattr(self.exchange, 'fetch_positions'):
                positions = self.exchange.fetch_positions(symbol)
                return [pos for pos in positions if pos.get('size', 0) != 0]
            else:
                return []
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def get_markets(self) -> List[str]:
        """Get available markets"""
        if not self.is_healthy():
            return []
        
        try:
            markets = self.exchange.load_markets()
            return list(markets.keys())
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information"""
        if not self.is_healthy():
            return {}
        
        try:
            return {
                'name': self.exchange_name,
                'sandbox': self.sandbox,
                'exchange_type': self.exchange_type,
                'markets_count': len(self.exchange.markets),
                'timeframes': self.exchange.timeframes
            }
        except Exception as e:
            print(f"Error fetching exchange info: {e}")
            return {}
