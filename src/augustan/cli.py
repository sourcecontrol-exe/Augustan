"""
Command Line Interface for Augustan Trading Bot
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from augustan import __version__


def run_paper_trading(args):
    """Run paper trading session"""
    print("🚀 Starting Augustan Paper Trading...")
    
    # Import and run the demo
    from scripts.demo_paper_trading import run_quick_demo, run_paper_trading_demo
    
    if args.quick:
        run_quick_demo()
    else:
        asyncio.run(run_paper_trading_demo())


def run_backtesting(args):
    """Run backtesting session"""
    print("📊 Starting Augustan Backtesting...")
    
    # Import and run backtest
    from scripts.run_backtest import main as run_backtest_main
    run_backtest_main()


def show_status():
    """Show system status"""
    print(f"🤖 Augustan Trading Bot v{__version__}")
    print("📈 Advanced Algorithmic Trading System")
    print("\nAvailable Commands:")
    print("  paper-trading    Run paper trading simulation")
    print("  backtest         Run strategy backtesting")
    print("  --version        Show version information")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Augustan - Advanced Algorithmic Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--version', action='version', version=f'Augustan {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Paper trading command
    paper_parser = subparsers.add_parser('paper-trading', help='Run paper trading')
    paper_parser.add_argument('--quick', action='store_true', help='Run quick demo')
    paper_parser.add_argument('--full', action='store_true', help='Run full session')
    
    # Backtesting command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtesting')
    backtest_parser.add_argument('--strategy', help='Strategy to backtest')
    
    args = parser.parse_args()
    
    if args.command == 'paper-trading':
        run_paper_trading(args)
    elif args.command == 'backtest':
        run_backtesting(args)
    else:
        show_status()


if __name__ == '__main__':
    main()
