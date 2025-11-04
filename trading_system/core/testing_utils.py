"""
Testing utilities for the trading system.

Provides:
- Mock factories
- Test data generators
- Assertion helpers
- Performance testing utilities
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import pandas as pd

from .models import MarketData, TradingSignal, StrategyType, SignalType
from .config_manager import ConfigManager


class MockMarketDataFactory:
    """Factory for creating mock market data."""
    
    @staticmethod
    def create_candle(
        symbol: str = "BTC/USDT",
        open_price: float = 50000.0,
        close_price: float = 50100.0,
        high: Optional[float] = None,
        low: Optional[float] = None,
        volume: float = 100.0,
        timestamp: Optional[datetime] = None
    ) -> MarketData:
        """Create a single candle."""
        timestamp = timestamp or datetime.now()
        high = high or max(open_price, close_price)
        low = low or min(open_price, close_price)
        
        return MarketData(
            symbol=symbol,
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=volume
        )
    
    @staticmethod
    def create_candles(
        symbol: str = "BTC/USDT",
        count: int = 100,
        start_price: float = 50000.0,
        price_change: float = 100.0
    ) -> List[MarketData]:
        """Create multiple candles."""
        candles = []
        timestamp = datetime.now()
        
        for i in range(count):
            open_price = start_price + (i * price_change)
            close_price = open_price + price_change
            
            candle = MockMarketDataFactory.create_candle(
                symbol=symbol,
                open_price=open_price,
                close_price=close_price,
                timestamp=timestamp - timedelta(minutes=count-i)
            )
            candles.append(candle)
        
        return candles
    
    @staticmethod
    def create_signal(
        symbol: str = "BTC/USDT",
        signal_type: SignalType = SignalType.BUY,
        price: float = 50000.0,
        confidence: float = 0.8,
        strategy: StrategyType = StrategyType.RSI
    ) -> TradingSignal:
        """Create a mock signal."""
        return TradingSignal(
            symbol=symbol,
            strategy=strategy,
            signal_type=signal_type,
            confidence=confidence,
            price=price,
            timestamp=datetime.now()
        )


class MockConfigFactory:
    """Factory for creating mock configurations."""
    
    @staticmethod
    def create_test_config(overrides: Optional[Dict[str, Any]] = None) -> ConfigManager:
        """Create a test configuration."""
        config_dict = {
            'risk_management': {
                'default_budget': 1000.0,
                'max_risk_per_trade': 0.01,
                'max_positions': 1,
            },
            'data_fetching': {
                'max_retries': 1,
                'timeout_seconds': 5,
            },
            'trading_mode': 'paper',
            'signal_generation': {
                'min_signal_strength': 0.7,
            }
        }
        
        if overrides:
            def deep_merge(base, override):
                for key, value in override.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        base[key] = deep_merge(base[key], value)
                    else:
                        base[key] = value
                return base
            config_dict = deep_merge(config_dict, overrides)
        
        from .config_manager import ConfigManager
        from .config_loader import ConfigLoader
        
        # Create a minimal config
        class TestConfig:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        return ConfigManager.create_for_testing(overrides)


class MockExchangeFactory:
    """Factory for creating mock exchanges."""
    
    @staticmethod
    def create_mock_ccxt():
        """Create a mock ccxt exchange."""
        exchange = MagicMock()
        
        # Mock fetch_ohlcv
        async def mock_ohlcv(symbol, timeframe='1m', limit=100):
            return [[
                int(datetime.now().timestamp() * 1000),  # timestamp
                50000.0,  # open
                50100.0,  # high
                49900.0,  # low
                50050.0,  # close
                100.0     # volume
            ]] * limit
        
        exchange.fetch_ohlcv = AsyncMock(side_effect=mock_ohlcv)
        
        # Mock fetch_ticker
        async def mock_ticker(symbol):
            return {
                'last': 50000.0,
                'bid': 49999.0,
                'ask': 50001.0,
                'volume': 1000.0
            }
        
        exchange.fetch_ticker = AsyncMock(side_effect=mock_ticker)
        
        # Mock fetch_balance
        async def mock_balance():
            return {
                'USDT': {'free': 1000.0, 'used': 0.0, 'total': 1000.0}
            }
        
        exchange.fetch_balance = AsyncMock(side_effect=mock_balance)
        
        return exchange


class MockEventBusFactory:
    """Factory for creating mock event buses."""
    
    @staticmethod
    def create() -> Mock:
        """Create a mock event bus."""
        bus = Mock()
        bus.subscribe = Mock()
        bus.unsubscribe = Mock()
        bus.emit = AsyncMock()
        bus.start = AsyncMock()
        bus.stop = AsyncMock()
        bus.is_running = Mock(return_value=True)
        return bus


class AssertionHelpers:
    """Helper methods for test assertions."""
    
    @staticmethod
    def assert_signal_valid(signal: TradingSignal):
        """Assert that a signal is valid."""
        assert signal is not None, "Signal should not be None"
        assert signal.confidence > 0, "Signal confidence should be positive"
        assert signal.confidence <= 1, "Signal confidence should be <= 1"
        assert signal.price > 0, "Signal price should be positive"
        assert signal.symbol, "Signal should have a symbol"
    
    @staticmethod
    def assert_market_data_valid(data: MarketData):
        """Assert that market data is valid."""
        assert data is not None, "Market data should not be None"
        assert data.high >= data.low, "High should be >= low"
        assert data.close >= data.low and data.close <= data.high, "Close should be within high/low range"
        assert data.volume >= 0, "Volume should be non-negative"
        assert data.symbol, "Market data should have a symbol"
    
    @staticmethod
    def assert_duration_reasonable(actual_ms: float, max_ms: float):
        """Assert that execution duration is reasonable."""
        assert actual_ms < max_ms, f"Duration {actual_ms}ms exceeds max {max_ms}ms"


class PerformanceTestHelpers:
    """Helpers for performance testing."""
    
    @staticmethod
    async def measure_performance(func, *args, **kwargs) -> float:
        """Measure function execution time in ms."""
        import time
        start = time.time()
        result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return duration
    
    @staticmethod
    def create_large_dataset(count: int) -> List[MarketData]:
        """Create a large dataset for performance testing."""
        return MockMarketDataFactory.create_candles(
            symbol="BTC/USDT",
            count=count,
            start_price=50000.0
        )


# Convenience fixtures for pytest
class PytestFixtures:
    """Pytest fixtures for common test components."""
    
    @staticmethod
    def mock_config_manager():
        """Fixture for mock config manager."""
        return MockConfigFactory.create_test_config()
    
    @staticmethod
    def mock_exchange():
        """Fixture for mock exchange."""
        return MockExchangeFactory.create_mock_ccxt()
    
    @staticmethod
    def sample_market_data(count: int = 100):
        """Fixture for sample market data."""
        return MockMarketDataFactory.create_candles(count=count)
    
    @staticmethod
    def sample_signal():
        """Fixture for sample signal."""
        return MockMarketDataFactory.create_signal()


# Export commonly used items
__all__ = [
    'MockMarketDataFactory',
    'MockConfigFactory',
    'MockExchangeFactory',
    'MockEventBusFactory',
    'AssertionHelpers',
    'PerformanceTestHelpers',
    'PytestFixtures'
]

