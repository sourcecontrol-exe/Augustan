"""
Pytest configuration and shared fixtures for Augustan Trading System tests.
"""
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any

from trading_system.core.exchange_manager import ExchangeManager, ExchangeConfig
from trading_system.core.data_handler import DataHandler, DataConfig
from trading_system.core.paper_trading import PaperTradingEngine, PaperTradingConfig


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def exchange_configs():
    """Create test exchange configurations."""
    return [
        ExchangeConfig(
            name="binance",
            api_key="test_key",
            secret="test_secret",
            sandbox=True,
            enabled=True
        ),
        ExchangeConfig(
            name="bybit", 
            api_key="test_key",
            secret="test_secret",
            sandbox=True,
            enabled=True
        )
    ]


@pytest.fixture
def data_config():
    """Create test data handler configuration."""
    return DataConfig(
        max_history_size=1000,
        data_validation=True,
        normalize_prices=True,
        cache_duration=60
    )


@pytest.fixture
def paper_config():
    """Create test paper trading configuration."""
    return PaperTradingConfig(
        initial_balance=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
        max_position_size=0.1,
        enable_slippage=True,
        enable_commission=True
    )


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    return {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'open': 50000.0,
        'high': 50001.0,
        'low': 49999.0,
        'close': 50000.5,
        'volume': 100.0
    }


@pytest.fixture
def sample_orderbook_data():
    """Create sample orderbook data for testing."""
    return {
        'bids': [(50000.0, 1.5), (49999.0, 2.0), (49998.0, 1.0)],
        'asks': [(50001.0, 1.2), (50002.0, 2.5), (50003.0, 1.8)],
        'timestamp': int(datetime.now().timestamp() * 1000),
        'sequence': 1
    }


@pytest.fixture
def sample_ticker_data():
    """Create sample ticker data for testing."""
    return {
        'last': 50000.5,
        'bid': 50000.0,
        'ask': 50001.0,
        'volume': 1000.0,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "paper_trading: mark test as a paper trading test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names."""
    for item in items:
        # Add markers based on test file names
        if "test_orderbook" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_paper_trading" in item.nodeid:
            item.add_marker(pytest.mark.paper_trading)
        
        # Mark slow tests
        if "performance" in item.name or "concurrent" in item.name:
            item.add_marker(pytest.mark.slow)
