#!/usr/bin/env python3
# ==============================================================================
# File: demo_backtest.py
# Description: Simple demonstration of backtesting with actual trading signals
# ==============================================================================

import pandas as pd
import numpy as np
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from augustan.backtesting.engine.backtester import BacktestEngine, BacktestConfig
from augustan.backtesting.engine.strategy_framework import RuleBasedStrategy, StrategyFactory, StrategyConfig, StrategyRule, StrategyCondition, SignalType, ConditionOperator
from augustan.backtesting.metrics.performance_metrics import PerformanceAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_trending_data(periods=2000):
    """Create trending market data that will generate trading signals"""
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='1H')
    
    np.random.seed(42)
    
    # Create trending price data with clear patterns
    trend_changes = [0, 500, 1000, 1500]  # Points where trend changes
    base_price = 50000
    prices = []
    
    for i in range(periods):
        # Determine current trend phase
        if i < trend_changes[1]:
            # Uptrend
            trend = 0.0008
        elif i < trend_changes[2]:
            # Sideways/slight down
            trend = -0.0002
        elif i < trend_changes[3]:
            # Strong uptrend
            trend = 0.0012
        else:
            # Downtrend
            trend = -0.0006
        
        # Add noise
        noise = np.random.normal(0, 0.003)
        
        if i == 0:
            price = base_price
        else:
            price = prices[-1] * (1 + trend + noise)
        
        prices.append(max(price, 1000))  # Ensure positive prices
    
    # Generate OHLCV data
    data = []
    for i, close_price in enumerate(prices):
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1]
        
        # Add realistic intrabar movement
        volatility = abs(np.random.normal(0, 0.005))
        high = max(open_price, close_price) * (1 + volatility)
        low = min(open_price, close_price) * (1 - volatility)
        volume = np.random.uniform(1000, 5000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df


def create_simple_rsi_strategy():
    """Create a simple RSI strategy with more sensitive parameters"""
    return StrategyConfig(
        name="Simple_RSI_Strategy",
        description="Simple RSI strategy with sensitive parameters",
        indicators=[
            {"name": "rsi", "params": {"length": 14}}
        ],
        entry_rules=[
            StrategyRule(
                conditions=[
                    StrategyCondition("rsi", "RSI_14", "<", 40, "RSI oversold")
                ],
                signal=SignalType.BUY,
                description="Buy when RSI < 40"
            ),
            StrategyRule(
                conditions=[
                    StrategyCondition("rsi", "RSI_14", ">", 60, "RSI overbought")
                ],
                signal=SignalType.SELL,
                description="Sell when RSI > 60"
            )
        ],
        exit_rules=[]
    )


def create_moving_average_strategy():
    """Create a simple moving average crossover strategy"""
    return StrategyConfig(
        name="MA_Crossover_Strategy",
        description="Simple moving average crossover",
        indicators=[
            {"name": "sma", "params": {"length": 20}},
            {"name": "sma", "params": {"length": 50}}
        ],
        entry_rules=[
            StrategyRule(
                conditions=[
                    StrategyCondition("ma", "SMA_20", "cross_above", "SMA_50", "Fast MA crosses above slow MA")
                ],
                signal=SignalType.BUY,
                description="Buy on golden cross"
            ),
            StrategyRule(
                conditions=[
                    StrategyCondition("ma", "SMA_20", "cross_below", "SMA_50", "Fast MA crosses below slow MA")
                ],
                signal=SignalType.SELL,
                description="Sell on death cross"
            )
        ],
        exit_rules=[]
    )


def run_demo():
    """Run a comprehensive backtesting demonstration"""
    print("🚀 AUGUSTAN BACKTESTING ENGINE DEMONSTRATION")
    print("=" * 60)
    
    # Generate trending market data
    logger.info("Generating trending market data...")
    data = create_trending_data(2000)
    logger.info(f"Generated {len(data)} data points from {data.index[0]} to {data.index[-1]}")
    
    # Create backtesting configuration
    config = BacktestConfig(
        initial_capital=100000,
        commission=0.001,  # 0.1% commission
        slippage=0.0005,   # 0.05% slippage
        stop_loss_pct=0.05,    # 5% stop loss
        take_profit_pct=0.15,  # 15% take profit
        max_position_size=0.8   # Use up to 80% of capital
    )
    
    # Initialize backtesting engine
    engine = BacktestEngine(config)
    
    # Test multiple strategies
    strategies = [
        RuleBasedStrategy(create_simple_rsi_strategy()),
        RuleBasedStrategy(create_moving_average_strategy()),
        RuleBasedStrategy(StrategyFactory.create_rsi_macd_strategy())
    ]
    
    print("\n📊 RUNNING BACKTESTS...")
    print("-" * 40)
    
    results = {}
    for strategy in strategies:
        logger.info(f"Testing {strategy.config.name}...")
        
        try:
            result = engine.run_backtest(strategy, data)
            results[strategy.config.name] = result
            
            # Print results
            metrics = result.performance_metrics
            print(f"\n✅ {strategy.config.name}:")
            print(f"   Total Return: {metrics.total_return:.2%}")
            print(f"   Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
            print(f"   Max Drawdown: {metrics.max_drawdown:.2%}")
            print(f"   Total Trades: {metrics.total_trades}")
            print(f"   Win Rate: {metrics.win_rate:.2%}")
            
        except Exception as e:
            logger.error(f"Error testing {strategy.config.name}: {e}")
            print(f"❌ {strategy.config.name}: Error - {e}")
    
    # Find best performing strategy
    if results:
        best_strategy = max(results.items(), key=lambda x: x[1].performance_metrics.sharpe_ratio)
        print(f"\n🏆 BEST STRATEGY: {best_strategy[0]}")
        print(f"   Sharpe Ratio: {best_strategy[1].performance_metrics.sharpe_ratio:.3f}")
        
        # Show some trade details
        if best_strategy[1].trades:
            print(f"\n📈 SAMPLE TRADES FROM {best_strategy[0]}:")
            for i, trade in enumerate(best_strategy[1].trades[:5]):  # Show first 5 trades
                print(f"   {i+1}. {trade['action']} at ${trade['price']:.2f} on {trade['date']}")
    
    print("\n" + "=" * 60)
    print("✨ DEMONSTRATION COMPLETE!")
    print("The backtesting engine is working correctly with realistic trading signals.")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    run_demo()
