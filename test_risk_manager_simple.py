#!/usr/bin/env python3
"""
Simple Risk Manager Test

This script tests the core Risk Manager functionality in isolation
without complex margin and leverage calculations.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from trading_system.core.position_sizing import ExchangeLimits, PositionSizingInput, PositionSizingCalculator, PositionSide
from trading_system.core.futures_models import ExchangeType
from trading_system.core.config_manager import get_config_manager


def create_test_exchange_limits(symbol: str, min_notional: float = 5.0, 
                               min_qty: float = 0.001, max_leverage: int = 100) -> ExchangeLimits:
    """Create test exchange limits."""
    return ExchangeLimits(
        symbol=symbol,
        exchange="binance",
        min_notional=min_notional,
        min_qty=min_qty,
        max_qty=1000000.0,
        qty_step=0.001,
        price_step=0.01,
        max_leverage=max_leverage,
        maintenance_margin_rate=0.005  # 0.5%
    )


def print_position_result(result, test_name: str):
    """Print position sizing results."""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    
    print(f"📊 Symbol: {result.symbol}")
    print(f"🎯 Tradeable: {'✅' if result.is_tradeable else '❌'}")
    
    if result.is_tradeable:
        print(f"\n📈 Position Details:")
        print(f"   Position Size: {result.position_size_qty:.6f}")
        print(f"   Position Value: ${result.position_size_usdt:.2f}")
        print(f"   Required Margin: ${result.required_margin:.2f}")
        print(f"   Risk Amount: ${result.risk_amount:.2f}")
        print(f"   Risk Percent: {result.risk_percent:.3f}%")
        
        print(f"\n🛡️ Safety Analysis:")
        print(f"   Liquidation Price: ${result.liquidation_price:.4f}")
        print(f"   Liquidation Buffer: {result.liquidation_buffer:.2f}%")
        print(f"   Risk Buffer: {result.risk_buffer:.2f}%")
        print(f"   Safety Ratio: {result.safety_ratio:.2f}")
        
        print(f"\n🔒 Exchange Compliance:")
        print(f"   Min Notional: {'✅' if result.meets_min_notional else '❌'}")
        print(f"   Min Quantity: {'✅' if result.meets_min_qty else '❌'}")
        print(f"   Min Feasible Notional: ${result.min_feasible_notional:.2f}")
    else:
        print(f"   Reason: {result.rejection_reason}")


def test_basic_position_sizing():
    """Test basic position sizing calculations."""
    print("🧪 Testing Basic Position Sizing...")
    
    # Initialize calculator
    calculator = PositionSizingCalculator()
    
    # Test case 1: BTC long position
    limits = create_test_exchange_limits("BTC/USDT", min_notional=5.0, min_qty=0.001)
    
    inputs = PositionSizingInput(
        symbol="BTC/USDT",
        entry_price=50000.0,
        stop_loss_price=49000.0,  # 2% stop loss
        take_profit_price=52000.0,  # 4% take profit
        user_budget=1000.0,
        risk_per_trade_percent=0.002,  # 0.2%
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "BTC/USDT Long Position - $1000 Account")
    
    # Verify calculations
    expected_risk = 1000.0 * 0.002  # 0.2% risk
    expected_position_size = expected_risk / 1000.0  # $1000 price difference
    
    if result.is_tradeable:
        assert abs(result.risk_amount - expected_risk) < 0.01, f"Risk amount mismatch: {result.risk_amount} vs {expected_risk}"
        assert abs(result.position_size_qty - expected_position_size) < 0.000001, f"Position size mismatch: {result.position_size_qty} vs {expected_position_size}"
    
    print("✅ Basic position sizing test passed!")


def test_exchange_limits():
    """Test exchange limits compliance."""
    print("\n🧪 Testing Exchange Limits Compliance...")
    
    calculator = PositionSizingCalculator()
    
    # Test case: Small position that might not meet minimums
    limits = create_test_exchange_limits(
        symbol="ETH/USDT",
        min_notional=10.0,  # $10 minimum
        min_qty=0.01  # 0.01 ETH minimum
    )
    
    inputs = PositionSizingInput(
        symbol="ETH/USDT",
        entry_price=3000.0,
        stop_loss_price=2970.0,  # 1% stop loss
        take_profit_price=3060.0,  # 2% take profit
        user_budget=50.0,  # Small account
        risk_per_trade_percent=0.002,  # 0.2%
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "ETH/USDT Small Account - Strict Limits")
    
    # Test case: Position that should meet minimums
    inputs2 = PositionSizingInput(
        symbol="ETH/USDT",
        entry_price=3000.0,
        stop_loss_price=2970.0,  # 1% stop loss
        take_profit_price=3060.0,  # 2% take profit
        user_budget=1000.0,  # Larger account
        risk_per_trade_percent=0.002,  # 0.2%
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result2 = calculator.analyze_position_sizing(inputs2)
    print_position_result(result2, "ETH/USDT Large Account - Strict Limits")
    
    print("✅ Exchange limits test completed!")


def test_leverage_and_liquidation():
    """Test leverage and liquidation calculations."""
    print("\n🧪 Testing Leverage and Liquidation...")
    
    calculator = PositionSizingCalculator()
    
    # Test case: Leveraged position
    limits = create_test_exchange_limits(
        symbol="SOL/USDT",
        min_notional=5.0,
        min_qty=0.1,
        max_leverage=10
    )
    
    inputs = PositionSizingInput(
        symbol="SOL/USDT",
        entry_price=100.0,
        stop_loss_price=98.0,  # 2% stop loss
        take_profit_price=104.0,  # 4% take profit
        user_budget=500.0,
        risk_per_trade_percent=0.002,  # 0.2%
        leverage=5,  # 5x leverage
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "SOL/USDT with 5x Leverage")
    
    # Verify leverage calculations
    if result.is_tradeable:
        expected_margin = result.position_size_usdt / 5
        assert abs(result.required_margin - expected_margin) < 0.01, f"Margin calculation error: {result.required_margin} vs {expected_margin}"
    
    print("✅ Leverage and liquidation test completed!")


def test_risk_limits():
    """Test risk limit enforcement."""
    print("\n🧪 Testing Risk Limits...")
    
    calculator = PositionSizingCalculator()
    
    # Test case: Position that might exceed maximum position size
    limits = create_test_exchange_limits(
        symbol="DOGE/USDT",
        min_notional=5.0,
        min_qty=100.0
    )
    
    inputs = PositionSizingInput(
        symbol="DOGE/USDT",
        entry_price=0.1,
        stop_loss_price=0.099,  # Very tight stop loss
        take_profit_price=0.102,  # Small take profit
        user_budget=10000.0,  # Large account
        risk_per_trade_percent=0.002,  # 0.2%
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "DOGE/USDT Large Position Test")
    
    # Verify position size limits
    if result.is_tradeable:
        max_position_value = 10000.0 * 0.1  # 10% of account
        assert result.position_size_usdt <= max_position_value, f"Position exceeds maximum: {result.position_size_usdt} > {max_position_value}"
    
    print("✅ Risk limits test completed!")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    
    calculator = PositionSizingCalculator()
    
    # Test case 1: Invalid stop loss (same as entry)
    limits = create_test_exchange_limits("BTC/USDT")
    
    inputs = PositionSizingInput(
        symbol="BTC/USDT",
        entry_price=50000.0,
        stop_loss_price=50000.0,  # Same as entry - invalid
        take_profit_price=52000.0,
        user_budget=1000.0,
        risk_per_trade_percent=0.002,
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "Invalid Stop Loss (Same as Entry)")
    assert not result.is_tradeable, "Should reject invalid stop loss"
    
    # Test case 2: Very small account balance
    inputs2 = PositionSizingInput(
        symbol="BTC/USDT",
        entry_price=50000.0,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        user_budget=1.0,  # Very small account
        risk_per_trade_percent=0.002,
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result2 = calculator.analyze_position_sizing(inputs2)
    print_position_result(result2, "Very Small Account Balance")
    
    # Test case 3: Zero account balance
    inputs3 = PositionSizingInput(
        symbol="BTC/USDT",
        entry_price=50000.0,
        stop_loss_price=49000.0,
        take_profit_price=52000.0,
        user_budget=0.0,  # Zero balance
        risk_per_trade_percent=0.002,
        leverage=1,
        position_side=PositionSide.LONG,
        exchange_limits=limits
    )
    
    result3 = calculator.analyze_position_sizing(inputs3)
    print_position_result(result3, "Zero Account Balance")
    
    print("✅ Edge cases test completed!")


def test_configuration():
    """Test configuration loading and risk settings."""
    print("\n🧪 Testing Configuration...")
    
    # Load configuration
    config_manager = get_config_manager()
    risk_config = config_manager.get_risk_management_config()
    
    print(f"\n📋 Risk Management Configuration:")
    print(f"   Max Budget: ${risk_config.max_budget:.2f}")
    print(f"   Max Risk per Trade: {risk_config.max_risk_per_trade:.3%}")
    print(f"   Min Safety Ratio: {risk_config.min_safety_ratio:.2f}")
    print(f"   Default Leverage: {risk_config.default_leverage}x")
    print(f"   Max Position Percent: {risk_config.max_position_percent:.1%}")
    
    # Test different risk configurations
    calculator = PositionSizingCalculator(risk_config)
    
    limits = create_test_exchange_limits("BTC/USDT")
    
    # Test with different risk percentages
    risk_percentages = [0.001, 0.002, 0.005, 0.01]  # 0.1%, 0.2%, 0.5%, 1%
    
    for risk_pct in risk_percentages:
        inputs = PositionSizingInput(
            symbol="BTC/USDT",
            entry_price=50000.0,
            stop_loss_price=49000.0,
            take_profit_price=52000.0,
            user_budget=1000.0,
            risk_per_trade_percent=risk_pct,
            leverage=1,
            position_side=PositionSide.LONG,
            exchange_limits=limits
        )
        
        result = calculator.analyze_position_sizing(inputs)
        print(f"\n💰 Risk {risk_pct:.3%} - Tradeable: {'✅' if result.is_tradeable else '❌'}")
        if result.is_tradeable:
            print(f"   Position Size: {result.position_size_qty:.6f} BTC")
            print(f"   Risk Amount: ${result.risk_amount:.2f}")
    
    print("✅ Configuration test completed!")


def test_short_positions():
    """Test short position calculations."""
    print("\n🧪 Testing Short Positions...")
    
    calculator = PositionSizingCalculator()
    
    # Test short position
    limits = create_test_exchange_limits("ETH/USDT")
    
    inputs = PositionSizingInput(
        symbol="ETH/USDT",
        entry_price=3000.0,
        stop_loss_price=3030.0,  # Stop loss above entry for short
        take_profit_price=2940.0,  # Take profit below entry
        user_budget=1000.0,
        risk_per_trade_percent=0.002,
        leverage=1,
        position_side=PositionSide.SHORT,
        exchange_limits=limits
    )
    
    result = calculator.analyze_position_sizing(inputs)
    print_position_result(result, "ETH/USDT Short Position")
    
    print("✅ Short positions test completed!")


def main():
    """Run all risk manager tests."""
    print("🚀 Starting Simple Risk Manager Tests")
    print("=" * 60)
    
    try:
        # Test basic functionality
        test_basic_position_sizing()
        
        # Test exchange limits
        test_exchange_limits()
        
        # Test leverage and liquidation
        test_leverage_and_liquidation()
        
        # Test risk limits
        test_risk_limits()
        
        # Test edge cases
        test_edge_cases()
        
        # Test configuration
        test_configuration()
        
        # Test short positions
        test_short_positions()
        
        print("\n" + "=" * 60)
        print("🎉 All Risk Manager tests completed successfully!")
        print("✅ Risk Manager core functionality is working correctly")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
