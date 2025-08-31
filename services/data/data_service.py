"""
Data Service

This module provides a unified interface for fetching market data from any exchange adapter.
It acts as a data layer abstraction over the adapter system.
"""

from ..adapters.base_adapter import BaseAdapter
from ..adapters.ccxt_adapter import CCXTAdapter
from ..adapters.pi42_adapter import Pi42Adapter
from ...core.exceptions import DataFetchError
from ..adapters import get_adapter, list_adapters

class DataService:
    """
    Data service that provides unified access to market data from any exchange adapter.
    """
    
    def __init__(self, exchange_name: str = 'ccxt', config: Dict[str, Any] = None):
        """
        Initialize the data service with a specific exchange adapter.
        
        Args:
            exchange_name: Name of the exchange adapter to use ('ccxt', 'pi42', etc.)
            config: Configuration dictionary for the exchange
        """
        self.exchange_name = exchange_name
        self.config = config or {}
        self.adapter = None
        self._initialize_adapter()
    
    def _initialize_adapter(self):
        """Initialize the exchange adapter"""
        try:
            self.adapter = get_adapter(self.exchange_name, self.config)
            
            # Connect to the exchange
            if not self.adapter.connect():
                raise ConnectionError(f"Failed to connect to {self.exchange_name}")
                
            print(f"DataService initialized with {self.exchange_name} adapter")
            
        except Exception as e:
            print(f"Error initializing {self.exchange_name} adapter: {e}")
            raise
    
    def get_markets(self) -> List[str]:
        """Get list of available trading markets"""
        try:
            return self.adapter.get_markets()
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Time interval (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            return self.adapter.get_ohlcv(symbol, timeframe, limit)
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker information for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary with ticker data (price, volume, etc.)
        """
        try:
            return self.adapter.get_ticker(symbol)
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            return {}
    
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """
        Get account balance
        
        Args:
            currency: Specific currency to get balance for (None for all)
            
        Returns:
            Dictionary with currency balances
        """
        try:
            return self.adapter.get_balance(currency)
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {}
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and capabilities"""
        try:
            return self.adapter.get_exchange_info()
        except Exception as e:
            print(f"Error fetching exchange info: {e}")
            return {}
    
    def is_healthy(self) -> bool:
        """Check if the data service is healthy and connected"""
        return self.adapter and self.adapter.is_healthy()
    
    def disconnect(self):
        """Disconnect from the exchange"""
        if self.adapter:
            self.adapter.disconnect()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of available exchange adapters"""
        return list_adapters()
    
    def switch_exchange(self, exchange_name: str, config: Dict[str, Any] = None):
        """
        Switch to a different exchange adapter
        
        Args:
            exchange_name: Name of the new exchange adapter
            config: Configuration for the new exchange
        """
        if self.adapter:
            self.adapter.disconnect()
        
        self.exchange_name = exchange_name
        self.config = config or {}
        self._initialize_adapter()
