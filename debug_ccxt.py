#!/usr/bin/env python3
"""
Debug CCXT Configuration
See what URLs CCXT is actually using
"""

import ccxt
import json
from pathlib import Path

def load_config():
    """Load the exchanges configuration."""
    config_path = Path("config/exchanges_config.json")
    if not config_path.exists():
        print("❌ Configuration file not found!")
        return None
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return None

def test_ccxt_config():
    """Test different CCXT configurations."""
    print("🔧 Debug CCXT Configuration")
    print("=" * 40)
    
    # Load configuration
    config = load_config()
    if not config:
        return
    
    # Get spot API credentials
    binance_config = config.get('binance', {})
    spot_config = binance_config.get('spot', {})
    
    api_key = spot_config.get('api_key')
    secret_key = spot_config.get('secret')
    
    print(f"🔑 Using Spot API Key: {api_key[:20]}...")
    
    # Test 1: Default CCXT configuration
    print("\n📡 Test 1: Default CCXT Configuration")
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': True,
        })
        
        print(f"  Testnet URLs: {exchange.urls.get('test', {})}")
        
        # Try to load markets
        markets = exchange.load_markets()
        print(f"  ✅ Markets loaded: {len(markets)} symbols")
        
        # Try to get ticker
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"  ✅ Ticker: BTC/USDT = ${ticker['last']}")
        
        # Try to get account info
        try:
            balance = exchange.fetch_balance()
            print(f"  ✅ Account info retrieved")
        except Exception as e:
            print(f"  ❌ Account info failed: {e}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: Custom testnet URLs
    print("\n📡 Test 2: Custom Testnet URLs")
    try:
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': True,
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision/api/v3',
                    'private': 'https://testnet.binance.vision/api/v3',
                }
            }
        })
        
        print(f"  Testnet URLs: {exchange.urls.get('test', {})}")
        
        # Try to load markets
        markets = exchange.load_markets()
        print(f"  ✅ Markets loaded: {len(markets)} symbols")
        
        # Try to get ticker
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"  ✅ Ticker: BTC/USDT = ${ticker['last']}")
        
        # Try to get account info
        try:
            balance = exchange.fetch_balance()
            print(f"  ✅ Account info retrieved")
        except Exception as e:
            print(f"  ❌ Account info failed: {e}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 3: No API key (public only)
    print("\n📡 Test 3: Public Only (No API Key)")
    try:
        exchange = ccxt.binance({
            'sandbox': True,
            'urls': {
                'api': {
                    'public': 'https://testnet.binance.vision/api/v3',
                    'private': 'https://testnet.binance.vision/api/v3',
                }
            }
        })
        
        print(f"  Testnet URLs: {exchange.urls.get('test', {})}")
        
        # Try to load markets
        markets = exchange.load_markets()
        print(f"  ✅ Markets loaded: {len(markets)} symbols")
        
        # Try to get ticker
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"  ✅ Ticker: BTC/USDT = ${ticker['last']}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

def main():
    """Main test function."""
    test_ccxt_config()
    
    print("\n📚 Analysis:")
    print("1. If Test 3 works, the URLs are correct")
    print("2. If Test 1 works, the API key is valid")
    print("3. If Test 2 fails, there's a URL configuration issue")

if __name__ == "__main__":
    main()
