"""
Command Line Interface for Augustan Trading Bot
"""

import argparse
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from augustan import __version__


def run_paper_trading(args):
    """Run paper trading session"""
    print("🚀 Starting Augustan Paper Trading...")
    
    try:
        # Import and run the demo
        from scripts.demo_paper_trading import run_quick_demo, run_paper_trading_demo
        
        if args.quick:
            print("Running quick paper trading demo...")
            run_quick_demo()
        else:
            print("Running full paper trading session...")
            asyncio.run(run_paper_trading_demo())
    except ImportError as e:
        print(f"❌ Error importing paper trading module: {e}")
        print("Make sure the scripts are properly installed.")
    except Exception as e:
        print(f"❌ Error running paper trading: {e}")


def run_backtesting(args):
    """Run backtesting session"""
    print("📊 Starting Augustan Backtesting...")
    
    try:
        # Import and run backtest
        from scripts.run_backtest import main as run_backtest_main
        
        if args.strategy:
            print(f"Running backtest for strategy: {args.strategy}")
        else:
            print("Running default backtesting session...")
            
        run_backtest_main()
    except ImportError as e:
        print(f"❌ Error importing backtesting module: {e}")
        print("Make sure the scripts are properly installed.")
    except Exception as e:
        print(f"❌ Error running backtest: {e}")


def run_live_trading(args):
    """Run live trading bot"""
    print("⚡ Starting Augustan Live Trading Bot...")
    
    try:
        from scripts.main import main as live_main
        
        if args.cycles:
            print(f"Running for {args.cycles} cycles...")
        else:
            print("Running continuous trading...")
            
        live_main()
    except ImportError as e:
        print(f"❌ Error importing live trading module: {e}")
        print("Make sure the scripts are properly installed.")
    except Exception as e:
        print(f"❌ Error running live trading: {e}")


def run_scanner(args):
    """Run market scanner"""
    print("🔍 Starting Augustan Market Scanner...")
    
    try:
        # Import scanner functionality
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from scanner import Scanner
        from data_service import DataService
        from config import config
        
        # Initialize data service
        exchanges = config.get_all_exchanges()
        if not exchanges:
            print("❌ No exchanges configured")
            return
            
        exchange_name = list(exchanges.keys())[0]
        exchange_config = exchanges[exchange_name]
        
        data_service = DataService('ccxt', {
            'exchange_id': exchange_config.get('exchange', exchange_name),
            'api_key': exchange_config.get('api_key'),
            'api_secret': exchange_config.get('api_secret'),
            'testnet': exchange_config.get('testnet', True),
            'default_type': exchange_config.get('default_type', 'future')
        })
        
        scanner = Scanner(data_service)
        opportunities = scanner.find_opportunities()
        
        print("\n📈 Market Opportunities Found:")
        for exchange_id, symbols in opportunities.items():
            print(f"\n{exchange_id.upper()}:")
            for symbol in symbols[:10]:  # Show top 10
                print(f"  • {symbol}")
                
    except Exception as e:
        print(f"❌ Error running scanner: {e}")


def run_tests(args):
    """Run test suite"""
    print("🧪 Running Augustan Test Suite...")
    
    try:
        from scripts.run_tests import main as test_main
        test_main()
    except ImportError as e:
        print(f"❌ Error importing test module: {e}")
    except Exception as e:
        print(f"❌ Error running tests: {e}")


def show_config(args):
    """Show current configuration"""
    print("⚙️  Augustan Configuration:")
    
    try:
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from config import config
        
        print(f"\nActive Environment: {config.environment}")
        print(f"Config File: {config.config_file}")
        
        # Show trading config
        trading_config = config.get_trading_config()
        print(f"\n📊 Trading Configuration:")
        for key, value in trading_config.items():
            print(f"  {key}: {value}")
            
        # Show exchanges
        exchanges = config.get_all_exchanges()
        print(f"\n🏦 Configured Exchanges:")
        for name, exchange_config in exchanges.items():
            print(f"  {name}: {exchange_config.get('exchange', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")


def show_status():
    """Show system status"""
    print(f"🤖 Augustan Trading Bot v{__version__}")
    print("📈 Advanced Algorithmic Trading System")
    print("\n🚀 Available Commands:")
    print("  paper-trading    Run paper trading simulation")
    print("  backtest         Run strategy backtesting")
    print("  live             Run live trading bot")
    print("  scan             Run market scanner")
    print("  test             Run test suite")
    print("  config           Show configuration")
    print("  --version        Show version information")
    print("\n💡 Examples:")
    print("  augustan paper-trading --quick")
    print("  augustan backtest --strategy RSI_MACD")
    print("  augustan scan")
    print("  augustan config")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Augustan - Advanced Algorithmic Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  augustan paper-trading --quick    Run quick paper trading demo
  augustan backtest                 Run backtesting session
  augustan live --cycles 5         Run live trading for 5 cycles
  augustan scan                     Scan for trading opportunities
  augustan test                     Run test suite
  augustan config                   Show current configuration
        """
    )
    
    parser.add_argument('--version', action='version', version=f'Augustan {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Paper trading command
    paper_parser = subparsers.add_parser('paper-trading', help='Run paper trading simulation')
    paper_parser.add_argument('--quick', action='store_true', help='Run quick demo')
    paper_parser.add_argument('--full', action='store_true', help='Run full session')
    
    # Backtesting command
    backtest_parser = subparsers.add_parser('backtest', help='Run strategy backtesting')
    backtest_parser.add_argument('--strategy', help='Strategy to backtest')
    backtest_parser.add_argument('--symbol', help='Symbol to backtest')
    backtest_parser.add_argument('--timeframe', help='Timeframe for backtesting')
    
    # Live trading command
    live_parser = subparsers.add_parser('live', help='Run live trading bot')
    live_parser.add_argument('--cycles', type=int, help='Number of trading cycles')
    live_parser.add_argument('--interval', type=int, default=60, help='Seconds between cycles')
    
    # Scanner command
    scan_parser = subparsers.add_parser('scan', help='Run market scanner')
    scan_parser.add_argument('--exchange', help='Specific exchange to scan')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run test suite')
    test_parser.add_argument('--coverage', action='store_true', help='Run with coverage')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show configuration')
    config_parser.add_argument('--env', help='Show specific environment config')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'paper-trading':
            run_paper_trading(args)
        elif args.command == 'backtest':
            run_backtesting(args)
        elif args.command == 'live':
            run_live_trading(args)
        elif args.command == 'scan':
            run_scanner(args)
        elif args.command == 'test':
            run_tests(args)
        elif args.command == 'config':
            show_config(args)
        else:
            show_status()
    except KeyboardInterrupt:
        print("\n👋 Augustan stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
