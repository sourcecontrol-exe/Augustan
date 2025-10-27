#!/usr/bin/env python3
"""
Overnight Trading Setup Script
=================================

This script sets up the Augustan trading system to run overnight with proper 
risk management, monitoring, and profit tracking.

Features:
- Configurable trading symbols and balance
- Overnight duration (8-12 hours)
- Profit monitoring and alerting
- Automatic risk management
- Emergency stop capabilities
- Performance reporting

Usage:
    python start_overnight_trading.py --symbols BTC/USDT ETH/USDT --balance 1000 --duration 480
"""

import argparse
import sys
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
import signal

# Add the trading system to the path
sys.path.append('.')

from trading_system.live_trading.live_engine import LiveTradingEngine
from loguru import logger

class OvernightTradingManager:
    """Manages overnight trading operations with monitoring and safety features."""
    
    def __init__(self, symbols: List[str], balance: float, duration_minutes: int, 
                 paper_trading: bool = True, config_path: str = None):
        """
        Initialize overnight trading manager.
        
        Args:
            symbols: List of trading symbols
            balance: Initial trading balance
            duration_minutes: Duration to run in minutes
            paper_trading: If True, run in paper trading mode
            config_path: Path to configuration file
        """
        self.symbols = symbols
        self.balance = balance
        self.duration_minutes = duration_minutes
        self.paper_trading = paper_trading
        self.config_path = config_path
        
        # Trading components
        self.trading_engine = None
        self.is_running = False
        self.start_time = None
        
        # Monitoring
        self.profit_target_percent = 5.0  # 5% profit target
        self.max_loss_percent = 3.0  # 3% stop loss
        self.check_interval = 60  # Check every minute
        
        # Performance tracking
        self.initial_balance = balance
        self.max_profit = 0.0
        self.max_drawdown = 0.0
        self.trades_taken = 0
        
        # Safety mechanisms
        self.emergency_stop = False
        self.last_check_time = None
        
        logger.info(f"Overnight Trading Manager initialized:")
        logger.info(f"  Symbols: {', '.join(symbols)}")
        logger.info(f"  Balance: ${balance:,.2f}")
        logger.info(f"  Duration: {duration_minutes} minutes ({duration_minutes/60:.1f} hours)")
        logger.info(f"  Mode: {'Paper Trading' if paper_trading else 'Live Trading'}")
        logger.info(f"  Profit Target: {self.profit_target_percent}%")
        logger.info(f"  Max Loss: {self.max_loss_percent}%")
    
    def setup(self):
        """Initialize the trading engine and set up monitoring."""
        try:
            logger.info("🔧 Setting up overnight trading system...")
            
            # Initialize trading engine
            self.trading_engine = LiveTradingEngine(
                watchlist=self.symbols,
                initial_balance=self.balance,
                config_path=self.config_path,
                paper_trading=self.paper_trading
            )
            
            # Add trade callback for monitoring
            self.trading_engine.add_trade_callback(self._on_trade_executed)
            
            logger.info("✅ Trading engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup trading system: {e}")
            return False
    
    def start_trading(self):
        """Start overnight trading with monitoring."""
        if not self.trading_engine:
            logger.error("Trading engine not initialized. Call setup() first.")
            return False
        
        try:
            logger.info("🚀 Starting overnight trading...")
            self.start_time = datetime.now()
            self.last_check_time = self.start_time
            self.is_running = True
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Start trading engine
            self.trading_engine.start()
            
            # Start monitoring thread
            monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            monitor_thread.start()
            
            # Run for specified duration
            logger.info(f"⏱️ Running for {self.duration_minutes} minutes until {(self.start_time + timedelta(minutes=self.duration_minutes)).strftime('%H:%M:%S')}")
            
            # Main trading loop
            self._run_trading_cycle()
            
        except Exception as e:
            logger.error(f"❌ Error during trading: {e}")
            return False
        finally:
            self._stop_trading()
        
        return True
    
    def _run_trading_cycle(self):
        """Main trading cycle with duration control."""
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)
        
        while (datetime.now() < end_time and 
               self.is_running and 
               not self.emergency_stop):
            
            # Check every minute
            time.sleep(self.check_interval)
            
            # Log progress
            elapsed = datetime.now() - self.start_time
            remaining = end_time - datetime.now()
            logger.info(f"📊 Trading Status: {elapsed} elapsed, {remaining} remaining")
    
    def _monitoring_loop(self):
        """Background monitoring for profit/loss and safety."""
        while self.is_running and not self.emergency_stop:
            try:
                self._check_performance()
                self._check_safety_limits()
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)
    
    def _check_performance(self):
        """Check trading performance and targets."""
        if not self.trading_engine:
            return
        
        try:
            # Get current portfolio status
            status = self.trading_engine.get_engine_status()
            current_balance = status['portfolio']['total_account_balance']
            
            # Calculate performance
            profit_loss = current_balance - self.initial_balance
            profit_percent = (profit_loss / self.initial_balance) * 100
            
            # Track maximums
            if profit_loss > self.max_profit:
                self.max_profit = profit_loss
            
            if profit_percent < -self.max_drawdown:
                self.max_drawdown = abs(profit_percent)
            
            # Check profit target
            if profit_percent >= self.profit_target_percent:
                logger.success(f"🎯 PROFIT TARGET REACHED! {profit_percent:.2f}% profit (${profit_loss:+.2f})")
                self._log_performance_summary()
                
                # Could optionally stop trading here
                # self.emergency_stop = True
            
            # Log significant moves
            if abs(profit_percent) > 1.0:  # Log moves > 1%
                logger.info(f"💰 Performance Update: {profit_percent:+.2f}% (${profit_loss:+.2f}) | Balance: ${current_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Performance check error: {e}")
    
    def _check_safety_limits(self):
        """Check safety limits and trigger emergency stop if needed."""
        if not self.trading_engine:
            return
        
        try:
            status = self.trading_engine.get_engine_status()
            current_balance = status['portfolio']['total_account_balance']
            
            profit_percent = ((current_balance - self.initial_balance) / self.initial_balance) * 100
            
            # Check maximum loss
            if profit_percent <= -self.max_loss_percent:
                logger.error(f"🚨 EMERGENCY STOP! Maximum loss exceeded: {profit_percent:.2f}%")
                self.emergency_stop = True
            
            # Check portfolio health
            if 'risk_limits_exceeded' in status.get('portfolio', {}):
                logger.warning(f"⚠️ Risk limits exceeded")
            
        except Exception as e:
            logger.error(f"Safety check error: {e}")
    
    def _on_trade_executed(self, trade_data: Dict[str, Any]):
        """Callback for when a trade is executed."""
        self.trades_taken += 1
        logger.info(f"📈 Trade #{self.trades_taken}: {trade_data['symbol']} {trade_data['signal_type']} "
                   f"at ${trade_data['price']:.4f} (Size: {trade_data['position_size']:.6f})")
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals."""
        logger.info(f"🛑 Received signal {signum}, stopping trading...")
        self.emergency_stop = True
        self.is_running = False
    
    def _stop_trading(self):
        """Stop trading and generate final report."""
        logger.info("🛑 Stopping overnight trading...")
        self.is_running = False
        
        if self.trading_engine:
            try:
                self.trading_engine.stop()
                logger.info("✅ Trading engine stopped")
            except Exception as e:
                logger.error(f"Error stopping trading engine: {e}")
        
        # Generate final report
        self._log_performance_summary()
    
    def _log_performance_summary(self):
        """Generate and log performance summary."""
        try:
            if not self.trading_engine:
                return
            
            # Get final status
            final_status = self.trading_engine.get_engine_status()
            final_balance = final_status['portfolio']['total_account_balance']
            
            # Calculate metrics
            total_profit_loss = final_balance - self.initial_balance
            total_return_percent = (total_profit_loss / self.initial_balance) * 100
            
            # Trading stats
            trade_stats = self.trading_engine.get_trade_analytics()
            
            # Duration
            duration = datetime.now() - self.start_time if self.start_time else timedelta()
            
            logger.info("=" * 80)
            logger.info("📊 OVERNIGHT TRADING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏱️ Duration: {duration}")
            logger.info(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
            logger.info(f"💰 Final Balance: ${final_balance:,.2f}")
            logger.info(f"💰 Total P&L: ${total_profit_loss:+,.2f}")
            logger.info(f"📈 Return: {total_return_percent:+.2f}%")
            logger.info(f"🎯 Max Profit: ${self.max_profit:+.2f}")
            logger.info(f"📉 Max Drawdown: {self.max_drawdown:.2f}%")
            logger.info(f"📊 Trades Taken: {self.trades_taken}")
            logger.info(f"📊 Total Trades: {trade_stats.get('total_trades', 0)}")
            logger.info(f"✅ Win Rate: {trade_stats.get('success_rate', 0)*100:.1f}%")
            
            # Performance rating
            if total_return_percent > 5:
                logger.success("🎉 EXCELLENT PERFORMANCE!")
            elif total_return_percent > 2:
                logger.success("✅ Good Performance")
            elif total_return_percent > 0:
                logger.info("👍 Positive Performance")
            else:
                logger.warning("⚠️ Negative Performance")
            
            logger.info("=" * 80)
            
            # Save summary to file
            self._save_summary_to_file(final_status, total_profit_loss, total_return_percent)
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
    
    def _save_summary_to_file(self, status: Dict[str, Any], profit_loss: float, return_percent: float):
        """Save trading summary to file."""
        try:
            summary_data = {
                'timestamp': datetime.now().isoformat(),
                'duration_minutes': self.duration_minutes,
                'symbols': self.symbols,
                'initial_balance': self.initial_balance,
                'final_balance': status['portfolio']['total_account_balance'],
                'profit_loss': profit_loss,
                'return_percent': return_percent,
                'max_profit': self.max_profit,
                'max_drawdown': self.max_drawdown,
                'trades_taken': self.trades_taken,
                'paper_trading': self.paper_trading,
                'trade_analytics': self.trading_engine.get_trade_analytics(),
                'engine_status': status
            }
            
            filename = f"overnight_trading_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            logger.info(f"📄 Summary saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving summary: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Start overnight trading with Augustan')
    
    parser.add_argument('--symbols', nargs='+', default=['BTC/USDT'], 
                       help='Trading symbols (e.g., BTC/USDT ETH/USDT)')
    parser.add_argument('--balance', type=float, default=1000.0, 
                       help='Initial trading balance')
    parser.add_argument('--duration', type=int, default=480, 
                       help='Duration in minutes - default: 480 = 8 hours')
    parser.add_argument('--paper', action='store_true', default=True,
                       help='Run in paper trading mode - default: True')
    parser.add_argument('--live', action='store_true',
                       help='Run in live trading mode - FALSE BY DEFAULT - USE WITH CAUTION')
    parser.add_argument('--config', type=str, 
                       help='Path to configuration file')
    parser.add_argument('--profit-target', type=float, default=5.0,
                       help='Profit target percentage - default: 5.0')
    parser.add_argument('--max-loss', type=float, default=3.0,
                       help='Maximum loss percentage - default: 3.0')
    
    args = parser.parse_args()
    
    # Determine trading mode
    paper_trading = args.paper and not args.live
    
    # Safety warning for live trading
    if not paper_trading:
        print("🚨 WARNING: LIVE TRADING MODE - REAL MONEY AT RISK!")
        print("Press Ctrl+C to cancel, or wait 10 seconds to continue...")
        time.sleep(10)
    
    # Initialize and configure trading manager
    trading_manager = OvernightTradingManager(
        symbols=args.symbols,
        balance=args.balance,
        duration_minutes=args.duration,
        paper_trading=paper_trading,
        config_path=args.config
    )
    
    # Set custom targets if provided
    trading_manager.profit_target_percent = args.profit_target
    trading_manager.max_loss_percent = args.max_loss
    
    # Setup and start trading
    if trading_manager.setup():
        logger.info("🎯 Starting overnight trading session...")
        success = trading_manager.start_trading()
        
        if success:
            logger.success("🎉 Overnight trading completed successfully!")
        else:
            logger.error("❌ Overnight trading encountered errors!")
            
        return 0 if success else 1
    else:
        logger.error("❌ Failed to setup trading system!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
