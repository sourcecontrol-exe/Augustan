"""
Data Service Module

Handles all data fetching, loading, and management operations.
"""

from .data_loader import DataLoader, load_crypto_data, load_exchange_data, get_sample_btc_data, get_crypto_pairs
from .data_service import DataService

__all__ = [
    'DataLoader', 'DataService',
    'load_crypto_data', 'load_exchange_data', 
    'get_sample_btc_data', 'get_crypto_pairs'
]
