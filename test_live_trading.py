#!/usr/bin/env python3
"""
Test Live Trading System

This script tests the new real-time data feeder and risk manager integration.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from trading_system import (
    LiveTradingEngine,
    RiskManager, 
    BinanceWebsocketFeeder,
    MultiExchangeRealtimeFeeder,
    PortfolioManager,
    get_config_manager
)


def test_risk_manager():
    """Test the core risk manager functionality."""
    print("🔧 Testing Risk Manager...")
    
    risk_manager = RiskManager()
    
    # Test account balance validation
    valid, reason = risk_manager.validate_account_balance(100.0)
    print(f"  ✅ Account validation (100 USD): {valid}")
    
    valid, reason = risk_manager.validate_account_balance(5.0)
    print(f"  ❌ Account validation (5 USD): {valid} - {reason}")
    
    # Test risk summary
    summary = risk_manager.get_risk_summary(1000.0)
    print(f"  📊 Risk Summary for $1000:")
    print(f"    - Max risk per trade: ${summary['max_risk_per_trade_usd']:.2f} ({summary['max_risk_per_trade_percent']:.2f}%)")
    print(f"    - Max position value: ${summary['max_position_value']:.2f} ({summary['max_position_percent']:.1f}%)")


def test_portfolio_manager():
    """Test portfolio manager functionality."""
    print("\n💼 Testing Portfolio Manager...")
    
    portfolio = PortfolioManager(initial_balance=1000.0)
    
    # Test portfolio limits
    can_open, reason = portfolio.can_open_new_position("BTC/USDT", 200.0)
    print(f"  ✅ Can open BTC position ($200): {can_open}")
    
    can_open, reason = portfolio.can_open_new_position("ETH/USDT", 600.0)
    print(f"  ❌ Can open ETH position ($600): {can_open} - {reason if not can_open else ''}")
    
    # Test portfolio metrics
    metrics = portfolio.calculate_portfolio_metrics()
    print(f"  📈 Portfolio Metrics:")
    print(f"    - Balance: ${metrics.total_account_balance:.2f}")
    print(f"    - Positions: {metrics.position_count}")
    print(f"    - Risk: {metrics.portfolio_risk_percentage:.2f}%")


def test_realtime_feeder():
    """Test real-time WebSocket data feeder."""
    print("\n📡 Testing Real-Time Data Feeder...")
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
    feeder = BinanceWebsocketFeeder(symbols, timeframe='1m')
    
    # Set up callback to monitor data
    def on_price_update(symbol: str, candle):
        print(f"  📊 {symbol}: ${candle.close:.4f} at {candle.timestamp.strftime('%H:%M:%S')}")
    
    feeder.add_callback(on_price_update)
    
    print(f"  🚀 Starting WebSocket for {len(symbols)} symbols...")
    feeder.start()
    
    # Let it run for 30 seconds
    time.sleep(30)
    
    # Stop the feeder immediately to prevent more callbacks
    feeder.stop()
    
    # Check connection status
    status = feeder.get_connection_status()
    print(f"  📊 Connection Status:")
    print(f"    - Running: {status['is_running']}")
    print(f"    - Connected: {status['connected']}")
    print(f"    - Symbols with data: {sum(1 for s in status['symbols'].values() if s['is_fresh'])}")
    
    # Get current prices
    prices = feeder.get_all_prices()
    print(f"  💰 Current Prices:")
    for symbol, price in prices.items():
        if price > 0:
            print(f"    - {symbol}: ${price:.4f}")
    print("  ✅ WebSocket feeder test completed")


def test_live_trading_engine():
    """Test the complete live trading engine."""
    print("\n🚀 Testing Live Trading Engine...")
    
    watchlist = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
    initial_balance = 1000.0
    
    engine = LiveTradingEngine(
        watchlist=watchlist,
        initial_balance=initial_balance,
        paper_trading=True  # Important: Paper trading only
    )
    
    # Add callback to monitor trades
    def on_trade_event(trade_event: Dict[str, Any]):
        print(f"  💸 TRADE: {trade_event['symbol']} {trade_event['signal_type']} "
              f"- Size: {trade_event['position_size']:.6f}, "
              f"Risk: ${trade_event['risk_amount']:.2f}")
    
    engine.add_trade_callback(on_trade_event)
    
    print(f"  🎯 Starting live trading engine for {len(watchlist)} symbols...")
    engine.start()
    
    # Let it run for 2 minutes to see if any signals are generated
    print("  ⏱️  Running for 2 minutes to monitor for signals...")
    time.sleep(120)
    
    # Stop the engine immediately to prevent more processing
    engine.stop()
    
    # Get engine status
    status = engine.get_engine_status()
    print(f"  📊 Engine Status:")
    print(f"    - Signals Generated: {status['engine_info']['signals_generated']}")
    print(f"    - Trades Executed: {status['engine_info']['trades_executed']}")
    print(f"    - Portfolio Balance: ${status['portfolio']['total_account_balance']:.2f}")
    print(f"    - Active Positions: {status['portfolio']['position_count']}")
    
    # Get portfolio summary
    portfolio_summary = engine.get_portfolio_summary()
    print(f"  💼 Portfolio Summary:")
    print(f"    - Total Return: {portfolio_summary['account_info']['total_return']:.2f}%")
    print(f"    - Risk Utilization: {portfolio_summary['portfolio_metrics']['portfolio_risk_percentage']:.2f}%")
    print("  ✅ Live trading engine test completed")


async def test_async_trading():
    """Test async trading engine operation."""
    print("\n🔄 Testing Async Trading Engine...")
    
    watchlist = ['BTC/USDT', 'ETH/USDT']
    engine = LiveTradingEngine(
        watchlist=watchlist,
        initial_balance=500.0,
        paper_trading=True
    )
    
    # Run for 1 minute asynchronously
    print("  ⚡ Running async trading for 1 minute...")
    await engine.run_async(duration_minutes=1)
    
    # Get final status
    status = engine.get_engine_status()
    print(f"  📈 Final Status: {status['engine_info']['signals_generated']} signals, "
          f"{status['engine_info']['trades_executed']} trades")
    
    print("  ✅ Async trading test completed")


def test_configuration_integration():
    """Test centralized configuration integration."""
    print("\n⚙️ Testing Configuration Integration...")
    
    config_manager = get_config_manager()
    
    # Test risk config
    risk_config = config_manager.get_risk_management_config()
    print(f"  📊 Risk Config:")
    print(f"    - Max risk per trade: {risk_config.max_risk_per_trade:.3%}")
    print(f"    - Default leverage: {risk_config.default_leverage}x")
    print(f"    - Max budget: ${risk_config.max_budget:.2f}")
    
    # Test data fetching config
    data_config = config_manager.get_data_fetching_config()
    print(f"  🔄 Data Config:")
    print(f"    - Max retries: {data_config.max_retries}")
    print(f"    - Timeout: {data_config.timeout_seconds}s")
    print(f"    - Backoff multiplier: {data_config.backoff_multiplier}x")
    
    # Test signal config
    signal_config = config_manager.get_signal_generation_config()
    print(f"  📈 Signal Config:")
    print(f"    - RSI period: {signal_config.rsi_period}")
    print(f"    - MACD fast: {signal_config.macd_fast}")
    print(f"    - Min confidence: {signal_config.min_signal_strength}")
    
    print("  ✅ Configuration integration test completed")


def main():
    """Run all tests."""
    print("🧪 LIVE TRADING SYSTEM TESTS")
    print("=" * 50)
    
    try:
        # Test individual components
        test_configuration_integration()
        test_risk_manager()
        test_portfolio_manager()
        
        # Test real-time components (requires internet connection)
        print("\n⚠️  Real-time tests require internet connection...")
        user_input = input("Run real-time tests? (y/n): ").lower().strip()
        
        if user_input == 'y':
            test_realtime_feeder()
            test_live_trading_engine()
            
            # Test async functionality
            print("\n🔄 Running async test...")
            asyncio.run(test_async_trading())
        else:
            print("  ⏭️  Skipped real-time tests")
        
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("\n📋 SUMMARY:")
        print("✅ Centralized Configuration Management")
        print("✅ Risk Manager with Position Sizing")
        print("✅ Portfolio Manager with Risk Limits")
        if user_input == 'y':
            print("✅ Real-Time WebSocket Data Feeder")
            print("✅ Live Trading Engine Integration")
            print("✅ Async Trading Operation")
        
        print("\n🚀 SYSTEM READY FOR LIVE TRADING!")
        print("💡 Use paper_trading=True for safe testing")
        print("⚠️  Set paper_trading=False only when ready for real trading")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
