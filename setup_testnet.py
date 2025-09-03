#!/usr/bin/env python3
"""
Binance Testnet Setup Script
Configure your own API tokens for Binance testnet
"""

import json
import os
import sys
from pathlib import Path

def get_user_input(prompt, default=None, password=False):
    """Get user input with optional default value"""
    if default:
        prompt = f"{prompt} (default: {default}): "
    else:
        prompt = f"{prompt}: "
    
    if password:
        import getpass
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value if value else default

def update_config_file(api_key, secret_key):
    """Update the exchanges configuration file with new API keys"""
    config_path = Path("config/exchanges_config.json")
    
    if not config_path.exists():
        print("❌ Configuration file not found!")
        return False
    
    try:
        # Read existing config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update Binance configuration
        if 'binance' not in config:
            config['binance'] = {}
        
        config['binance'].update({
            'api_key': api_key,
            'secret': secret_key,
            'enabled': True,
            'testnet': True
        })
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration updated: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating configuration: {e}")
        return False

def test_connection(api_key, secret_key):
    """Test the connection to Binance testnet"""
    print("\n🔍 Testing connection to Binance testnet...")
    
    try:
        from trading_system.data_feeder.binance_feeder import BinanceDataFeeder
        
        # Initialize feeder with testnet settings
        feeder = BinanceDataFeeder(
            api_key=api_key,
            api_secret=secret_key,
            testnet=True
        )
        
        # Test basic connection
        print("  Testing API connection...")
        account_info = feeder.get_account_info()
        
        if account_info and 'balances' in account_info:
            print("✅ API connection successful!")
            
            # Show account balance
            balances = account_info['balances']
            usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
            
            if usdt_balance:
                free_balance = float(usdt_balance['free'])
                print(f"💰 USDT Balance: {free_balance:.2f}")
                
                if free_balance < 100:
                    print("⚠️  Low balance warning: Consider adding more testnet USDT")
                else:
                    print("✅ Sufficient balance for testing")
            else:
                print("⚠️  No USDT balance found")
            
            return True
        else:
            print("❌ Failed to get account information")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🔧 Binance Testnet Setup")
    print("=" * 40)
    
    print("\n📋 Prerequisites:")
    print("1. Visit: https://testnet.binancefuture.com/")
    print("2. Create a testnet account")
    print("3. Generate API keys with trading permissions")
    print("4. Add some testnet USDT (recommended: 1000+ USDT)")
    
    print("\n🔑 Enter your Binance testnet API credentials:")
    
    # Get API key
    api_key = get_user_input("API Key")
    if not api_key:
        print("❌ API key is required!")
        sys.exit(1)
    
    # Get secret key
    secret_key = get_user_input("Secret Key", password=True)
    if not secret_key:
        print("❌ Secret key is required!")
        sys.exit(1)
    
    print("\n📝 Updating configuration...")
    
    # Update config file
    if not update_config_file(api_key, secret_key):
        sys.exit(1)
    
    # Test connection
    if not test_connection(api_key, secret_key):
        print("\n❌ Setup failed! Please check your API credentials.")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📚 Next steps:")
    print("1. Run: aug live testnet --dry-run")
    print("2. Test volume analysis: aug volume analyze --enhanced")
    print("3. Test position sizing: aug position analyze --symbol BTC/USDT --budget 1000")
    print("4. Start live trading: aug live start --paper")
    
    print("\n🔒 Security reminder:")
    print("- Keep your API keys secure")
    print("- Never share them publicly")
    print("- Use testnet only for testing")
    print("- Monitor your API usage")

if __name__ == "__main__":
    main()
