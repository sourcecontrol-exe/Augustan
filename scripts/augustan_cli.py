#!/usr/bin/env python3
"""
Augustan CLI - Standalone command-line interface
Direct access to all Augustan trading bot functionality
"""

import sys
import os
import argparse
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def main():
    """Main entry point for standalone CLI"""
    parser = argparse.ArgumentParser(
        description="Augustan Trading Bot - Standalone CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Commands:
  --backtest-quick     Run quick backtesting demo
  --paper-quick        Run quick paper trading demo
  --scan-markets       Scan for trading opportunities
  --show-config        Display current configuration
  --run-tests          Execute test suite
  --live-demo          Run live trading demo (1 cycle)

Examples:
  python augustan_cli.py --backtest-quick
  python augustan_cli.py --paper-quick
  python augustan_cli.py --scan-markets
        """
    )
    
    # Quick action flags
    parser.add_argument('--backtest-quick', action='store_true', 
                       help='Run quick backtesting demo')
    parser.add_argument('--paper-quick', action='store_true',
                       help='Run quick paper trading demo')
    parser.add_argument('--scan-markets', action='store_true',
                       help='Scan for trading opportunities')
    parser.add_argument('--show-config', action='store_true',
                       help='Display current configuration')
    parser.add_argument('--run-tests', action='store_true',
                       help='Execute test suite')
    parser.add_argument('--live-demo', action='store_true',
                       help='Run live trading demo (1 cycle)')
    
    args = parser.parse_args()
    
    try:
        if args.backtest_quick:
            print("🚀 Quick Backtesting Demo")
            print("=" * 40)
            from backtesting.demo_backtest import run_single_strategy_demo
            run_single_strategy_demo()
            
        elif args.paper_quick:
            print("💰 Quick Paper Trading Demo")
            print("=" * 40)
            from paper_trading.demo_paper_trading import run_quick_demo
            run_quick_demo()
            
        elif args.scan_markets:
            print("🔍 Market Scanner")
            print("=" * 40)
            from cli_demos import demo_market_scanner
            demo_market_scanner()
            
        elif args.show_config:
            print("⚙️  Configuration Display")
            print("=" * 40)
            from config import config
            print(f"Environment: {config.environment}")
            print(f"Config File: {config.config_file}")
            
            trading_config = config.get_trading_config()
            print("\n📊 Trading Settings:")
            for key, value in trading_config.items():
                print(f"  {key}: {value}")
                
        elif args.run_tests:
            print("🧪 Test Suite")
            print("=" * 40)
            from scripts.run_tests import main as test_main
            test_main()
            
        elif args.live_demo:
            print("⚡ Live Trading Demo")
            print("=" * 40)
            from scripts.main import AugustanBot
            bot = AugustanBot()
            bot.run(cycles=1)
            
        else:
            # Show help if no arguments
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
