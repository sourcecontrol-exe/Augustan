# ==============================================================================
# File: run_backtest.py
# Description: Example script to run comprehensive backtesting and optimization
# ==============================================================================

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtester import BacktestEngine, BacktestConfig, StrategyOptimizer
from backtesting.strategy_framework import RuleBasedStrategy, StrategyFactory
from backtesting.performance_metrics import StrategyComparison
from backtesting.indicators import TechnicalIndicators

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_sample_data():
    """Load sample data for backtesting"""
    # Try to load existing data
    data_path = Path(__file__).parent.parent / "data" / "btc_usdt_3m.csv"
    
    if data_path.exists() and data_path.stat().st_size > 0:
        logger.info(f"Loading data from {data_path}")
        try:
            df = pd.read_csv(data_path)
            
            # Ensure proper column names and datetime index
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'])
                df.set_index('datetime', inplace=True)
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            # Standardize column names
            column_mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            }
            df.rename(columns=column_mapping, inplace=True)
            
            if not df.empty:
                return df
        except Exception as e:
            logger.warning(f"Error loading data file: {e}")
    
    logger.info("Using generated sample data for demonstration.")
    return generate_sample_data()


def generate_sample_data(periods=5000):
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start='2020-01-01', periods=periods, freq='3min')
    
    # Generate realistic price data using random walk
    np.random.seed(42)
    returns = np.random.normal(0, 0.002, periods)  # 0.2% volatility per period
    
    # Starting price
    initial_price = 40000
    prices = [initial_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 1))  # Ensure positive prices
    
    # Generate OHLC from close prices
    data = []
    for i, price in enumerate(prices):
        if i == 0:
            open_price = price
        else:
            open_price = prices[i-1]
        
        # Add some intrabar volatility
        high_mult = 1 + abs(np.random.normal(0, 0.001))
        low_mult = 1 - abs(np.random.normal(0, 0.001))
        
        high = max(open_price, price) * high_mult
        low = min(open_price, price) * low_mult
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df


def run_single_strategy_backtest():
    """Run backtest for a single strategy"""
    logger.info("=== Running Single Strategy Backtest ===")
    
    # Load data
    data = load_sample_data()
    logger.info(f"Loaded {len(data)} data points from {data.index[0]} to {data.index[-1]}")
    
    # Create backtest configuration
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001,
        slippage=0.0005,
        start_date='2022-01-01',
        end_date='2023-12-31'
    )
    
    # Initialize backtesting engine
    engine = BacktestEngine(config)
    
    # Create strategy
    strategy_config = StrategyFactory.create_rsi_macd_strategy()
    strategy = RuleBasedStrategy(strategy_config)
    
    # Run backtest
    result = engine.run_backtest(strategy, data)
    
    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Strategy: {result.strategy_name}")
    print(f"Total Return: {result.performance_metrics.total_return:.2%}")
    print(f"Annualized Return: {result.performance_metrics.annualized_return:.2%}")
    print(f"Sharpe Ratio: {result.performance_metrics.sharpe_ratio:.3f}")
    print(f"Maximum Drawdown: {result.performance_metrics.max_drawdown:.2%}")
    print(f"Win Rate: {result.performance_metrics.win_rate:.2%}")
    print(f"Total Trades: {result.performance_metrics.total_trades}")
    print("="*60)
    
    # Save results
    engine.save_results(result, "single_strategy_results")
    logger.info("Results saved to single_strategy_results/")
    
    return result


def run_multiple_strategies_comparison():
    """Compare multiple strategies"""
    logger.info("=== Running Multiple Strategies Comparison ===")
    
    # Load data
    data = load_sample_data()
    
    # Create backtest configuration
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001,
        start_date='2022-01-01',
        end_date='2023-12-31'
    )
    
    # Initialize backtesting engine
    engine = BacktestEngine(config)
    
    # Create multiple strategies
    strategies = [
        RuleBasedStrategy(StrategyFactory.create_rsi_macd_strategy()),
        RuleBasedStrategy(StrategyFactory.create_bollinger_rsi_strategy()),
        RuleBasedStrategy(StrategyFactory.create_multi_timeframe_strategy())
    ]
    
    # Run backtests
    results = engine.run_multiple_strategies(strategies, data)
    
    # Create comparison
    comparison = StrategyComparison()
    for name, result in results.items():
        comparison.add_strategy(name, data, result.signals)
    
    # Print comparison table
    comparison_df = comparison.compare_strategies()
    print("\n" + "="*80)
    print("STRATEGY COMPARISON")
    print("="*80)
    print(comparison_df.to_string())
    print("="*80)
    
    # Rank strategies
    rankings = comparison.rank_strategies('sharpe_ratio')
    print("\nSTRATEGY RANKINGS (by Sharpe Ratio):")
    for i, (name, score) in enumerate(rankings, 1):
        print(f"{i}. {name}: {score:.3f}")
    
    # Save results
    engine.save_results(results, "multi_strategy_results")
    logger.info("Results saved to multi_strategy_results/")
    
    return results, comparison


