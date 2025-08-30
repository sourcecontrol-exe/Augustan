#!/usr/bin/env python3
"""
Configuration Environment Switcher for Augustan Trading Bot

This script allows you to easily switch between different configuration
environments (testing, live, default) and view current configuration status.
"""

import os
import sys
import argparse
from pathlib import Path
from config_manager import ConfigManager

def switch_environment(environment: str):
    """Switch to the specified environment."""
    try:
        config_manager = ConfigManager(environment)
        print(f"✅ Switched to {environment} environment")
        print(f"📁 Configuration file: {config_manager.config_path}")
        
        # Show environment info
        info = config_manager.get_environment_info()
        print(f"\n🔧 Environment Information:")
        print(f"   Environment: {info['environment']}")
        print(f"   Testnet: {info['testnet']}")
        print(f"   Total Capital: ${info['total_capital']:,}")
        print(f"   Timeframe: {info['timeframe']}")
        print(f"   Risk per Trade: {info['risk_per_trade']:.1%}")
        
        # Validate configuration
        if config_manager.validate():
            print("\n✅ Configuration validation passed")
        else:
            print("\n❌ Configuration validation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to switch to {environment} environment: {e}")
        sys.exit(1)

def show_current_environment():
    """Show current environment information."""
    try:
        config_manager = ConfigManager()
        info = config_manager.get_environment_info()
        
        print(f"🔧 Current Environment: {info['environment']}")
        print(f"📁 Configuration file: {info['config_file']}")
        print(f"🌐 Testnet: {info['testnet']}")
        print(f"💰 Total Capital: ${info['total_capital']:,}")
        print(f"⏱️  Timeframe: {info['timeframe']}")
        print(f"⚠️  Risk per Trade: {info['risk_per_trade']:.1%}")
        
    except Exception as e:
        print(f"❌ Failed to get environment information: {e}")
        sys.exit(1)

def list_environments():
    """List available environments."""
    configs_dir = Path('configs')
    
    print("📁 Available Configuration Environments:")
    
    # Check testing config
    testing_config = configs_dir / 'testing' / 'config.json'
    if testing_config.exists():
        print("   🧪 testing/ - For testing and development")
    else:
        print("   ❌ testing/ - Not found")
    
    # Check live config
    live_config = configs_dir / 'live' / 'config.json'
    if live_config.exists():
        print("   🚀 live/ - For live trading (use with caution!)")
    else:
        print("   ❌ live/ - Not found")
    
    # Check default config
    default_config = configs_dir / 'default.json'
    if default_config.exists():
        print("   📋 default.json - Fallback configuration")
    else:
        print("   ❌ default.json - Not found")

def create_environment(environment: str):
    """Create a new environment configuration."""
    configs_dir = Path('configs')
    
    if environment == 'testing':
        target_dir = configs_dir / 'testing'
        target_file = target_dir / 'config.json'
        
        if target_file.exists():
            print(f"⚠️  {environment} environment already exists")
            return
        
        # Create testing config
        target_dir.mkdir(exist_ok=True)
        testing_config = {
            "trading": {
                "timeframe": "3m",
                "stake_currency": "USDT",
                "total_capital": 1000,
                "exchange_type": "future",
                "testnet": True
            },
            "scanner": {
                "base_currency": "USDT",
                "market_limit": 50,
                "min_24h_change": 3.0
            },
            "risk_management": {
                "risk_per_trade": 0.005,
                "risk_reward_ratio": 2.5,
                "stop_loss_multiplier": 1.5
            },
            "exchanges": {
                "binance": {"enabled": True, "testnet": True},
                "bybit": {"enabled": True, "testnet": True}
            }
        }
        
        import json
        with open(target_file, 'w') as f:
            json.dump(testing_config, f, indent=2)
        
        print(f"✅ Created {environment} environment configuration")
        
    elif environment == 'live':
        print("⚠️  Live trading environment creation is disabled for safety")
        print("   Please create configs/live/config.json manually with your settings")
        
    else:
        print(f"❌ Unknown environment: {environment}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Augustan Trading Bot Configuration Environment Switcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python switch_env.py --current          # Show current environment
  python switch_env.py --switch testing   # Switch to testing environment
  python switch_env.py --switch live      # Switch to live environment
  python switch_env.py --list             # List available environments
  python switch_env.py --create testing   # Create testing environment
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--current', action='store_true', help='Show current environment')
    group.add_argument('--switch', metavar='ENV', help='Switch to environment (testing/live)')
    group.add_argument('--list', action='store_true', help='List available environments')
    group.add_argument('--create', metavar='ENV', help='Create new environment (testing)')
    
    args = parser.parse_args()
    
    if args.current:
        show_current_environment()
    elif args.switch:
        if args.switch not in ['testing', 'live']:
            print("❌ Invalid environment. Use 'testing' or 'live'")
            sys.exit(1)
        switch_environment(args.switch)
    elif args.list:
        list_environments()
    elif args.create:
        if args.create not in ['testing']:
            print("❌ Can only create 'testing' environment for safety")
            sys.exit(1)
        create_environment(args.create)

if __name__ == '__main__':
    main()
