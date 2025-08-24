"""
Base Adapter Interface

This module defines the standard interface that all exchange adapters must implement.
It acts as our "plug socket" for different exchange implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd

class BaseAdapter(ABC):
    """Abstract base class for all exchange adapters"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exchange = None
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the exchange"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the exchange"""
        pass
    
    @abstractmethod
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Get account balance for specified currency or all currencies"""
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker information for a symbol"""
        pass
    
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data for a symbol"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, 
                   amount: float, price: float = None) -> Dict[str, Any]:
        """Place an order on the exchange"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Get the status of an order"""
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        pass
    
    @abstractmethod
    def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def get_markets(self) -> List[str]:
        """Get list of available trading markets"""
        pass
    
    @abstractmethod
    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information and trading rules"""
        pass
    
    def is_healthy(self) -> bool:
        """Check if the exchange connection is healthy"""
        return self.is_connected and self.exchange is not None
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update the configuration"""
        self.config.update(new_config)
