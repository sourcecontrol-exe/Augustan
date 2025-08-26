# ==============================================================================
# File: performance_metrics.py
# Description: Comprehensive performance analytics for backtesting
# ==============================================================================

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PerformanceMetrics:
    """Container for all performance metrics"""
    # Returns
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Risk Metrics
    max_drawdown: float
    max_drawdown_duration: int
    var_95: float
    cvar_95: float
    
    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Additional Metrics
    information_ratio: float
    treynor_ratio: float
    alpha: float
    beta: float
    
    # Drawdown Analysis
    drawdown_periods: List[Dict[str, Any]]
    
    # Monthly/Yearly Returns
    monthly_returns: pd.Series
    yearly_returns: pd.Series


class PerformanceAnalyzer:
    """Comprehensive performance analysis for trading strategies"""
    
    def __init__(self, risk_free_rate: float = 0.02, benchmark_returns: Optional[pd.Series] = None):
        self.risk_free_rate = risk_free_rate
        self.benchmark_returns = benchmark_returns
    
    def analyze_performance(self, df: pd.DataFrame, signals: pd.Series, 
                          initial_capital: float = 100000,
                          commission: float = 0.001) -> PerformanceMetrics:
        """
        Comprehensive performance analysis
        
        Args:
            df: OHLCV data
            signals: Trading signals (BUY, SELL, HOLD)
            initial_capital: Starting capital
            commission: Commission rate per trade
            
        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        # Calculate portfolio returns
        portfolio_data = self._calculate_portfolio_returns(df, signals, initial_capital, commission)
        returns = portfolio_data['returns']
        equity_curve = portfolio_data['equity_curve']
        trades = portfolio_data['trades']
        
        # Calculate all metrics
        metrics = self._calculate_all_metrics(returns, equity_curve, trades, df.index)
        
        return metrics
    
    def _calculate_portfolio_returns(self, df: pd.DataFrame, signals: pd.Series,
                                   initial_capital: float, commission: float) -> Dict[str, Any]:
        """Calculate portfolio returns and equity curve"""
        # Align data
        df_aligned = df.copy()
        signals_aligned = signals.reindex(df.index, fill_value='HOLD')
        
        # Calculate price returns
        price_returns = df_aligned['close'].pct_change().fillna(0)
        
        # Generate position signals
        positions = signals_aligned.map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
        
        # Calculate strategy returns with commission
        strategy_returns = []
        current_position = 0
        trades = []
        
        for i, (date, signal) in enumerate(signals_aligned.items()):
            if i == 0:
                strategy_returns.append(0)
                continue
            
            prev_position = current_position
            
            # Update position based on signal
            if signal == 'BUY' and current_position <= 0:
                current_position = 1
            elif signal == 'SELL' and current_position >= 0:
                current_position = -1
            elif signal == 'HOLD':
                pass  # Keep current position
            
            # Calculate return
            period_return = price_returns.iloc[i] * prev_position
            
            # Apply commission if position changed
            if current_position != prev_position:
                period_return -= commission
                trades.append({
                    'date': date,
                    'action': signal,
                    'price': df_aligned['close'].iloc[i],
                    'position_change': current_position - prev_position
                })
            
            strategy_returns.append(period_return)
        
        # Convert to series
        returns = pd.Series(strategy_returns, index=df.index)
        
        # Calculate equity curve
        equity_curve = (1 + returns).cumprod() * initial_capital
        
        return {
            'returns': returns,
            'equity_curve': equity_curve,
            'trades': trades,
            'positions': positions
        }
    
    def _calculate_all_metrics(self, returns: pd.Series, equity_curve: pd.Series,
                             trades: List[Dict], dates: pd.Index) -> PerformanceMetrics:
        """Calculate all performance metrics"""
        
        # Basic return metrics
        if len(equity_curve) == 0:
            total_return = 0.0
        else:
            total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1 if equity_curve.iloc[0] != 0 else 0.0
        
        # Annualized return
        years = len(returns) / 252  # Assuming daily data
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Volatility
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.0
        
        # Sharpe ratio
        excess_returns = returns - self.risk_free_rate/252
        sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 0 and returns.std() > 0 else 0
        
        # Sortino ratio
        downside_returns = returns[returns < 0] if len(returns) > 0 else pd.Series(dtype=float)
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = excess_returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 and len(excess_returns) > 0 else 0
        
        # Drawdown analysis
        drawdown_data = self._calculate_drawdowns(equity_curve)
        max_drawdown = drawdown_data['max_drawdown']
        max_drawdown_duration = drawdown_data['max_duration']
        drawdown_periods = drawdown_data['periods']
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # VaR and CVaR
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        cvar_95 = returns[returns <= var_95].mean() if len(returns) > 0 and len(returns[returns <= var_95]) > 0 else 0
        
        # Trade analysis
        trade_analysis = self._analyze_trades(trades, equity_curve)
        
        # Beta and Alpha (if benchmark provided)
        beta, alpha = self._calculate_beta_alpha(returns)
        
        # Information ratio
        if self.benchmark_returns is not None and len(returns) > 0:
            benchmark_aligned = self.benchmark_returns.reindex(returns.index, fill_value=0)
            excess_return = returns - benchmark_aligned
            tracking_error = excess_return.std() * np.sqrt(252)
            information_ratio = excess_return.mean() / tracking_error * np.sqrt(252) if tracking_error > 0 else 0
        else:
            information_ratio = 0
        
        # Treynor ratio
        treynor_ratio = excess_returns.mean() / beta * 252 if beta != 0 and len(excess_returns) > 0 else 0
        
        # Monthly and yearly returns
        monthly_returns = self._calculate_period_returns(returns, 'M')
        yearly_returns = self._calculate_period_returns(returns, 'Y')
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            var_95=var_95,
            cvar_95=cvar_95,
            total_trades=trade_analysis['total_trades'],
            winning_trades=trade_analysis['winning_trades'],
            losing_trades=trade_analysis['losing_trades'],
            win_rate=trade_analysis['win_rate'],
            avg_win=trade_analysis['avg_win'],
            avg_loss=trade_analysis['avg_loss'],
            profit_factor=trade_analysis['profit_factor'],
            information_ratio=information_ratio,
            treynor_ratio=treynor_ratio,
            alpha=alpha,
            beta=beta,
            drawdown_periods=drawdown_periods,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns
        )
    
    def _calculate_drawdowns(self, equity_curve: pd.Series) -> Dict[str, Any]:
        """Calculate drawdown analysis"""
        if len(equity_curve) == 0:
            return {
                'max_drawdown': 0.0,
                'max_duration': 0,
                'periods': [],
                'drawdown_series': pd.Series(dtype=float)
            }
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = (equity_curve - running_max) / running_max
        
        # Find maximum drawdown
        max_drawdown = drawdown.min()
        
        # Find drawdown periods
        in_drawdown = drawdown < 0
        drawdown_periods = []
        
        start_idx = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                end_idx = i - 1
                period_dd = drawdown.iloc[start_idx:end_idx+1].min()
                drawdown_periods.append({
                    'start': equity_curve.index[start_idx],
                    'end': equity_curve.index[end_idx],
                    'duration': end_idx - start_idx + 1,
                    'drawdown': period_dd
                })
                start_idx = None
        
        # Handle case where drawdown continues to end
        if start_idx is not None:
            period_dd = drawdown.iloc[start_idx:].min()
            drawdown_periods.append({
                'start': equity_curve.index[start_idx],
                'end': equity_curve.index[-1],
                'duration': len(equity_curve) - start_idx,
                'drawdown': period_dd
            })
        
        # Find maximum duration
        max_duration = max([p['duration'] for p in drawdown_periods]) if drawdown_periods else 0
        
        return {
            'max_drawdown': max_drawdown,
            'max_duration': max_duration,
            'periods': drawdown_periods,
            'drawdown_series': drawdown
        }
    
    def _analyze_trades(self, trades: List[Dict], equity_curve: pd.Series) -> Dict[str, Any]:
        """Analyze individual trades"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        # Group trades into complete round trips
        trade_returns = []
        entry_price = None
        entry_type = None
        
        for trade in trades:
            if trade['action'] in ['BUY', 'SELL'] and entry_price is None:
                entry_price = trade['price']
                entry_type = trade['action']
            elif trade['action'] in ['BUY', 'SELL'] and entry_price is not None:
                # Calculate return
                if entry_type == 'BUY':
                    trade_return = (trade['price'] - entry_price) / entry_price
                else:  # SELL
                    trade_return = (entry_price - trade['price']) / entry_price
                
                trade_returns.append(trade_return)
                entry_price = trade['price']
                entry_type = trade['action']
        
        if not trade_returns:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0
            }
        
        # Analyze returns
        winning_trades = [r for r in trade_returns if r > 0]
        losing_trades = [r for r in trade_returns if r < 0]
        
        total_trades = len(trade_returns)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        win_rate = num_winning / total_trades if total_trades > 0 else 0
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': num_winning,
            'losing_trades': num_losing,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }
    
    def _calculate_beta_alpha(self, returns: pd.Series) -> Tuple[float, float]:
        """Calculate beta and alpha relative to benchmark"""
        if self.benchmark_returns is None:
            return 1.0, 0.0
        
        # Align returns
        benchmark_aligned = self.benchmark_returns.reindex(returns.index, fill_value=0)
        
        # Calculate beta
        covariance = np.cov(returns, benchmark_aligned)[0, 1]
        benchmark_variance = np.var(benchmark_aligned)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
        
        # Calculate alpha
        avg_return = returns.mean() * 252
        avg_benchmark = benchmark_aligned.mean() * 252
        alpha = avg_return - (self.risk_free_rate + beta * (avg_benchmark - self.risk_free_rate))
        
        return beta, alpha
    
    def _calculate_period_returns(self, returns: pd.Series, period: str) -> pd.Series:
        """Calculate returns for specific periods (M=monthly, Y=yearly)"""
        try:
            # Group by period and calculate cumulative returns
            grouped = returns.groupby(pd.Grouper(freq=period))
            period_returns = grouped.apply(lambda x: (1 + x).prod() - 1)
            return period_returns
        except:
            return pd.Series(dtype=float)
    
    def generate_report(self, metrics: PerformanceMetrics) -> str:
        """Generate a formatted performance report"""
        report = f"""
PERFORMANCE ANALYSIS REPORT
{'='*50}

RETURN METRICS:
  Total Return:           {metrics.total_return:.2%}
  Annualized Return:      {metrics.annualized_return:.2%}
  Volatility:             {metrics.volatility:.2%}

RISK-ADJUSTED RETURNS:
  Sharpe Ratio:           {metrics.sharpe_ratio:.3f}
  Sortino Ratio:          {metrics.sortino_ratio:.3f}
  Calmar Ratio:           {metrics.calmar_ratio:.3f}
  Information Ratio:      {metrics.information_ratio:.3f}
  Treynor Ratio:          {metrics.treynor_ratio:.3f}

RISK METRICS:
  Maximum Drawdown:       {metrics.max_drawdown:.2%}
  Max DD Duration:        {metrics.max_drawdown_duration} periods
  VaR (95%):             {metrics.var_95:.2%}
  CVaR (95%):            {metrics.cvar_95:.2%}

TRADE STATISTICS:
  Total Trades:           {metrics.total_trades}
  Winning Trades:         {metrics.winning_trades}
  Losing Trades:          {metrics.losing_trades}
  Win Rate:               {metrics.win_rate:.2%}
  Average Win:            {metrics.avg_win:.2%}
  Average Loss:           {metrics.avg_loss:.2%}
  Profit Factor:          {metrics.profit_factor:.2f}

MARKET EXPOSURE:
  Beta:                   {metrics.beta:.3f}
  Alpha:                  {metrics.alpha:.2%}

{'='*50}
        """
        return report.strip()


