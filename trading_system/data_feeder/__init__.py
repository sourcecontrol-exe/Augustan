"""
Data Feeder Module

Provides data feeding capabilities for the trading system.
"""

# Export old implementations for backward compatibility
from .binance_feeder import BinanceDataFeeder
from .binance_futures_feeder import BinanceFuturesFeeder

# Export new refactored implementations
from .exchange_client import (
    ExchangeClient,
    ExchangeCredentials,
    ExchangeConfig,
)
from .binance_exchange_client import BinanceExchangeClient


def create_binance_spot_client(
    api_key: str = None,
    api_secret: str = None,
    testnet: bool = True,
    default_symbols: list = None,
    config_manager = None
) -> BinanceExchangeClient:
    """
    Factory function to create a Binance spot exchange client.
    
    Args:
        api_key: Binance API key
        api_secret: Binance secret
        testnet: Use testnet (default: True)
        default_symbols: Default trading symbols
        config_manager: Optional config manager for credentials
        
    Returns:
        BinanceExchangeClient instance
    """
    # Get credentials from config manager if not provided
    if api_key is None or api_secret is None:
        if config_manager:
            exchange_config = config_manager.get_exchange_config('binance')
            if 'spot' in exchange_config:
                api_key = exchange_config['spot'].get('api_key')
                api_secret = exchange_config['spot'].get('secret')
                testnet = exchange_config.get('testnet', True)
    
    # Use default symbols if not provided
    if default_symbols is None:
        default_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT',
            'SOL/USDT', 'XRP/USDT', 'DOT/USDT', 'AVAX/USDT'
        ]
    
    # Create configuration
    credentials = ExchangeCredentials(
        api_key=api_key,
        secret=api_secret,
        testnet=testnet
    )
    
    config = ExchangeConfig(
        credentials=credentials,
        default_symbols=default_symbols
    )
    
    return BinanceExchangeClient(config, market_type='spot')


def create_binance_futures_client(
    api_key: str = None,
    api_secret: str = None,
    testnet: bool = True,
    default_symbols: list = None,
    config_manager = None
) -> BinanceExchangeClient:
    """
    Factory function to create a Binance futures exchange client.
    
    Args:
        api_key: Binance API key
        api_secret: Binance secret
        testnet: Use testnet (default: True)
        default_symbols: Default trading symbols
        config_manager: Optional config manager for credentials
        
    Returns:
        BinanceExchangeClient instance
    """
    # Get credentials from config manager if not provided
    if api_key is None or api_secret is None:
        if config_manager:
            exchange_config = config_manager.get_exchange_config('binance')
            if 'futures' in exchange_config:
                api_key = exchange_config['futures'].get('api_key')
                api_secret = exchange_config['futures'].get('secret')
                testnet = exchange_config.get('testnet', True)
    
    # Use default symbols if not provided
    if default_symbols is None:
        default_symbols = [
            'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT',
            'ADA/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT'
        ]
    
    # Create configuration
    credentials = ExchangeCredentials(
        api_key=api_key,
        secret=api_secret,
        testnet=testnet
    )
    
    config = ExchangeConfig(
        credentials=credentials,
        default_symbols=default_symbols
    )
    
    return BinanceExchangeClient(config, market_type='futures')


__all__ = [
    # Old implementations (backward compatibility)
    'BinanceDataFeeder',
    'BinanceFuturesFeeder',
    
    # New implementations
    'ExchangeClient',
    'ExchangeCredentials',
    'ExchangeConfig',
    'BinanceExchangeClient',
    
    # Factory functions
    'create_binance_spot_client',
    'create_binance_futures_client',
]
