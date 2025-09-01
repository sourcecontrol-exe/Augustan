#!/usr/bin/env python3
"""
Test script for position sizing and risk management functionality.
"""

from src.core.position_sizing import (
    PositionSizingCalculator, PositionSizingInput, RiskManagementConfig,
    ExchangeLimits, PositionSide
)
from src.data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
from src.jobs.enhanced_volume_job import EnhancedVolumeJob
from src.core.futures_models import ExchangeType


def test_position_sizing_calculator():
    """Test the position sizing calculator with sample data."""
    print("🧪 Testing Position Sizing Calculator...")
    
    # Create sample exchange limits
    btc_limits = ExchangeLimits(
        symbol="BTC/USDT",
        exchange="binance",
        min_notional=5.0,
        min_qty=0.001,
        max_qty=1000.0,
        qty_step=0.001,
        price_step=0.01,
        max_leverage=125,
        maintenance_margin_rate=0.004  # 0.4%
    )
    
    # Create risk config for $50 budget
    risk_config = RiskManagementConfig(
        max_budget=50.0,
        max_risk_per_trade=0.002,  # 0.2%
        min_safety_ratio=1.5,
        default_leverage=5
    )
    
    calculator = PositionSizingCalculator(risk_config)
    
    # Test BTC at $100,000 with 2% stop loss
    btc_price = 100000.0
    stop_loss_price = btc_price * 0.98  # 2% stop loss
    
    inputs = PositionSizingInput(
        symbol="BTC/USDT",
        entry_price=btc_price,
        stop_loss_price=stop_loss_price,
        take_profit_price=btc_price * 1.04,
        user_budget=50.0,
        risk_per_trade_percent=0.002,
        leverage=5,
        position_side=PositionSide.LONG,
        exchange_limits=btc_limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    
    print(f"\n📊 BTC/USDT Analysis:")
    print(f"   Entry Price: ${btc_price:,.2f}")
    print(f"   Stop Loss: ${stop_loss_price:,.2f}")
    print(f"   Budget: ${inputs.user_budget:.2f}")
    print(f"   Leverage: {inputs.leverage}x")
    
    if result.is_tradeable:
        print(f"   ✅ TRADEABLE")
        print(f"   Position Size: {result.position_size_qty:.6f} BTC")
        print(f"   Position Value: ${result.position_size_usdt:.2f}")
        print(f"   Required Margin: ${result.required_margin:.2f}")
        print(f"   Liquidation Price: ${result.liquidation_price:,.2f}")
        print(f"   Safety Ratio: {result.safety_ratio:.2f}x")
    else:
        print(f"   ❌ NOT TRADEABLE: {result.rejection_reason}")
    
    return result.is_tradeable


def test_exchange_limits_fetcher():
    """Test fetching real exchange limits."""
    print("\n🌐 Testing Exchange Limits Fetcher...")
    
    try:
        fetcher = ExchangeLimitsFetcher()
        
        # Test fetching limits for BTC/USDT
        limits = fetcher.fetch_symbol_limits(ExchangeType.BINANCE, "BTC/USDT")
        
        if limits:
            print(f"   ✅ Fetched limits for BTC/USDT:")
            print(f"   Min Notional: ${limits.min_notional:.2f}")
            print(f"   Min Qty: {limits.min_qty:.6f}")
            print(f"   Max Leverage: {limits.max_leverage}x")
            print(f"   Maintenance Margin: {limits.maintenance_margin_rate:.3%}")
            return True
        else:
            print(f"   ❌ Could not fetch limits for BTC/USDT")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_enhanced_volume_job():
    """Test the enhanced volume job with position sizing."""
    print("\n📈 Testing Enhanced Volume Job...")
    
    try:
        # Create risk config
        risk_config = RiskManagementConfig(
            max_budget=50.0,
            max_risk_per_trade=0.002
        )
        
        job = EnhancedVolumeJob(risk_config=risk_config)
        
        # Test getting tradeable symbols (may not work without running full analysis)
        try:
            tradeable = job.get_tradeable_symbols(5)
            print(f"   ✅ Found {len(tradeable)} tradeable symbols")
            for symbol in tradeable:
                print(f"      • {symbol}")
            return True
        except:
            print(f"   ⚠️  No cached analysis found (run enhanced analysis first)")
            print(f"   To test: python3 cli.py volume analyze --enhanced")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all position sizing tests."""
    print("🚀 Position Sizing System Tests")
    print("=" * 50)
    
    tests = [
        ("Position Sizing Calculator", test_position_sizing_calculator),
        ("Exchange Limits Fetcher", test_exchange_limits_fetcher),
        ("Enhanced Volume Job", test_enhanced_volume_job)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"   ❌ Test failed with error: {e}")
    
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed or skipped")
    
    print(f"\n💡 To test the full system:")
    print("   python3 cli.py volume analyze --enhanced --budget 50")
    print("   python3 cli.py position tradeable --budget 50")
    print("   python3 cli.py position analyze --symbol BTC/USDT --budget 50")


if __name__ == "__main__":
    main()
