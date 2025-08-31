#!/usr/bin/env python3
"""
Augustan Backtesting Script
Easy-to-use script for running backtests and parameter optimizations
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backtesting.backtester import AugustanBacktester, BacktestConfig
from strategy import RSIMACDStrategy, BollingerRSIStrategy, MeanReversionStrategy
from backtesting import optimize
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_sample_data(symbol='BTC-USD', period='2y', interval='1d'):
    """Load sample data using yfinance"""
    try:
        logger.info("Loading data for %s (%s, %s)", symbol, period, interval)
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            raise ValueError("No data found for %s" % symbol)
        
        # Ensure proper column names
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        logger.info("Loaded %d bars from %s to %s", len(data), data.index[0], data.index[-1])
        return data
        
    except Exception as e:
        logger.error("Error loading data: %s", e)
        raise

def run_single_backtest(strategy_class, data, **params):
    """Run a single backtest"""
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001
    )
    
    backtester = AugustanBacktester(config)
    result = backtester.run_backtest(strategy_class, data, **params)
    
    return result

def run_optimization(strategy_class, data, param_ranges):
    """Run parameter optimization"""
    from backtesting import Backtest
    
    logger.info(f"Starting optimization for {strategy_class.__name__}")
    
    # Prepare data
    config = BacktestConfig()
    backtester = AugustanBacktester(config)
    prepared_data = backtester._prepare_data(data)
    
    # Create backtest instance
    bt = Backtest(
        prepared_data,
        strategy_class,
        cash=100000,
        commission=0.001
    )
    
    # Run optimization
    stats = bt.optimize(**param_ranges, maximize='Sharpe Ratio')
    
    return stats

def print_results(result):
    """Print backtest results in a formatted way"""
    print("\n" + "="*60)
    print(f"BACKTEST RESULTS: {result.strategy_name}")
    print("="*60)
    
    stats = result.stats
    
    # Key metrics
    print(f"📊 Performance Metrics:")
    print(f"   Total Return:     {stats['Return [%]']:.2f}%")
    print(f"   Annual Return:    {stats.get('Annual Return [%]', 'N/A')}")
    print(f"   Volatility:       {stats.get('Volatility [%]', 'N/A')}")
    print(f"   Sharpe Ratio:     {stats['Sharpe Ratio']:.2f}")
    print(f"   Max Drawdown:     {stats['Max. Drawdown [%]']:.2f}%")
    
    # Trading metrics
    print(f"\n💰 Trading Metrics:")
    print(f"   Total Trades:     {stats['# Trades']}")
    print(f"   Win Rate:         {stats['Win Rate [%]']:.1f}%")
    print(f"   Best Trade:       {stats['Best Trade [%]']:.2f}%")
    print(f"   Worst Trade:      {stats['Worst Trade [%]']:.2f}%")
    print(f"   Avg Trade:        {stats['Avg. Trade [%]']:.2f}%")
    
    # Duration metrics
    print(f"\n⏱️  Duration Metrics:")
    print(f"   Avg Trade Duration: {stats.get('Avg. Trade Duration', 'N/A')}")
    print(f"   Max Trade Duration: {stats.get('Max. Trade Duration', 'N/A')}")
    
    print("="*60)

def save_results(result, output_dir="backtest_results"):
    """Save backtest results to files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    strategy_dir = output_path / result.strategy_name
    strategy_dir.mkdir(exist_ok=True)
    
    # Save stats as JSON
    stats_dict = dict(result.stats)
    # Convert non-serializable objects to strings
    for key, value in stats_dict.items():
        if hasattr(value, 'total_seconds'):  # timedelta
            stats_dict[key] = str(value)
        elif isinstance(value, (pd.Timestamp, datetime)):
            stats_dict[key] = value.isoformat()
    
    import json
    with open(strategy_dir / 'stats.json', 'w') as f:
        json.dump(stats_dict, f, indent=2, default=str)
    
    # Save equity curve
    result.equity_curve.to_csv(strategy_dir / 'equity_curve.csv')
    
    # Save trades if available
    if not result.trades.empty:
        result.trades.to_csv(strategy_dir / 'trades.csv')
    
    logger.info(f"Results saved to {strategy_dir}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Augustan Backtesting Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_backtest.py --strategy rsi_macd
  python run_backtest.py --strategy bollinger_rsi --symbol ETH-USD
  python run_backtest.py --optimize --strategy rsi_macd
  python run_backtest.py --compare-all --symbol BTC-USD
        """
    )
    
    parser.add_argument('--strategy', choices=['rsi_macd', 'bollinger_rsi', 'mean_reversion'],
                       default='rsi_macd', help='Strategy to backtest')
    parser.add_argument('--symbol', default='BTC-USD', help='Symbol to backtest')
    parser.add_argument('--period', default='2y', help='Data period (1y, 2y, 5y, max)')
    parser.add_argument('--interval', default='1d', help='Data interval (1h, 4h, 1d)')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--compare-all', action='store_true', help='Compare all strategies')
    parser.add_argument('--save', action='store_true', help='Save results to files')
    
    args = parser.parse_args()
    
    try:
        # Load data
        data = load_sample_data(args.symbol, args.period, args.interval)
        
        # Strategy mapping
        strategies = {
            'rsi_macd': RSIMACDStrategy,
            'bollinger_rsi': BollingerRSIStrategy,
            'mean_reversion': MeanReversionStrategy
        }
        
        if args.compare_all:
            # Compare all strategies
            print(f"\n🔍 Comparing all strategies on {args.symbol}")
            results = []
            
            for name, strategy_class in strategies.items():
                try:
                    result = run_single_backtest(strategy_class, data)
                    results.append((name, result))
                    print(f"✅ {name}: Sharpe={result.stats['Sharpe Ratio']:.2f}")
                except Exception as e:
                    print(f"❌ {name}: Error - {e}")
            
            # Sort by Sharpe ratio
            results.sort(key=lambda x: x[1].stats['Sharpe Ratio'], reverse=True)
            
            print(f"\n🏆 Strategy Rankings:")
            for i, (name, result) in enumerate(results, 1):
                stats = result.stats
                print(f"{i}. {name.upper()}")
                print(f"   Sharpe: {stats['Sharpe Ratio']:.2f} | "
                      f"Return: {stats['Return [%]']:.1f}% | "
                      f"Drawdown: {stats['Max. Drawdown [%]']:.1f}%")
        
        elif args.optimize:
            # Run optimization
            strategy_class = strategies[args.strategy]
            
            # Define parameter ranges for optimization
            param_ranges = {}
            if args.strategy == 'rsi_macd':
                param_ranges = {
                    'rsi_length': range(10, 21, 2),
                    'rsi_oversold': range(25, 36, 5),
                    'rsi_overbought': range(65, 76, 5)
                }
            elif args.strategy == 'bollinger_rsi':
                param_ranges = {
                    'bb_period': range(15, 26, 5),
                    'bb_std': [1.5, 2.0, 2.5],
                    'rsi_length': range(10, 21, 5)
                }
            elif args.strategy == 'mean_reversion':
                param_ranges = {
                    'rsi_length': range(10, 21, 5),
                    'sma_period': range(30, 61, 10),
                    'deviation_threshold': [0.01, 0.02, 0.03]
                }
            
            print(f"\n🔧 Optimizing {args.strategy} on {args.symbol}")
            print(f"Parameter ranges: {param_ranges}")
            
            optimized_stats = run_optimization(strategy_class, data, param_ranges)
            
            print(f"\n🎯 Optimization Results:")
            print(f"Best Parameters: {optimized_stats._strategy}")
            print(f"Best Sharpe Ratio: {optimized_stats['Sharpe Ratio']:.2f}")
            print(f"Best Return: {optimized_stats['Return [%]']:.2f}%")
        
        else:
            # Run single backtest
            strategy_class = strategies[args.strategy]
            result = run_single_backtest(strategy_class, data)
            
            print_results(result)
            
            if args.save:
                save_results(result)
    
    except KeyboardInterrupt:
        print("\n👋 Backtest interrupted by user")
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
