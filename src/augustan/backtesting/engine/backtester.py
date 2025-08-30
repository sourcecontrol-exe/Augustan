# ==============================================================================
# File: backtester.py
# Description: Main backtesting engine for strategy evaluation and optimization
# ==============================================================================

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
import concurrent.futures
from pathlib import Path
import json

from .strategy_framework import (
    BaseStrategy, RuleBasedStrategy, MLStrategy, StrategyConfig, 
    StrategyFactory, SignalType
)
from ..metrics.performance_metrics import PerformanceAnalyzer, PerformanceMetrics, StrategyComparison
from ..indicators.indicators import TechnicalIndicators
from ...core.risk_management.risk_manager import RiskManager
from ...utils.exceptions import ValidationError, DataFetchError


@dataclass
class BacktestConfig:
    """Configuration for backtesting parameters"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000
    commission: float = 0.001
    slippage: float = 0.0005
    risk_free_rate: float = 0.02
    benchmark_symbol: Optional[str] = None
    
    # Risk management
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 0.02     # 2% stop loss
    take_profit_pct: float = 0.06   # 6% take profit
    
    # Execution settings
    execution_delay: int = 1        # Bars delay for execution
    allow_short_selling: bool = True
    margin_requirement: float = 0.5


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    strategy_name: str
    config: BacktestConfig
    performance_metrics: PerformanceMetrics
    equity_curve: pd.Series
    signals: pd.Series
    trades: List[Dict[str, Any]]
    positions: pd.Series
    drawdown_series: pd.Series
    
    # Additional analysis
    monthly_returns: pd.Series
    yearly_returns: pd.Series
    rolling_sharpe: pd.Series
    
    # Execution details
    execution_log: List[Dict[str, Any]]
    risk_events: List[Dict[str, Any]]


class BacktestEngine:
    """
    Comprehensive backtesting engine for strategy evaluation
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.performance_analyzer = PerformanceAnalyzer(
            risk_free_rate=self.config.risk_free_rate
        )
        self.risk_manager = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize risk manager if available
        try:
            self.risk_manager = RiskManager()
        except ImportError:
            self.logger.warning("Risk manager not available")
        except Exception as e:
            self.logger.warning(f"Risk manager initialization failed: {e}")
            self.risk_manager = None
    
    def run_backtest(self, strategy: BaseStrategy, data: pd.DataFrame) -> BacktestResult:
        """
        Run a complete backtest for a strategy
        
        Args:
            strategy: Strategy instance to test
            data: OHLCV market data
            
        Returns:
            BacktestResult with comprehensive analysis
        """
        # Validate inputs
        self._validate_inputs(strategy, data)
        
        # Filter data by date range if specified
        filtered_data = self._filter_data_by_date(data)
        
        # Generate signals
        self.logger.info(f"Generating signals for {strategy.config.name}")
        signals = strategy.generate_signals(filtered_data)
        
        # Execute trades with realistic simulation
        execution_result = self._execute_trades(filtered_data, signals)
        
        # Calculate performance metrics
        performance_metrics = self.performance_analyzer.analyze_performance(
            filtered_data, signals, self.config.initial_capital, self.config.commission
        )
        
        # Generate additional analysis
        additional_analysis = self._generate_additional_analysis(
            filtered_data, execution_result['equity_curve'], execution_result['returns']
        )
        
        # Create result object
        result = BacktestResult(
            strategy_name=strategy.config.name,
            config=self.config,
            performance_metrics=performance_metrics,
            equity_curve=execution_result['equity_curve'],
            signals=signals,
            trades=execution_result['trades'],
            positions=execution_result['positions'],
            drawdown_series=additional_analysis['drawdown_series'],
            monthly_returns=additional_analysis['monthly_returns'],
            yearly_returns=additional_analysis['yearly_returns'],
            rolling_sharpe=additional_analysis['rolling_sharpe'],
            execution_log=execution_result['execution_log'],
            risk_events=execution_result['risk_events']
        )
        
        self.logger.info(f"Backtest completed for {strategy.config.name}")
        return result
    
    def _validate_inputs(self, strategy: BaseStrategy, data: pd.DataFrame):
        """Validate backtest inputs"""
        if data.empty:
            raise ValidationError("Data cannot be empty")
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")
        
        if not isinstance(strategy, BaseStrategy):
            raise ValidationError("Strategy must inherit from BaseStrategy")
    
    def _filter_data_by_date(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter data by specified date range"""
        filtered_data = data.copy()
        
        if self.config.start_date:
            start_date = pd.to_datetime(self.config.start_date)
            filtered_data = filtered_data[filtered_data.index >= start_date]
        
        if self.config.end_date:
            end_date = pd.to_datetime(self.config.end_date)
            filtered_data = filtered_data[filtered_data.index <= end_date]
        
        return filtered_data
    
    def _execute_trades(self, data: pd.DataFrame, signals: pd.Series) -> Dict[str, Any]:
        """
        Execute trades with realistic simulation including slippage, commission, and risk management
        """
        # Initialize tracking variables
        portfolio_value = self.config.initial_capital
        position = 0  # Current position (-1, 0, 1)
        position_size = 0  # Actual position size in dollars
        cash = self.config.initial_capital
        
        # Results tracking
        equity_curve = []
        returns = []
        trades = []
        positions = []
        execution_log = []
        risk_events = []
        
        # Entry tracking for risk management
        entry_price = None
        entry_date = None
        
        for i, (date, signal) in enumerate(signals.items()):
            if i >= len(data):
                break
                
            current_price = data.iloc[i]['close']
            
            # Calculate current portfolio value
            if position != 0:
                position_value = position_size * (current_price / entry_price) if entry_price else 0
                portfolio_value = cash + position_value
            else:
                portfolio_value = cash
            
            # Risk management checks
            risk_action = self._check_risk_management(
                current_price, entry_price, position, date
            )
            
            if risk_action:
                signal = risk_action['action']
                risk_events.append(risk_action)
            
            # Execute signal with delay
            if i >= self.config.execution_delay:
                delayed_signal = signals.iloc[i - self.config.execution_delay]
                execution_price = self._calculate_execution_price(
                    data.iloc[i], delayed_signal
                )
                
                # Process trade
                trade_result = self._process_trade(
                    delayed_signal, execution_price, position, position_size,
                    cash, portfolio_value, date, i
                )
                
                if trade_result:
                    position = trade_result['new_position']
                    position_size = trade_result['new_position_size']
                    cash = trade_result['new_cash']
                    
                    if trade_result['trade_executed']:
                        trades.append(trade_result['trade_details'])
                        execution_log.append(trade_result['execution_details'])
                        
                        # Update entry tracking
                        if position != 0:
                            entry_price = execution_price
                            entry_date = date
                        else:
                            entry_price = None
                            entry_date = None
            
            # Record state
            equity_curve.append(portfolio_value)
            if i > 0:
                returns.append((portfolio_value - equity_curve[i-1]) / equity_curve[i-1])
            else:
                returns.append(0)
            positions.append(position)
        
        return {
            'equity_curve': pd.Series(equity_curve, index=data.index[:len(equity_curve)]),
            'returns': pd.Series(returns, index=data.index[:len(returns)]),
            'trades': trades,
            'positions': pd.Series(positions, index=data.index[:len(positions)]),
            'execution_log': execution_log,
            'risk_events': risk_events
        }
    
    def _check_risk_management(self, current_price: float, entry_price: Optional[float],
                             position: int, date: pd.Timestamp) -> Optional[Dict[str, Any]]:
        """Check risk management rules"""
        if position == 0 or entry_price is None:
            return None
        
        # Calculate current P&L percentage
        if position > 0:  # Long position
            pnl_pct = (current_price - entry_price) / entry_price
        else:  # Short position
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Check stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            return {
                'action': 'SELL' if position > 0 else 'BUY',
                'reason': 'stop_loss',
                'pnl_pct': pnl_pct,
                'date': date,
                'price': current_price
            }
        
        # Check take profit
        if pnl_pct >= self.config.take_profit_pct:
            return {
                'action': 'SELL' if position > 0 else 'BUY',
                'reason': 'take_profit',
                'pnl_pct': pnl_pct,
                'date': date,
                'price': current_price
            }
        
        return None
    
    def _calculate_execution_price(self, bar_data: pd.Series, signal: str) -> float:
        """Calculate realistic execution price with slippage"""
        base_price = bar_data['close']
        
        if signal == 'BUY':
            # Add slippage for buying (higher price)
            slippage_amount = base_price * self.config.slippage
            execution_price = min(base_price + slippage_amount, bar_data['high'])
        elif signal == 'SELL':
            # Subtract slippage for selling (lower price)
            slippage_amount = base_price * self.config.slippage
            execution_price = max(base_price - slippage_amount, bar_data['low'])
        else:
            execution_price = base_price
        
        return execution_price
    
    def _process_trade(self, signal: str, execution_price: float, current_position: int,
                      current_position_size: float, cash: float, portfolio_value: float,
                      date: pd.Timestamp, index: int) -> Optional[Dict[str, Any]]:
        """Process a trade signal and update portfolio state"""
        
        if signal == 'HOLD':
            return None
        
        # Calculate position size based on risk management
        max_position_value = portfolio_value * self.config.max_position_size
        
        trade_executed = False
        trade_details = None
        execution_details = None
        
        new_position = current_position
        new_position_size = current_position_size
        new_cash = cash
        
        if signal == 'BUY' and current_position <= 0:
            # Close short position if any, then go long
            if current_position < 0:
                # Close short position
                close_value = abs(current_position_size)
                commission = close_value * self.config.commission
                new_cash += close_value - commission
                new_position_size = 0
            
            # Open long position
            available_cash = new_cash
            position_value = min(max_position_value, available_cash * 0.95)  # Leave some cash buffer
            shares = position_value / execution_price
            commission = position_value * self.config.commission
            
            if available_cash >= position_value + commission:
                new_position = 1
                new_position_size = position_value
                new_cash -= position_value + commission
                trade_executed = True
                
                trade_details = {
                    'date': date,
                    'action': 'BUY',
                    'price': execution_price,
                    'quantity': shares,
                    'value': position_value,
                    'commission': commission,
                    'cash_after': new_cash
                }
        
        elif signal == 'SELL' and current_position >= 0:
            # Close long position if any, then go short (if allowed)
            if current_position > 0:
                # Close long position
                close_value = current_position_size * (execution_price / (current_position_size / current_position_size))  # Simplified
                commission = close_value * self.config.commission
                new_cash += close_value - commission
                new_position_size = 0
                trade_executed = True
                
                trade_details = {
                    'date': date,
                    'action': 'SELL',
                    'price': execution_price,
                    'value': close_value,
                    'commission': commission,
                    'cash_after': new_cash
                }
            
            # Open short position if allowed
            if self.config.allow_short_selling:
                position_value = min(max_position_value, new_cash * self.config.margin_requirement)
                commission = position_value * self.config.commission
                
                if new_cash >= commission:
                    new_position = -1
                    new_position_size = position_value
                    new_cash -= commission
                    trade_executed = True
        
        execution_details = {
            'date': date,
            'index': index,
            'signal': signal,
            'execution_price': execution_price,
            'portfolio_value_before': portfolio_value,
            'position_before': current_position,
            'position_after': new_position,
            'cash_before': cash,
            'cash_after': new_cash
        }
        
        return {
            'new_position': new_position,
            'new_position_size': new_position_size,
            'new_cash': new_cash,
            'trade_executed': trade_executed,
            'trade_details': trade_details,
            'execution_details': execution_details
        }
    
    def _generate_additional_analysis(self, data: pd.DataFrame, equity_curve: pd.Series,
                                    returns: pd.Series) -> Dict[str, Any]:
        """Generate additional analysis metrics"""
        
        # Drawdown analysis
        running_max = equity_curve.expanding().max()
        drawdown_series = (equity_curve - running_max) / running_max
        
        # Period returns
        try:
            monthly_returns = returns.groupby(pd.Grouper(freq='M')).apply(
                lambda x: (1 + x).prod() - 1
            )
            yearly_returns = returns.groupby(pd.Grouper(freq='Y')).apply(
                lambda x: (1 + x).prod() - 1
            )
        except:
            monthly_returns = pd.Series(dtype=float)
            yearly_returns = pd.Series(dtype=float)
        
        # Rolling Sharpe ratio (252-day window)
        rolling_sharpe = pd.Series(index=returns.index, dtype=float)
        window = min(252, len(returns) // 4)  # Use smaller window if insufficient data
        
        if window > 30:  # Only calculate if we have enough data
            for i in range(window, len(returns)):
                window_returns = returns.iloc[i-window:i]
                if window_returns.std() > 0:
                    rolling_sharpe.iloc[i] = (
                        window_returns.mean() / window_returns.std() * np.sqrt(252)
                    )
        
        return {
            'drawdown_series': drawdown_series,
            'monthly_returns': monthly_returns,
            'yearly_returns': yearly_returns,
            'rolling_sharpe': rolling_sharpe
        }
    
    def run_multiple_strategies(self, strategies: List[BaseStrategy], 
                              data: pd.DataFrame) -> Dict[str, BacktestResult]:
        """Run backtests for multiple strategies"""
        results = {}
        
        for strategy in strategies:
            self.logger.info(f"Running backtest for {strategy.config.name}")
            try:
                result = self.run_backtest(strategy, data)
                results[strategy.config.name] = result
            except Exception as e:
                self.logger.error(f"Error running backtest for {strategy.config.name}: {e}")
        
        return results
    
    def run_parallel_backtests(self, strategies: List[BaseStrategy], 
                             data: pd.DataFrame, max_workers: int = 4) -> Dict[str, BacktestResult]:
        """Run backtests in parallel for better performance"""
        results = {}
        
        def run_single_backtest(strategy):
            try:
                return strategy.config.name, self.run_backtest(strategy, data)
            except Exception as e:
                self.logger.error(f"Error in parallel backtest for {strategy.config.name}: {e}")
                return strategy.config.name, None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_strategy = {
                executor.submit(run_single_backtest, strategy): strategy 
                for strategy in strategies
            }
            
            for future in concurrent.futures.as_completed(future_to_strategy):
                name, result = future.result()
                if result:
                    results[name] = result
        
        return results
    
    def save_results(self, results: Union[BacktestResult, Dict[str, BacktestResult]], 
                    output_dir: str = "backtest_results"):
        """Save backtest results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        if isinstance(results, BacktestResult):
            results = {results.strategy_name: results}
        
        for name, result in results.items():
            strategy_dir = output_path / name
            strategy_dir.mkdir(exist_ok=True)
            
            # Save performance metrics
            metrics_dict = {
                'total_return': result.performance_metrics.total_return,
                'annualized_return': result.performance_metrics.annualized_return,
                'volatility': result.performance_metrics.volatility,
                'sharpe_ratio': result.performance_metrics.sharpe_ratio,
                'max_drawdown': result.performance_metrics.max_drawdown,
                'win_rate': result.performance_metrics.win_rate,
                'total_trades': result.performance_metrics.total_trades
            }
            
            with open(strategy_dir / 'metrics.json', 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            
            # Save equity curve
            result.equity_curve.to_csv(strategy_dir / 'equity_curve.csv')
            
            # Save signals
            result.signals.to_csv(strategy_dir / 'signals.csv')
            
            # Save trades
            if result.trades:
                trades_df = pd.DataFrame(result.trades)
                trades_df.to_csv(strategy_dir / 'trades.csv', index=False)
        
        self.logger.info(f"Results saved to {output_path}")


class StrategyOptimizer:
    """Optimize strategy parameters using various methods"""
    
    def __init__(self, base_strategy_config: StrategyConfig, 
                 backtest_engine: BacktestEngine):
        self.base_config = base_strategy_config
        self.engine = backtest_engine
        self.optimization_results = []
        self.logger = logging.getLogger(__name__)
    
    def grid_search_optimization(self, data: pd.DataFrame, 
                               parameter_grid: Dict[str, List[Any]],
                               optimization_metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """
        Perform grid search optimization on strategy parameters
        
        Args:
            data: Market data for backtesting
            parameter_grid: Dictionary of parameters and their possible values
            optimization_metric: Metric to optimize for
            
        Returns:
            Dictionary with best parameters and results
        """
        from itertools import product
        
        best_params = None
        best_score = float('-inf')
        all_results = []
        
        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        
        total_combinations = np.prod([len(values) for values in param_values])
        self.logger.info(f"Testing {total_combinations} parameter combinations")
        
        for i, combination in enumerate(product(*param_values)):
            params = dict(zip(param_names, combination))
            
            try:
                # Create modified strategy with new parameters
                modified_config = self._apply_parameters(params)
                strategy = RuleBasedStrategy(modified_config)
                
                # Run backtest
                result = self.engine.run_backtest(strategy, data)
                
                # Get optimization score
                score = getattr(result.performance_metrics, optimization_metric, 0)
                
                result_entry = {
                    'parameters': params,
                    'score': score,
                    'total_return': result.performance_metrics.total_return,
                    'sharpe_ratio': result.performance_metrics.sharpe_ratio,
                    'max_drawdown': result.performance_metrics.max_drawdown,
                    'win_rate': result.performance_metrics.win_rate
                }
                
                all_results.append(result_entry)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Completed {i + 1}/{total_combinations} combinations")
                    
            except Exception as e:
                self.logger.error(f"Error testing parameters {params}: {e}")
        
        # Sort results by score
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'best_parameters': best_params,
            'best_score': best_score,
            'optimization_metric': optimization_metric,
            'all_results': all_results[:50],  # Top 50 results
            'total_tested': len(all_results)
        }
    
    def _apply_parameters(self, params: Dict[str, Any]) -> StrategyConfig:
        """Apply parameter modifications to create new strategy config"""
        # Create a copy of the base config
        new_config = StrategyConfig(
            name=f"{self.base_config.name}_optimized",
            description=f"{self.base_config.description} (optimized)",
            indicators=self.base_config.indicators.copy(),
            entry_rules=self.base_config.entry_rules.copy(),
            exit_rules=self.base_config.exit_rules.copy(),
            risk_management=self.base_config.risk_management.copy(),
            parameters=params
        )
        
        # Apply parameter modifications to indicators
        for param_name, param_value in params.items():
            # Update indicator parameters
            for indicator in new_config.indicators:
                if param_name in indicator.get('params', {}):
                    indicator['params'][param_name] = param_value
        
        return new_config