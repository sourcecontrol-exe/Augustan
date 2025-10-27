"""
Service Interfaces - Explicit contracts for all live trading services.

Defines ABCs (Abstract Base Classes) for all services to enforce contracts
and facilitate mocking in tests.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime


class IMarketDataStreamer(ABC):
    """Interface for market data streaming service."""
    
    @abstractmethod
    def start(self):
        """Start streaming market data."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop streaming market data."""
        pass
    
    @abstractmethod
    def add_data_callback(self, callback: Callable):
        """Add callback for market data events."""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if streamer is running."""
        pass


class ISignalGeneratorService(ABC):
    """Interface for signal generation service."""
    
    @abstractmethod
    def add_signal_callback(self, callback: Callable):
        """Add callback for signals."""
        pass
    
    @abstractmethod
    def set_cooldown(self, minutes: int):
        """Set signal cooldown period."""
        pass
    
    @abstractmethod
    async def process_market_data(self, symbol: str, candle_data, current_price: float):
        """Process market data and generate signals."""
        pass


class ITradeExecutionService(ABC):
    """Interface for trade execution service."""
    
    @abstractmethod
    def add_execution_callback(self, callback: Callable):
        """Add callback for trade execution events."""
        pass
    
    @abstractmethod
    async def execute_trade(self, risk_result) -> bool:
        """Execute a trade with retry logic."""
        pass


class IMonitoringService(ABC):
    """Interface for monitoring service."""
    
    @abstractmethod
    def start(self):
        """Start monitoring."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop monitoring."""
        pass
    
    @abstractmethod
    def add_alert_callback(self, callback: Callable):
        """Add callback for alerts."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get current portfolio metrics."""
        pass


class IRealtimeFeeder(ABC):
    """Interface for realtime data feeder."""
    
    @abstractmethod
    def start(self):
        """Start the data feed."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop the data feed."""
        pass
    
    @abstractmethod
    def add_event_callback(self, callback: Callable):
        """Add callback for data events."""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        pass

