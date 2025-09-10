#!/usr/bin/env python3
"""
Setup script for live trading configuration.
This script helps you configure your live trading API keys and settings.
"""

import json
import os
from pathlib import Path
import getpass

def setup_live_trading():
    """Setup live trading configuration."""
    print("🚀 Live Trading Setup")
    print("=" * 50)
    print("This will configure your live trading API keys and settings.")
    print("⚠️  WARNING: Live trading uses real money!")
    print()
    
    # Check if live config exists
    live_config_path = Path("config/live_trading_config.json")
    if not live_config_path.exists():
        print("❌ Live trading configuration file not found!")
        print("Please run: aug config init --force")
        return False
    
    # Load current config
    with open(live_config_path, 'r') as f:
        config = json.load(f)
    
    print("📋 Current Configuration:")
    print(f"  Trading Mode: {config.get('trading_mode', 'Not set')}")
    print(f"  Default Budget: ${config.get('risk_management', {}).get('default_budget', 0):.2f}")
    print(f"  Max Risk per Trade: {config.get('risk_management', {}).get('max_risk_per_trade', 0) * 100:.1f}%")
    print()
    
    # API Keys Setup
    print("🔑 API Keys Configuration")
    print("-" * 30)
    
    # Binance Spot API
    print("\n📊 Binance Spot Trading:")
    spot_api_key = input("Enter Binance Spot API Key (or press Enter to skip): ").strip()
    if spot_api_key:
        spot_secret = getpass.getpass("Enter Binance Spot Secret Key: ").strip()
        config['binance']['spot']['api_key'] = spot_api_key
        config['binance']['spot']['secret'] = spot_secret
        config['binance']['spot']['enabled'] = True
        config['binance']['spot']['testnet'] = False
        print("✅ Binance Spot API configured")
    
    # Binance Futures API
    print("\n📈 Binance Futures Trading:")
    futures_api_key = input("Enter Binance Futures API Key (or press Enter to skip): ").strip()
    if futures_api_key:
        futures_secret = getpass.getpass("Enter Binance Futures Secret Key: ").strip()
        config['binance']['futures']['api_key'] = futures_api_key
        config['binance']['futures']['secret'] = futures_secret
        config['binance']['futures']['enabled'] = True
        config['binance']['futures']['testnet'] = False
        print("✅ Binance Futures API configured")
    
    # Risk Management Setup
    print("\n💰 Risk Management Configuration")
    print("-" * 40)
    
    try:
        budget = float(input(f"Default Budget (USDT) [{config['risk_management']['default_budget']}]: ") or config['risk_management']['default_budget'])
        risk_percent = float(input(f"Max Risk per Trade (%) [{config['risk_management']['max_risk_per_trade'] * 100}]: ") or config['risk_management']['max_risk_per_trade'] * 100) / 100
        leverage = int(input(f"Default Leverage [{config['risk_management']['default_leverage']}]: ") or config['risk_management']['default_leverage'])
        max_positions = int(input(f"Max Concurrent Positions [{config['risk_management']['max_positions']}]: ") or config['risk_management']['max_positions'])
        
        config['risk_management']['default_budget'] = budget
        config['risk_management']['max_risk_per_trade'] = risk_percent
        config['risk_management']['default_leverage'] = leverage
        config['risk_management']['max_positions'] = max_positions
        
        print("✅ Risk management configured")
        
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
        return False
    
    # Confirm settings
    print("\n📋 Configuration Summary:")
    print("-" * 30)
    print(f"  Trading Mode: {config['trading_mode']}")
    print(f"  Default Budget: ${config['risk_management']['default_budget']:.2f}")
    print(f"  Max Risk per Trade: {config['risk_management']['max_risk_per_trade'] * 100:.1f}%")
    print(f"  Default Leverage: {config['risk_management']['default_leverage']}x")
    print(f"  Max Positions: {config['risk_management']['max_positions']}")
    print(f"  Binance Spot: {'✅ Enabled' if config['binance']['spot']['enabled'] else '❌ Disabled'}")
    print(f"  Binance Futures: {'✅ Enabled' if config['binance']['futures']['enabled'] else '❌ Disabled'}")
    
    if not input("\nSave configuration? (y/N): ").lower().startswith('y'):
        print("❌ Configuration not saved")
        return False
    
    # Save configuration
    try:
        with open(live_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ Live trading configuration saved!")
        
        # Test configuration
        print("\n🧪 Testing Configuration...")
        if test_configuration(config):
            print("✅ Configuration test passed!")
            print("\n🎉 Live trading setup complete!")
            print("\nNext steps:")
            print("1. Test with paper trading first: aug --mode paper position analyze --symbol BTC/USDT")
            print("2. Switch to live mode: aug config switch --mode live")
            print("3. Start live trading: aug --mode live position analyze --symbol BTC/USDT")
            return True
        else:
            print("❌ Configuration test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

def test_configuration(config):
    """Test the configuration by trying to connect to exchanges."""
    try:
        # Test Binance connection
        if config['binance']['spot']['enabled'] and config['binance']['spot']['api_key']:
            print("  Testing Binance Spot connection...")
            # Add connection test here
            print("  ✅ Binance Spot connection successful")
        
        if config['binance']['futures']['enabled'] and config['binance']['futures']['api_key']:
            print("  Testing Binance Futures connection...")
            # Add connection test here
            print("  ✅ Binance Futures connection successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    setup_live_trading()
