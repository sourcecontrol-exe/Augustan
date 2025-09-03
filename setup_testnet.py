#!/usr/bin/env python3
"""
Binance Testnet Configuration Setup

This script helps you configure your Binance testnet API keys
for the dry-run testing.
"""

import json
import os
from pathlib import Path


def setup_testnet_config():
    """Setup Binance testnet configuration."""
    print("🚀 Binance Testnet Configuration Setup")
    print("=" * 60)
    print("This will help you configure your Binance testnet API keys")
    print("for the dry-run testing.")
    print("=" * 60)
    
    # Check if config file exists
    config_path = Path("config/exchanges_config.json")
    if not config_path.exists():
        print("❌ Configuration file not found. Please run 'aug config init' first.")
        return False
    
    # Load current config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("\n📋 Current Binance Configuration:")
    binance_config = config.get("binance", {})
    print(f"   Testnet Enabled: {binance_config.get('testnet', False)}")
    print(f"   API Key: {'✅ Configured' if binance_config.get('api_key') else '❌ Not configured'}")
    print(f"   Secret: {'✅ Configured' if binance_config.get('secret') else '❌ Not configured'}")
    
    # Get testnet API keys
    print("\n🔑 Enter your Binance Testnet API credentials:")
    print("(Get them from: https://testnet.binancefuture.com/en/futures/BTCUSDT)")
    
    api_key = input("API Key: ").strip()
    secret = input("Secret Key: ").strip()
    
    if not api_key or not secret:
        print("❌ API key and secret are required.")
        return False
    
    # Update configuration
    config["binance"] = {
        "api_key": api_key,
        "secret": secret,
        "enabled": True,
        "testnet": True  # Enable testnet
    }
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Configuration updated successfully!")
    print("📋 Updated Binance Configuration:")
    print(f"   Testnet Enabled: {config['binance']['testnet']}")
    print(f"   API Key: ✅ Configured")
    print(f"   Secret: ✅ Configured")
    
    # Test configuration
    print("\n🧪 Testing configuration...")
    try:
        from trading_system.core.config_manager import get_config_manager
        from trading_system.data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
        from trading_system.core.futures_models import ExchangeType
        
        config_manager = get_config_manager(str(config_path))
        limits_fetcher = ExchangeLimitsFetcher()
        
        # Test connection
        exchange = limits_fetcher.exchanges.get(ExchangeType.BINANCE)
        if exchange:
            try:
                balance = exchange.fetch_balance()
                usdt_balance = balance.get('USDT', {}).get('free', 0)
                print(f"✅ Connection successful! USDT Balance: {usdt_balance}")
                
                if usdt_balance < 100:
                    print("⚠️ Low testnet balance. Consider adding more USDT for testing.")
                    print("   You can get testnet USDT from: https://testnet.binancefuture.com/en/futures/BTCUSDT")
                
                return True
                
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                return False
        else:
            print("❌ Exchange not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def main():
    """Main function."""
    success = setup_testnet_config()
    
    if success:
        print("\n🎉 Testnet configuration completed successfully!")
        print("You can now run the dry-run test with:")
        print("   python3 testnet_dry_run.py")
    else:
        print("\n❌ Testnet configuration failed.")
        print("Please check your API keys and try again.")


if __name__ == "__main__":
    main()
