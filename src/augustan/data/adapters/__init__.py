"""
Adapter Plugin Registry

This module acts as a central registry for all exchange adapters.
It automatically discovers and registers available adapters.
"""

from .base_adapter import BaseAdapter
from .ccxt_adapter import CCXTAdapter
from .pi42_adapter import Pi42Adapter
from .pi42_public_adapter import Pi42PublicAdapter
from .pi42_mock_adapter import Pi42MockAdapter

# Registry of available adapters
AVAILABLE_ADAPTERS = {
    'ccxt': CCXTAdapter,
    'pi42': Pi42Adapter,
    'pi42_public': Pi42PublicAdapter,
    'pi42_mock': Pi42MockAdapter
}

def get_adapter(adapter_name: str, config: dict = None) -> BaseAdapter:
    """Get an adapter instance by name"""
    if adapter_name not in AVAILABLE_ADAPTERS:
        raise ValueError(f"Adapter '{adapter_name}' not found. Available: {list(AVAILABLE_ADAPTERS.keys())}")
    
    config = config or {}
    return AVAILABLE_ADAPTERS[adapter_name](config)

def list_adapters():
    """List all available adapters"""
    return list(AVAILABLE_ADAPTERS.keys())

def register_adapter(name: str, adapter_class):
    """Register a new adapter"""
    if not issubclass(adapter_class, BaseAdapter):
        raise ValueError(f"Adapter must inherit from BaseAdapter")
    
    AVAILABLE_ADAPTERS[name] = adapter_class

__all__ = [
    'BaseAdapter',
    'CCXTAdapter', 
    'Pi42Adapter',
    'Pi42PublicAdapter',
    'Pi42MockAdapter',
    'get_adapter',
    'list_adapters',
    'register_adapter',
    'AVAILABLE_ADAPTERS'
]
