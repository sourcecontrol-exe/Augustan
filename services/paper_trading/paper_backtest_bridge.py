"""
Bridge between Paper Trading and Backtesting Systems

Allows conversion between paper trading results and backtesting format
for unified performance analysis and comparison.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging

from backtesting.performance_metrics import PerformanceAnalyzer
from paper_trading.paper_trader import VirtualPortfolio, VirtualOrder, PaperTradingEngine


class PaperBacktestBridge:
    """Bridge for converting paper trading results to backtesting format"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.performance_analyzer = PerformanceAnalyzer()
    
    def convert_paper_trades_to_backtest_format(self, paper_trader: PaperTradingEngine) -> pd.DataFrame:
        """Convert paper trading trades to backtesting format"""
        trades_data = []
        
        for trade in paper_trader.portfolio.trade_history:
            trades_data.append({
                'timestamp': trade['timestamp'],
                'symbol': trade['symbol'],
                'side': trade['side'],
                'quantity': trade['quantity'],
                'price': trade['price'],
                'commission': trade['commission'],
                'order_id': trade['order_id']
            })
        
        if not trades_data:
            return pd.DataFrame()
            
        trades_df = pd.DataFrame(trades_data)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
        trades_df = trades_df.sort_values('timestamp')
        
        return trades_df
    
    def convert_equity_curve_to_backtest_format(self, paper_trader: PaperTradingEngine) -> pd.DataFrame:
        """Convert paper trading equity curve to backtesting format"""
        if not paper_trader.portfolio.equity_history:
            return pd.DataFrame()
        
        equity_data = []
        for timestamp, equity in paper_trader.portfolio.equity_history:
            equity_data.append({
                'timestamp': timestamp,
                'equity': equity,
                'returns': 0.0  # Will be calculated
            })
        
        equity_df = pd.DataFrame(equity_data)
        equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
        equity_df = equity_df.sort_values('timestamp')
        
        # Calculate returns
        equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)
        
        return equity_df
    
    def generate_paper_trading_report(self, paper_trader: PaperTradingEngine, 
                                    current_prices: Dict[str, float]) -> Dict:
        """Generate comprehensive paper trading report in backtesting format"""
        
        # Convert data
        trades_df = self.convert_paper_trades_to_backtest_format(paper_trader)
        equity_df = self.convert_equity_curve_to_backtest_format(paper_trader)
        
        # Calculate basic metrics
        initial_capital = paper_trader.config.initial_capital
        final_equity = paper_trader.portfolio.get_total_equity(current_prices)
        total_return = (final_equity - initial_capital) / initial_capital
        
        report = {
            'session_info': {
                'initial_capital': initial_capital,
                'final_equity': final_equity,
                'total_return': total_return,
                'total_trades': len(trades_df),
                'duration_hours': self._calculate_session_duration(equity_df),
                'symbols_traded': trades_df['symbol'].nunique() if not trades_df.empty else 0
            },
            'portfolio_state': {
                'cash': paper_trader.portfolio.cash,
                'positions': len(paper_trader.portfolio.positions),
                'pending_orders': len([o for o in paper_trader.orders.values() 
                                     if o.status.value == 'pending'])
            }
        }
        
        # Add performance metrics if we have equity data
        if not equity_df.empty and len(equity_df) > 1:
            try:
                metrics = self.performance_analyzer.calculate_metrics(
                    equity_df['equity'].values,
                    equity_df['returns'].values
                )
                report['performance_metrics'] = metrics
            except Exception as e:
                self.logger.warning(f"Could not calculate performance metrics: {e}")
                report['performance_metrics'] = {}
        
        # Add trade analysis if we have trades
        if not trades_df.empty:
            trade_analysis = self._analyze_trades(trades_df)
            report['trade_analysis'] = trade_analysis
        
        # Add position analysis
        if paper_trader.portfolio.positions:
            position_analysis = self._analyze_positions(paper_trader.portfolio.positions, current_prices)
            report['position_analysis'] = position_analysis
        
        return report
    
    def _calculate_session_duration(self, equity_df: pd.DataFrame) -> float:
        """Calculate session duration in hours"""
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        
        start_time = equity_df['timestamp'].iloc[0]
        end_time = equity_df['timestamp'].iloc[-1]
        duration = (end_time - start_time).total_seconds() / 3600
        
        return round(duration, 2)
    
    def _analyze_trades(self, trades_df: pd.DataFrame) -> Dict:
        """Analyze trading patterns and statistics"""
        if trades_df.empty:
            return {}
        
        # Basic trade statistics
        total_trades = len(trades_df)
        buy_trades = len(trades_df[trades_df['side'] == 'buy'])
        sell_trades = len(trades_df[trades_df['side'] == 'sell'])
        
        # Commission analysis
        total_commission = trades_df['commission'].sum()
        avg_commission = trades_df['commission'].mean()
        
        # Symbol distribution
        symbol_counts = trades_df['symbol'].value_counts().to_dict()
        
        # Trading frequency
        if len(trades_df) > 1:
            time_diff = trades_df['timestamp'].iloc[-1] - trades_df['timestamp'].iloc[0]
            trades_per_hour = total_trades / (time_diff.total_seconds() / 3600) if time_diff.total_seconds() > 0 else 0
        else:
            trades_per_hour = 0
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_commission': round(total_commission, 4),
            'avg_commission': round(avg_commission, 4),
            'trades_per_hour': round(trades_per_hour, 2),
            'symbol_distribution': symbol_counts,
            'avg_trade_size': round(trades_df['quantity'].mean(), 6),
            'avg_trade_value': round((trades_df['quantity'] * trades_df['price']).mean(), 2)
        }
    
    def _analyze_positions(self, positions: Dict, current_prices: Dict[str, float]) -> Dict:
        """Analyze current positions"""
        position_analysis = {}
        
        for symbol, position in positions.items():
            current_price = current_prices.get(symbol, 0)
            market_value = position.quantity * current_price
            cost_basis = position.quantity * position.avg_price
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_pct = unrealized_pnl / cost_basis if cost_basis > 0 else 0
            
            position_analysis[symbol] = {
                'quantity': position.quantity,
                'avg_price': position.avg_price,
                'current_price': current_price,
                'market_value': round(market_value, 2),
                'cost_basis': round(cost_basis, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'unrealized_pnl_pct': round(unrealized_pnl_pct, 4),
                'realized_pnl': round(position.realized_pnl, 2)
            }
        
        return position_analysis
    
    def compare_with_backtest(self, paper_report: Dict, backtest_result: Dict) -> Dict:
        """Compare paper trading results with backtesting results"""
        comparison = {
            'paper_trading': {
                'total_return': paper_report['session_info']['total_return'],
                'total_trades': paper_report['session_info']['total_trades'],
                'sharpe_ratio': paper_report.get('performance_metrics', {}).get('sharpe_ratio', 0),
                'max_drawdown': paper_report.get('performance_metrics', {}).get('max_drawdown', 0)
            },
            'backtesting': {
                'total_return': backtest_result.get('total_return', 0),
                'total_trades': backtest_result.get('total_trades', 0),
                'sharpe_ratio': backtest_result.get('sharpe_ratio', 0),
                'max_drawdown': backtest_result.get('max_drawdown', 0)
            }
        }
        
        # Calculate differences
        comparison['differences'] = {
            'return_diff': comparison['paper_trading']['total_return'] - comparison['backtesting']['total_return'],
            'trades_diff': comparison['paper_trading']['total_trades'] - comparison['backtesting']['total_trades'],
            'sharpe_diff': comparison['paper_trading']['sharpe_ratio'] - comparison['backtesting']['sharpe_ratio'],
            'drawdown_diff': comparison['paper_trading']['max_drawdown'] - comparison['backtesting']['max_drawdown']
        }
        
        return comparison
    
    def save_paper_trading_results(self, paper_trader: PaperTradingEngine, 
                                 current_prices: Dict[str, float], 
                                 filename_prefix: str = "paper_trading"):
        """Save paper trading results in multiple formats"""
        
        # Generate report
        report = self.generate_paper_trading_report(paper_trader, current_prices)
        
        # Save trades
        trades_df = self.convert_paper_trades_to_backtest_format(paper_trader)
        if not trades_df.empty:
            trades_filename = f"{filename_prefix}_trades.csv"
            trades_df.to_csv(trades_filename, index=False)
            self.logger.info(f"Saved trades to {trades_filename}")
        
        # Save equity curve
        equity_df = self.convert_equity_curve_to_backtest_format(paper_trader)
        if not equity_df.empty:
            equity_filename = f"{filename_prefix}_equity_curve.csv"
            equity_df.to_csv(equity_filename, index=False)
            self.logger.info(f"Saved equity curve to {equity_filename}")
        
        # Save report as JSON
        import json
        report_filename = f"{filename_prefix}_report.json"
        with open(report_filename, 'w') as f:
            # Convert datetime objects to strings for JSON serialization
            json_report = self._prepare_report_for_json(report)
            json.dump(json_report, f, indent=2)
        
        self.logger.info(f"Saved report to {report_filename}")
        
        return {
            'trades_file': trades_filename if not trades_df.empty else None,
            'equity_file': equity_filename if not equity_df.empty else None,
            'report_file': report_filename
        }
    
    def _prepare_report_for_json(self, report: Dict) -> Dict:
        """Prepare report for JSON serialization"""
        import json
        
        def convert_value(obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            elif isinstance(obj, pd.Series):
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_value(item) for item in obj]
            else:
                return obj
        
        return convert_value(report)
