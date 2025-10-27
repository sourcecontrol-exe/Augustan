"""
Exchange Client Interface - Abstraction layer for exchange operations.

Provides a consistent interface for different exchanges, handling
testnet/mainnet differences internally.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ExchangeCredentials:
    """Exchange API credentials."""
    api_key: Optional[str] = None
    secret: Optional[str] = None
    testnet: bool = True


@dataclass
class ExchangeConfig:
    """Configuration for exchange client."""
    credentials: ExchangeCredentials
    default_symbols: List[str]
    max_queue_size: int = 1000
    timeout: int = 30


class ExchangeClient(ABC):
    """
    Abstract base class for exchange clients.
    
    Provides a consistent interface for different exchanges while
    allowing implementations to handle exchange-specific details.
    """
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get available trading symbols."""
        pass
    
    @abstractmethod
    def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = '1m', 
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch OHLCV data.
        
        Returns:
            List of dicts with keys: timestamp, open, high, low, close, volume
        """
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Optional[Dict]:
        """Get account information."""
        pass
    
    @abstractmethod
    def is_testnet(self) -> bool:
        """Check if using testnet."""
        pass


class ExchangeClientBase(ExchangeClient):
    """
    Base implementation with common functionality.
    """
    
    def __init__(self, config: ExchangeConfig):
        """
        Initialize exchange client.
        
        Args:
            config: Exchange configuration
        """
        self.config = config
        self._credentials = config.credentials
        self._default_symbols = config.default_symbols
        
    def get_default_symbols(self) -> List[str]:
        """Get default trading symbols from configuration."""
        return self._default_symbols
    
    def set_default_symbols(self, symbols: List[str]):
        """Update default trading symbols."""
        self._default_symbols = symbols
    
    def is_testnet(self) -> bool:
        """Check if using testnet."""
        return self._credentials.testnet
    
    def has_credentials(self) -> bool:
        """Check if credentials are configured."""
        return self._credentials.api_key is not None and self._credentials.secret is not None

