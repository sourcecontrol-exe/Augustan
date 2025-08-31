#!/usr/bin/env python3
"""
Augustan Paper Trading Demo

Demo script for paper trading with real market data.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.paper_trading import PaperTradingEngine
from services.trading import RSIMACDStrategy
from services.data import DataLoader
from core.config import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_paper_trading_demo(duration_minutes=5, symbol='BTC/USDT'):
    """Run paper trading demo"""
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_active_config()
        
        # Initialize paper trading engine
        paper_trader = PaperTradingEngine(config)
        
        # Initialize strategy
        strategy = RSIMACDStrategy()
        
        # Initialize data loader
        data_loader = DataLoader()
        
        logger.info(f"Starting paper trading demo for {symbol}")
        logger.info(f"Demo duration: {duration_minutes} minutes")
        
        # Start paper trading session
        await paper_trader.start_session(
            strategy=strategy,
            symbol=symbol,
            duration_minutes=duration_minutes
        )
        
        # Print final results
        portfolio = paper_trader.get_portfolio_summary()
        print("\n" + "="*60)
        print("PAPER TRADING DEMO RESULTS")
        print("="*60)
        print(f"Symbol: {symbol}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Final Portfolio Value: ${portfolio['total_value']:,.2f}")
        print(f"Total Return: {portfolio['total_return']:.2f}%")
        print(f"Total Trades: {portfolio['total_trades']}")
        print(f"Win Rate: {portfolio['win_rate']:.1f}%")
        
    except Exception as e:
        logger.error(f"Paper trading demo failed: {e}")
        raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Augustan Paper Trading Demo")
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading symbol')
    parser.add_argument('--duration', type=int, default=5, help='Demo duration in minutes')
    parser.add_argument('--quick', action='store_true', help='Quick 1-minute demo')
    parser.add_argument('--full', action='store_true', help='Full 30-minute demo')
    
    args = parser.parse_args()
    
    if args.quick:
        duration = 1
    elif args.full:
        duration = 30
    else:
        duration = args.duration
    
    try:
        asyncio.run(run_paper_trading_demo(duration, args.symbol))
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