class StrategyComparison:
    """Compare multiple strategies side by side"""
    
    def __init__(self):
        self.strategies = {}
        self.results = {}
    
    def add_strategy(self, name: str, df: pd.DataFrame, signals: pd.Series,
                    initial_capital: float = 100000, commission: float = 0.001):
        """Add a strategy for comparison"""
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze_performance(df, signals, initial_capital, commission)
        
        self.strategies[name] = {
            'signals': signals,
            'metrics': metrics
        }
    
    def compare_strategies(self) -> pd.DataFrame:
        """Generate comparison table of all strategies"""
        if not self.strategies:
            return pd.DataFrame()
        
        comparison_data = {}
        
        for name, data in self.strategies.items():
            metrics = data['metrics']
            comparison_data[name] = {
                'Total Return': f"{metrics.total_return:.2%}",
                'Annualized Return': f"{metrics.annualized_return:.2%}",
                'Volatility': f"{metrics.volatility:.2%}",
                'Sharpe Ratio': f"{metrics.sharpe_ratio:.3f}",
                'Sortino Ratio': f"{metrics.sortino_ratio:.3f}",
                'Max Drawdown': f"{metrics.max_drawdown:.2%}",
                'Win Rate': f"{metrics.win_rate:.2%}",
                'Profit Factor': f"{metrics.profit_factor:.2f}",
                'Total Trades': metrics.total_trades
            }
        
        return pd.DataFrame(comparison_data).T
    
    def rank_strategies(self, metric: str = 'sharpe_ratio') -> List[Tuple[str, float]]:
        """Rank strategies by a specific metric"""
        rankings = []
        
        for name, data in self.strategies.items():
            metrics = data['metrics']
            value = getattr(metrics, metric, 0)
            rankings.append((name, value))
        
        # Sort by metric value (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
