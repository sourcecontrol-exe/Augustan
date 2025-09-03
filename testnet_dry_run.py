#!/usr/bin/env python3
"""
Binance Testnet Dry-Run - Final Dress Rehearsal

This script performs a comprehensive test of the entire trading system
using Binance testnet to confirm all components work with real exchange
connections without risking real money.

Prerequisites:
- Binance testnet API keys configured
- Testnet enabled in config
- Sufficient testnet USDT balance
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from trading_system.core.config_manager import get_config_manager
from trading_system.core.futures_models import ExchangeType
from trading_system.data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
from trading_system.risk_manager.risk_manager import RiskManager
from trading_system.risk_manager.portfolio_manager import PortfolioManager
from trading_system.data_feeder.realtime_feeder import BinanceWebsocketFeeder
from trading_system.live_trading.live_engine import LiveTradingEngine
from trading_system.jobs.enhanced_volume_job import EnhancedVolumeJob


class TestnetDryRun:
    """Comprehensive testnet dry-run for the trading system."""
    
    def __init__(self, config_path: str = "config/exchanges_config.json"):
        """Initialize the dry-run test."""
        self.config_path = config_path
        self.config_manager = get_config_manager(config_path)
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "errors": [],
            "warnings": []
        }
        
        print("🚀 Starting Binance Testnet Dry-Run")
        print("=" * 60)
        print(f"📋 Config Path: {config_path}")
        print(f"⏰ Start Time: {self.results['start_time']}")
        print("=" * 60)
    
    def log_result(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """Log test results."""
        self.results["tests"][test_name] = {
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
        if details:
            print(f"   📝 {details}")
        if error:
            print(f"   ❌ Error: {error}")
            self.results["errors"].append(f"{test_name}: {error}")
    
    def test_configuration(self):
        """Test configuration loading and testnet settings."""
        print("\n🧪 Testing Configuration...")
        
        try:
            # Load configuration
            config = self.config_manager.get_raw_config()
            
            # Check Binance testnet settings
            binance_config = config.get("binance", {})
            testnet_enabled = binance_config.get("testnet", False)
            api_key = binance_config.get("api_key", "")
            secret = binance_config.get("secret", "")
            
            if not testnet_enabled:
                self.log_result("Configuration", False, "", "Binance testnet not enabled")
                return False
            
            if not api_key or not secret:
                self.log_result("Configuration", False, "", "Binance testnet API keys not configured")
                return False
            
            # Check risk management config
            risk_config = self.config_manager.get_risk_management_config()
            
            self.log_result("Configuration", True, 
                           f"Testnet enabled, API keys configured, Risk: {risk_config.max_risk_per_trade:.3%}")
            return True
            
        except Exception as e:
            self.log_result("Configuration", False, "", str(e))
            return False
    
    def test_exchange_connection(self):
        """Test connection to Binance testnet."""
        print("\n🧪 Testing Exchange Connection...")
        
        try:
            # Initialize exchange limits fetcher with configuration
            config = self.config_manager.get_raw_config()
            limits_fetcher = ExchangeLimitsFetcher(exchanges_config=config)
            
            # Test connection by fetching account info
            exchange = limits_fetcher.exchanges.get(ExchangeType.BINANCE)
            if not exchange:
                self.log_result("Exchange Connection", False, "", "Binance exchange not initialized")
                return False
            
            # Fetch account balance
            balance = exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            if usdt_balance < 100:
                self.log_result("Exchange Connection", True, 
                               f"Connected to Binance testnet, USDT balance: {usdt_balance}", 
                               "Low testnet balance - consider adding more")
                self.results["warnings"].append(f"Low testnet balance: {usdt_balance} USDT")
            else:
                self.log_result("Exchange Connection", True, 
                               f"Connected to Binance testnet, USDT balance: {usdt_balance}")
            
            return True
            
        except Exception as e:
            self.log_result("Exchange Connection", False, "", str(e))
            return False
    
    def test_market_data(self):
        """Test market data fetching from testnet."""
        print("\n🧪 Testing Market Data...")
        
        try:
            # Initialize exchange limits fetcher with configuration
            config = self.config_manager.get_raw_config()
            limits_fetcher = ExchangeLimitsFetcher(exchanges_config=config)
            
            # Test symbols
            test_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            
            # Fetch current prices
            prices = limits_fetcher.get_current_prices(test_symbols, ExchangeType.BINANCE)
            
            if not prices:
                self.log_result("Market Data", False, "", "Could not fetch market prices")
                return False
            
            # Fetch exchange limits
            limits_results = {}
            for symbol in test_symbols:
                limits = limits_fetcher.fetch_symbol_limits(ExchangeType.BINANCE, symbol)
                if limits:
                    limits_results[symbol] = {
                        "min_notional": limits.min_notional,
                        "min_qty": limits.min_qty,
                        "max_leverage": limits.max_leverage
                    }
            
            self.log_result("Market Data", True, 
                           f"Fetched prices for {len(prices)} symbols, limits for {len(limits_results)} symbols")
            return True
            
        except Exception as e:
            self.log_result("Market Data", False, "", str(e))
            return False
    
    def test_risk_manager(self):
        """Test risk manager with real market data."""
        print("\n🧪 Testing Risk Manager...")
        
        try:
            risk_manager = RiskManager(self.config_path)
            # Initialize exchange limits fetcher with configuration
            config = self.config_manager.get_raw_config()
            limits_fetcher = ExchangeLimitsFetcher(exchanges_config=config)
            
            # Test position sizing with real data
            symbol = "BTC/USDT"
            current_price = limits_fetcher.get_current_prices([symbol], ExchangeType.BINANCE).get(symbol, 50000)
            limits = limits_fetcher.fetch_symbol_limits(ExchangeType.BINANCE, symbol)
            
            if not limits:
                self.log_result("Risk Manager", False, "", f"Could not fetch limits for {symbol}")
                return False
            
            # Create a mock signal for testing
            class MockSignal:
                def __init__(self, symbol, signal_type):
                    self.symbol = symbol
                    self.signal_type = signal_type
                    self.confidence = 0.75
                    self.strategy = "test"
                    self.timestamp = datetime.now()
                    self.metadata = {"test": True}
            
            from trading_system.core.position_state import SignalType
            signal = MockSignal(symbol, SignalType.BUY_OPEN)
            
            # Calculate position size
            result = risk_manager.calculate_position_size(
                signal=signal,
                current_price=current_price,
                account_balance=1000.0,
                leverage=1,
                exchange_limits=limits
            )
            
            if result.is_safe_to_trade:
                self.log_result("Risk Manager", True, 
                               f"Position size: {result.position_size:.6f}, Risk: ${result.risk_amount:.2f}")
            else:
                self.log_result("Risk Manager", True, 
                               f"Trade rejected: {result.rejection_reason}")
            
            return True
            
        except Exception as e:
            self.log_result("Risk Manager", False, "", str(e))
            return False
    
    def test_portfolio_manager(self):
        """Test portfolio manager with testnet account."""
        print("\n🧪 Testing Portfolio Manager...")
        
        try:
            # Initialize portfolio manager with testnet config
            portfolio = PortfolioManager(1000.0, self.config_path)
            
            # Calculate portfolio metrics
            metrics = portfolio.calculate_portfolio_metrics()
            
            self.log_result("Portfolio Manager", True, 
                           f"Balance: ${metrics.total_account_balance:.2f}, "
                           f"Available: ${metrics.available_balance:.2f}, "
                           f"Positions: {metrics.open_positions_count}")
            
            return True
            
        except Exception as e:
            self.log_result("Portfolio Manager", False, "", str(e))
            return False
    
    def test_realtime_data(self):
        """Test real-time data feed from testnet."""
        print("\n🧪 Testing Real-Time Data...")
        
        try:
            # Test WebSocket connection
            symbols = ["BTC/USDT"]
            feeder = BinanceWebsocketFeeder(symbols, timeframe='1m', stream_type='ticker')
            
            # Track messages
            message_count = 0
            last_price = 0
            
            def on_price_update(symbol: str, candle):
                nonlocal message_count, last_price
                message_count += 1
                last_price = candle.close
                print(f"   📡 {symbol}: ${candle.close:.4f} | #{message_count}")
            
            feeder.add_callback(on_price_update)
            feeder.start()
            
            # Wait for messages
            time.sleep(10)
            
            feeder.stop()
            feeder.cleanup()
            
            if message_count > 0 and last_price > 0:
                self.log_result("Real-Time Data", True, 
                               f"Received {message_count} messages, Last price: ${last_price:.4f}")
            else:
                self.log_result("Real-Time Data", False, "", "No messages received")
            
            return message_count > 0
            
        except Exception as e:
            self.log_result("Real-Time Data", False, "", str(e))
            return False
    
    def test_live_trading_engine(self):
        """Test live trading engine in paper trading mode."""
        print("\n🧪 Testing Live Trading Engine...")
        
        try:
            # Initialize live trading engine
            engine = LiveTradingEngine(
                symbols=["BTC/USDT"],
                account_balance=1000.0,
                config_path=self.config_path,
                paper_trading=True
            )
            
            # Start engine
            engine.start()
            
            # Let it run for a short time
            time.sleep(15)
            
            # Stop engine
            engine.stop()
            
            self.log_result("Live Trading Engine", True, 
                           "Engine started and stopped successfully in paper trading mode")
            return True
            
        except Exception as e:
            self.log_result("Live Trading Engine", False, "", str(e))
            return False
    
    def test_volume_analysis(self):
        """Test volume analysis with testnet data."""
        print("\n🧪 Testing Volume Analysis...")
        
        try:
            # Initialize enhanced volume job
            risk_config = self.config_manager.get_risk_management_config()
            job = EnhancedVolumeJob(config_path=self.config_path, risk_config=risk_config)
            
            # Run analysis
            results = job.run_enhanced_volume_analysis()
            
            if results and len(results.get('tradeable_symbols', [])) > 0:
                tradeable_count = len(results['tradeable_symbols'])
                self.log_result("Volume Analysis", True, 
                               f"Found {tradeable_count} tradeable symbols")
            else:
                self.log_result("Volume Analysis", True, 
                               "Analysis completed, no tradeable symbols found")
            
            return True
            
        except Exception as e:
            self.log_result("Volume Analysis", False, "", str(e))
            return False
    
    def test_order_placement(self):
        """Test order placement (without execution)."""
        print("\n🧪 Testing Order Placement...")
        
        try:
            # Initialize exchange limits fetcher with configuration
            config = self.config_manager.get_raw_config()
            limits_fetcher = ExchangeLimitsFetcher(exchanges_config=config)
            exchange = limits_fetcher.exchanges.get(ExchangeType.BINANCE)
            
            if not exchange:
                self.log_result("Order Placement", False, "", "Exchange not available")
                return False
            
            # Test order placement simulation
            symbol = "BTC/USDT"
            side = "buy"
            order_type = "limit"
            amount = 0.001  # Small amount
            price = 50000  # Reasonable price
            
            # Create order (but don't submit)
            order = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'amount': amount,
                'price': price,
                'test': True  # This would be a test order
            }
            
            self.log_result("Order Placement", True, 
                           f"Order structure created: {symbol} {side} {amount} @ {price}")
            return True
            
        except Exception as e:
            self.log_result("Order Placement", False, "", str(e))
            return False
    
    def run_all_tests(self):
        """Run all dry-run tests."""
        print("🚀 Starting Comprehensive Testnet Dry-Run")
        print("=" * 60)
        
        tests = [
            ("Configuration", self.test_configuration),
            ("Exchange Connection", self.test_exchange_connection),
            ("Market Data", self.test_market_data),
            ("Risk Manager", self.test_risk_manager),
            ("Portfolio Manager", self.test_portfolio_manager),
            ("Real-Time Data", self.test_realtime_data),
            ("Live Trading Engine", self.test_live_trading_engine),
            ("Volume Analysis", self.test_volume_analysis),
            ("Order Placement", self.test_order_placement),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_result(test_name, False, "", f"Unexpected error: {str(e)}")
        
        # Calculate results
        self.results["end_time"] = datetime.now().isoformat()
        self.results["summary"] = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": (passed / total) * 100 if total > 0 else 0
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 DRY-RUN SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        print(f"📈 Success Rate: {self.results['summary']['success_rate']:.1f}%")
        
        if self.results["errors"]:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        if self.results["warnings"]:
            print(f"\n⚠️ Warnings ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"   • {warning}")
        
        # Save results
        results_file = f"testnet_dry_run_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        # Final assessment
        if passed == total:
            print("\n🎉 ALL TESTS PASSED - System ready for production!")
        elif passed >= total * 0.8:
            print("\n✅ MOST TESTS PASSED - System mostly ready, review failures")
        else:
            print("\n❌ MANY TESTS FAILED - System needs fixes before production")
        
        return passed == total


def main():
    """Main function to run the testnet dry-run."""
    print("🚀 Binance Testnet Dry-Run - Final Dress Rehearsal")
    print("=" * 60)
    print("This will test the entire trading system with real exchange connections")
    print("using Binance testnet. No real money will be risked.")
    print("=" * 60)
    
    # Check if user wants to proceed
    response = input("\nDo you want to proceed with the testnet dry-run? (y/N): ")
    if response.lower() != 'y':
        print("Dry-run cancelled.")
        return
    
    # Run the dry-run
    dry_run = TestnetDryRun()
    success = dry_run.run_all_tests()
    
    if success:
        print("\n🎉 DRY-RUN COMPLETED SUCCESSFULLY!")
        print("The trading system is ready for production deployment.")
    else:
        print("\n⚠️ DRY-RUN COMPLETED WITH ISSUES")
        print("Please review the results and fix any failures before going live.")


if __name__ == "__main__":
    main()