def run_parameter_optimization():
    """Run parameter optimization for a strategy"""
    logger.info("=== Running Parameter Optimization ===")
    
    # Load data
    data = load_sample_data()
    
    # Create backtest configuration
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001,
        start_date='2022-01-01',
        end_date='2023-06-30'  # Use first half for optimization
    )
    
    # Initialize backtesting engine
    engine = BacktestEngine(config)
    
    # Create base strategy for optimization
    base_strategy_config = StrategyFactory.create_rsi_macd_strategy()
    
    # Initialize optimizer
    optimizer = StrategyOptimizer(base_strategy_config, engine)
    
    # Define parameter grid for optimization
    parameter_grid = {
        'length': [10, 14, 20],  # RSI length
        'fast': [8, 12, 16],     # MACD fast period
        'slow': [21, 26, 30]     # MACD slow period
    }
    
    # Run optimization
    logger.info("Starting parameter optimization...")
    optimization_results = optimizer.grid_search_optimization(
        data, parameter_grid, 'sharpe_ratio'
    )
    
    # Print optimization results
    print("\n" + "="*60)
    print("PARAMETER OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Best Parameters: {optimization_results['best_parameters']}")
    print(f"Best {optimization_results['optimization_metric']}: {optimization_results['best_score']:.3f}")
    print(f"Total Combinations Tested: {optimization_results['total_tested']}")
    
    print("\nTop 5 Parameter Combinations:")
    for i, result in enumerate(optimization_results['all_results'][:5], 1):
        print(f"{i}. Params: {result['parameters']}")
        print(f"   Sharpe: {result['sharpe_ratio']:.3f}, Return: {result['total_return']:.2%}")
    print("="*60)
    
    return optimization_results


def run_walk_forward_analysis():
    """Run walk-forward analysis"""
    logger.info("=== Running Walk-Forward Analysis ===")
    
    # Load data
    data = load_sample_data()
    
    # Split data into periods
    total_periods = len(data)
    train_size = total_periods // 3  # Use 1/3 for training
    test_size = total_periods // 6   # Use 1/6 for testing
    
    results = []
    
    for i in range(0, total_periods - train_size - test_size, test_size):
        train_start = i
        train_end = i + train_size
        test_start = train_end
        test_end = min(test_start + test_size, total_periods)
        
        if test_end <= test_start:
            break
        
        logger.info(f"Period {len(results)+1}: Train {train_start}-{train_end}, Test {test_start}-{test_end}")
        
        train_data = data.iloc[train_start:train_end]
        test_data = data.iloc[test_start:test_end]
        
        # Optimize on training data
        config = BacktestConfig(initial_capital=100000, commission=0.001)
        engine = BacktestEngine(config)
        
        base_strategy_config = StrategyFactory.create_rsi_macd_strategy()
        optimizer = StrategyOptimizer(base_strategy_config, engine)
        
        # Smaller parameter grid for speed
        parameter_grid = {
            'length': [10, 14, 20],
            'fast': [12, 16],
            'slow': [26, 30]
        }
        
        # Optimize
        opt_results = optimizer.grid_search_optimization(train_data, parameter_grid)
        
        # Test on out-of-sample data
        best_params = opt_results['best_parameters']
        optimized_config = optimizer._apply_parameters(best_params)
        optimized_strategy = RuleBasedStrategy(optimized_config)
        
        test_result = engine.run_backtest(optimized_strategy, test_data)
        
        results.append({
            'period': len(results) + 1,
            'train_periods': len(train_data),
            'test_periods': len(test_data),
            'best_params': best_params,
            'train_sharpe': opt_results['best_score'],
            'test_return': test_result.performance_metrics.total_return,
            'test_sharpe': test_result.performance_metrics.sharpe_ratio,
            'test_drawdown': test_result.performance_metrics.max_drawdown
        })
    
    # Print walk-forward results
    print("\n" + "="*80)
    print("WALK-FORWARD ANALYSIS RESULTS")
    print("="*80)
    
    wf_df = pd.DataFrame(results)
    print(wf_df.to_string(index=False))
    
    print(f"\nAverage Out-of-Sample Return: {wf_df['test_return'].mean():.2%}")
    print(f"Average Out-of-Sample Sharpe: {wf_df['test_sharpe'].mean():.3f}")
    print(f"Average Max Drawdown: {wf_df['test_drawdown'].mean():.2%}")
    print("="*80)
    
    return results


def main():
    """Main function to run all backtesting examples"""
    print("AUGUSTAN BACKTESTING ENGINE")
    print("="*50)
    
    try:
        # Run single strategy backtest
        single_result = run_single_strategy_backtest()
        
        # Run multiple strategies comparison
        multi_results, comparison = run_multiple_strategies_comparison()
        
        # Run parameter optimization
        opt_results = run_parameter_optimization()
        
        # Run walk-forward analysis
        wf_results = run_walk_forward_analysis()
        
        print("\n" + "="*50)
        print("ALL BACKTESTING COMPLETED SUCCESSFULLY!")
        print("Check the output directories for detailed results.")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error during backtesting: {e}")
        raise


if __name__ == "__main__":
    main()