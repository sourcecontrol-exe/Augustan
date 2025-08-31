# ==============================================================================
# File: backtester.py
# Description: Main backtesting engine using backtesting.py library
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
import yfinance as yf
from backtesting import Backtest
from backtesting.lib import crossover
import warnings
warnings.filterwarnings('ignore')

# Import our strategy classes
from strategy import BacktestableStrategy, RSIMACDStrategy, BollingerRSIStrategy, MeanReversionStrategy
from data_service import DataService
from risk_manager import RiskManager
from exceptions import ValidationError, DataFetchError


@dataclass
class BacktestConfig:
    """Configuration for backtesting parameters"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000
    commission: float = 0.001
    margin: float = 1.0
    trade_on_close: bool = False
    hedging: bool = False
    exclusive_orders: bool = False


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    strategy_name: str
    config: BacktestConfig
    stats: Dict[str, Any]
    equity_curve: pd.Series
    trades: pd.DataFrame
    
    # Additional analysis
    monthly_returns: pd.Series
    yearly_returns: pd.Series
    rolling_metrics: Dict[str, pd.Series]


class AugustanBacktester:
    """
    Augustan backtesting engine using backtesting.py library
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.logger = logging.getLogger(__name__)
        self.data_service = None
        
        # Initialize data service if available
        try:
            self.data_service = DataService('ccxt', {
                'exchange_id': 'binance',
                'testnet': True
            })
        except Exception as e:
            self.logger.warning(f"Data service initialization failed: {e}")
    
    def run_backtest(self, strategy_class, data: pd.DataFrame, **strategy_params) -> BacktestResult:
        """
        Run a complete backtest for a strategy using backtesting.py library
        
        Args:
            strategy_class: Strategy class that inherits from BacktestableStrategy
            data: OHLCV market data with columns [Open, High, Low, Close, Volume]
            **strategy_params: Parameters to pass to the strategy
            
        Returns:
            BacktestResult with comprehensive analysis
        """
        # Validate inputs
        self._validate_inputs(data)
        
        # Filter data by date range if specified
        filtered_data = self._filter_data_by_date(data)
        
        # Ensure proper column names (backtesting.py expects capitalized names)
        filtered_data = self._prepare_data(filtered_data)
        
        self.logger.info(f"Running backtest for {strategy_class.__name__}")
        
        # Create backtest instance
        bt = Backtest(
            filtered_data,
            strategy_class,
            cash=self.config.initial_capital,
            commission=self.config.commission,
            margin=self.config.margin,
            trade_on_close=self.config.trade_on_close,
            hedging=self.config.hedging,
            exclusive_orders=self.config.exclusive_orders
        )
        
        # Run backtest with strategy parameters
        stats = bt.run(**strategy_params)
        
        # Generate additional analysis
        additional_analysis = self._generate_additional_analysis(stats)
        
        # Create result object
        result = BacktestResult(
            strategy_name=strategy_class.__name__,
            config=self.config,
            stats=stats,
            equity_curve=stats['_equity_curve']['Equity'],
            trades=stats['_trades'],
            monthly_returns=additional_analysis['monthly_returns'],
            yearly_returns=additional_analysis['yearly_returns'],
            rolling_metrics=additional_analysis['rolling_metrics']
        )
        
        self.logger.info(f"Backtest completed for {strategy_class.__name__}")
        return result
    
    def _validate_inputs(self, data: pd.DataFrame):
        """Validate backtest inputs"""
        if data.empty:
            raise ValidationError("Data cannot be empty")
        
        # Check for required columns (case insensitive)
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        data_columns_lower = [col.lower() for col in data.columns]
        missing_columns = [col for col in required_columns if col not in data_columns_lower]
        if missing_columns:
            raise ValidationError(f"Missing required columns: {missing_columns}")
        
        # Check for sufficient data
        if len(data) < 50:
            raise ValidationError("Insufficient data for backtesting (minimum 50 bars required)")
    
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
    
    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for backtesting.py library (ensure proper column names)"""
        prepared_data = data.copy()
        
        # Map column names to expected format
        column_mapping = {
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        # Rename columns if they exist in lowercase
        for old_name, new_name in column_mapping.items():
            if old_name in prepared_data.columns:
                prepared_data = prepared_data.rename(columns={old_name: new_name})
        
        # Ensure we have the required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in prepared_data.columns:
                raise ValidationError(f"Missing required column: {col}")
        
        return prepared_data[required_cols]
    
    def _generate_additional_analysis(self, stats) -> Dict[str, Any]:
        """Generate additional analysis from backtest stats"""
        equity_curve = stats['_equity_curve']['Equity']
        
        # Monthly and yearly returns
        try:
            returns = equity_curve.pct_change().dropna()
            monthly_returns = returns.groupby(pd.Grouper(freq='M')).apply(
                lambda x: (1 + x).prod() - 1
            )
            yearly_returns = returns.groupby(pd.Grouper(freq='Y')).apply(
                lambda x: (1 + x).prod() - 1
            )
        except:
            monthly_returns = pd.Series(dtype=float)
            yearly_returns = pd.Series(dtype=float)
        
        # Rolling metrics
        rolling_metrics = {}
        if len(equity_curve) > 252:
            returns = equity_curve.pct_change().dropna()
            rolling_metrics['sharpe'] = returns.rolling(252).apply(
                lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
            )
            rolling_metrics['volatility'] = returns.rolling(252).std() * np.sqrt(252)
        
        return {
            'monthly_returns': monthly_returns,
            'yearly_returns': yearly_returns,
            'rolling_metrics': rolling_metrics
        }
        
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