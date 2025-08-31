#!/usr/bin/env python3
"""
Augustan Backtesting Script

Run backtests with real crypto data from exchanges.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.data import DataLoader
from services.trading import RSIMACDStrategy, BollingerRSIStrategy, MeanReversionStrategy
from services.backtesting import AugustanBacktester, BacktestConfig

import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_crypto_data(symbol='BTC/USDT', exchange='binance', timeframe='1h', limit=1000):
    """Load crypto data using CCXT"""
    try:
        logger.info("Loading %s from %s (%s, %d bars)", symbol, exchange, timeframe, limit)
        
        loader = DataLoader()
        data = loader.load_data(symbol, source=exchange, timeframe=timeframe, limit=limit)
        
        if data.empty:
            raise ValueError("No data found for %s" % symbol)
        
        logger.info("Loaded %d bars from %s to %s", len(data), data.index[0], data.index[-1])
        return data
        
    except Exception as e:
        logger.error("Error loading data: %s", e)
        raise

def run_single_backtest(strategy_class, data, **params):
    """Run a single backtest"""
    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        margin=1.0,
        trade_on_close=True,
        hedging=False,
        exclusive_orders=True
    )
    
    backtester = AugustanBacktester(config)
    results = backtester.run_backtest(data, strategy_class, **params)
    return results

def run_optimization(strategy_class, data, param_ranges):
    """Run parameter optimization"""
    config = BacktestConfig(
        initial_capital=10000,
        commission=0.001,
        margin=1.0,
        trade_on_close=True,
        hedging=False,
        exclusive_orders=True
    )
    
    backtester = AugustanBacktester(config)
    best_params, best_result = backtester.optimize_strategy(
        data, strategy_class, param_ranges, 
        metric='Return [%]', maximize=True
    )
    return best_params, best_result

def compare_strategies(data, strategies):
    """Compare multiple strategies"""
    results = {}
    
    for name, strategy_class in strategies.items():
        logger.info("Running backtest for %s", name)
        result = run_single_backtest(strategy_class, data)
        results[name] = result
    
    # Print comparison
    print("\n" + "="*80)
    print("STRATEGY COMPARISON")
    print("="*80)
    
    comparison_data = []
    for name, result in results.items():
        comparison_data.append({
            'Strategy': name,
            'Return [%]': f"{result['Return [%]']:.2f}%",
            'Sharpe Ratio': f"{result['Sharpe Ratio']:.2f}",
            'Max Drawdown [%]': f"{result['Max. Drawdown [%]']:.2f}%",
            'Win Rate [%]': f"{result['Win Rate [%]']:.1f}%",
            'Total Trades': result['# Trades']
        })
    
    # Sort by return
    comparison_data.sort(key=lambda x: float(x['Return [%]'].rstrip('%')), reverse=True)
    
    # Print table
    headers = ['Strategy', 'Return [%]', 'Sharpe Ratio', 'Max Drawdown [%]', 'Win Rate [%]', 'Total Trades']
    
    # Calculate column widths
    col_widths = [max(len(str(row.get(header, ''))) for row in comparison_data + [dict(zip(headers, headers))]) for header in headers]
    
    # Print header
    header_row = " | ".join(header.ljust(width) for header, width in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))
    
    # Print data rows
    for row in comparison_data:
        data_row = " | ".join(str(row.get(header, '')).ljust(width) for header, width in zip(headers, col_widths))
        print(data_row)
    
    return results

def main():
    parser = argparse.ArgumentParser(
        description="Augustan Backtesting Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m augustan.scripts.run_backtest --strategy rsi_macd
  python -m augustan.scripts.run_backtest --strategy bollinger_rsi --symbol ETH/USDT
  python -m augustan.scripts.run_backtest --optimize --strategy rsi_macd
  python -m augustan.scripts.run_backtest --compare-all --symbol BTC/USDT
        """
    )
    
    parser.add_argument('--strategy', choices=['rsi_macd', 'bollinger_rsi', 'mean_reversion'],
                       default='rsi_macd', help='Strategy to backtest')
    parser.add_argument('--symbol', default='BTC/USDT', help='Crypto symbol to backtest')
    parser.add_argument('--exchange', default='binance', choices=['binance', 'okx', 'bybit', 'kucoin'],
                       help='Exchange to fetch data from')
    parser.add_argument('--timeframe', default='1h', choices=['1m', '5m', '15m', '1h', '4h', '1d'],
                       help='Timeframe for data')
    parser.add_argument('--limit', type=int, default=1000, help='Number of bars to fetch')
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--compare-all', action='store_true', help='Compare all strategies')
    parser.add_argument('--save', action='store_true', help='Save results to files')
    
    args = parser.parse_args()
    
    try:
        # Load data
        data = load_crypto_data(args.symbol, args.exchange, args.timeframe, args.limit)
        
        # Strategy mapping
        strategies = {
            'rsi_macd': RSIMACDStrategy,
            'bollinger_rsi': BollingerRSIStrategy,
            'mean_reversion': MeanReversionStrategy
        }
        
        if args.compare_all:
            # Compare all strategies
            results = compare_strategies(data, strategies)
            
            if args.save:
                import json
                with open('strategy_comparison.json', 'w') as f:
                    json.dump({k: dict(v) for k, v in results.items()}, f, indent=2)
                logger.info("Results saved to strategy_comparison.json")
        
        elif args.optimize:
            # Run optimization
            strategy_class = strategies[args.strategy]
            
            # Define parameter ranges based on strategy
            if args.strategy == 'rsi_macd':
                param_ranges = {
                    'rsi_period': range(10, 21, 2),
                    'rsi_oversold': range(25, 36, 5),
                    'rsi_overbought': range(65, 76, 5)
                }
            elif args.strategy == 'bollinger_rsi':
                param_ranges = {
                    'bb_period': range(15, 26, 5),
                    'bb_std': [1.5, 2.0, 2.5],
                    'rsi_period': range(10, 21, 5)
                }
            else:  # mean_reversion
                param_ranges = {
                    'rsi_period': range(10, 21, 5),
                    'sma_period': range(15, 31, 5),
                    'deviation_threshold': [1.5, 2.0, 2.5]
                }
            
            logger.info("Running optimization for %s strategy", args.strategy)
            best_params, best_result = run_optimization(strategy_class, data, param_ranges)
            
            print("\n" + "="*60)
            print("OPTIMIZATION RESULTS")
            print("="*60)
            print(f"Best Parameters: {best_params}")
            print(f"Best Return: {best_result['Return [%]']:.2f}%")
            print(f"Sharpe Ratio: {best_result['Sharpe Ratio']:.2f}")
            print(f"Max Drawdown: {best_result['Max. Drawdown [%]']:.2f}%")
            
            if args.save:
                import json
                with open(f'{args.strategy}_optimization.json', 'w') as f:
                    json.dump({
                        'best_params': best_params,
                        'best_result': dict(best_result)
                    }, f, indent=2)
                logger.info("Optimization results saved")
        
        else:
            # Run single backtest
            strategy_class = strategies[args.strategy]
            logger.info("Running backtest for %s strategy on %s", args.strategy, args.symbol)
            
            result = run_single_backtest(strategy_class, data)
            
            print("\n" + "="*60)
            print(f"BACKTEST RESULTS - {args.strategy.upper()} on {args.symbol}")
            print("="*60)
            print(f"Return [%]: {result['Return [%]']:.2f}%")
            print(f"Buy & Hold Return [%]: {result['Buy & Hold Return [%]']:.2f}%")
            print(f"Sharpe Ratio: {result['Sharpe Ratio']:.2f}")
            print(f"Sortino Ratio: {result['Sortino Ratio']:.2f}")
            print(f"Calmar Ratio: {result['Calmar Ratio']:.2f}")
            print(f"Max Drawdown [%]: {result['Max. Drawdown [%]']:.2f}%")
            print(f"Win Rate [%]: {result['Win Rate [%]']:.1f}%")
            print(f"Total Trades: {result['# Trades']}")
            print(f"Avg Trade [%]: {result['Avg. Trade [%]']:.2f}%")
            print(f"Profit Factor: {result['Profit Factor']:.2f}")
            
            if args.save:
                import json
                with open(f'{args.strategy}_{args.symbol.replace("/", "_")}_backtest.json', 'w') as f:
                    json.dump(dict(result), f, indent=2)
                logger.info("Results saved")
    
    except Exception as e:
        logger.error("Backtest failed: %s", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
