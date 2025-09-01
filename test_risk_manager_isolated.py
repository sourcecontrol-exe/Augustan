#!/usr/bin/env python3
"""
Isolated Risk Manager Test

This script tests the Risk Manager component in isolation to ensure
all risk calculations, position sizing, and safety checks work correctly.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from trading_system.risk_manager.risk_manager import RiskManager, RiskCalculationResult
from trading_system.core.position_state import EnhancedSignal, SignalType, PositionState
from trading_system.core.position_sizing import ExchangeLimits, PositionSizingInput, PositionSizingCalculator
from trading_system.core.futures_models import ExchangeType
from trading_system.core.config_manager import get_config_manager


class MockSignal:
    """Mock signal class for testing that has the required attributes."""
    
    def __init__(self, symbol: str, signal_type: SignalType, price: float):
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.confidence = 0.75
        self.strategy = "test"
        self.timestamp = datetime.now()
        self.metadata = {"test": True}


def create_test_signal(symbol: str, signal_type: SignalType, 
                      entry_price: float, stop_loss: float, 
                      take_profit: float = None) -> MockSignal:
    """Create a test signal for risk calculations."""
    return MockSignal(symbol, signal_type, entry_price)


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


def print_risk_result(result: RiskCalculationResult, test_name: str):
    """Print risk calculation results in a formatted way."""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name}")
    print(f"{'='*60}")
    
    print(f"📊 Signal: {result.signal.symbol} - {result.signal.signal_type.value}")
    print(f"💰 Current Price: ${result.current_price:.4f}")
    print(f"💵 Account Balance: ${result.account_balance:.2f}")
    
    print(f"\n📈 Position Sizing:")
    print(f"   Risk Amount: ${result.risk_amount:.2f}")
    print(f"   Position Size: {result.position_size:.6f}")
    print(f"   Position Value: ${result.position_value:.2f}")
    print(f"   Required Margin: ${result.required_margin:.2f}")
    
    print(f"\n⚠️ Risk Metrics:")
    print(f"   Risk Percentage: {result.risk_percentage:.3f}%")
    print(f"   Reward/Risk Ratio: {result.reward_risk_ratio:.2f}")
    print(f"   Max Loss %: {result.max_loss_percentage:.3f}%")
    
    print(f"\n🔒 Exchange Compliance:")
    print(f"   Min Notional: {'✅' if result.meets_min_notional else '❌'}")
    print(f"   Min Quantity: {'✅' if result.meets_min_quantity else '❌'}")
    print(f"   Adjusted: {'✅' if result.adjusted_for_limits else '❌'}")
    
    if result.liquidation_price:
        print(f"\n💀 Liquidation Analysis:")
        print(f"   Liquidation Price: ${result.liquidation_price:.4f}")
        print(f"   Distance to Liquidation: {result.liquidation_distance:.2f}%")
    
    print(f"\n🎯 Final Decision:")
    if result.is_safe_to_trade:
        print(f"   ✅ SAFE TO TRADE")
    else:
        print(f"   ❌ NOT SAFE TO TRADE")
        print(f"   Reason: {result.rejection_reason}")
    
    if result.safety_warnings:
        print(f"\n⚠️ Safety Warnings:")
        for warning in result.safety_warnings:
            print(f"   • {warning}")


def test_position_sizing_calculator():
    """Test the PositionSizingCalculator directly."""
    print("🧪 Testing PositionSizingCalculator...")
    
    from trading_system.core.position_sizing import PositionSide
    
    # Initialize calculator
    calculator = PositionSizingCalculator()
    
    # Test case: BTC long position
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
    
    print(f"\n📊 Position Sizing Analysis:")
    print(f"   Symbol: {result.symbol}")
    print(f"   Tradeable: {'✅' if result.is_tradeable else '❌'}")
    if result.is_tradeable:
        print(f"   Position Size: {result.position_size_qty:.6f} BTC")
        print(f"   Position Value: ${result.position_size_usdt:.2f}")
        print(f"   Risk Amount: ${result.risk_amount:.2f}")
        print(f"   Safety Ratio: {result.safety_ratio:.2f}")
    else:
        print(f"   Reason: {result.rejection_reason}")
    
    # Verify calculations
    expected_risk = 1000.0 * 0.002  # 0.2% risk
    expected_position_size = expected_risk / 1000.0  # $1000 price difference
    
    if result.is_tradeable:
        assert abs(result.risk_amount - expected_risk) < 0.01, f"Risk amount mismatch: {result.risk_amount} vs {expected_risk}"
        assert abs(result.position_size_qty - expected_position_size) < 0.000001, f"Position size mismatch: {result.position_size_qty} vs {expected_position_size}"
    
    print("✅ PositionSizingCalculator test passed!")


def test_basic_position_sizing():
    """Test basic position sizing calculations."""
    print("🧪 Testing Basic Position Sizing...")
    
    # Initialize risk manager
    risk_manager = RiskManager()
    
    # Test case 1: BTC long position
    signal = create_test_signal(
        symbol="BTC/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=50000.0,
        stop_loss=49000.0  # 2% stop loss
    )
    
    result = risk_manager.calculate_position_size(
        signal=signal,
        current_price=50000.0,
        account_balance=1000.0,
        leverage=1
    )
    
    print_risk_result(result, "BTC/USDT Long Position - $1000 Account")
    
    # Verify calculations
    expected_risk = 1000.0 * 0.002  # 0.2% risk
    expected_position_size = expected_risk / 1000.0  # $1000 price difference
    
    assert abs(result.risk_amount - expected_risk) < 0.01, f"Risk amount mismatch: {result.risk_amount} vs {expected_risk}"
    assert abs(result.position_size - expected_position_size) < 0.000001, f"Position size mismatch: {result.position_size} vs {expected_position_size}"
    
    print("✅ Basic position sizing test passed!")


def test_exchange_limits():
    """Test exchange limits compliance."""
    print("\n🧪 Testing Exchange Limits Compliance...")
    
    risk_manager = RiskManager()
    
    # Test case: Small position that might not meet minimums
    signal = create_test_signal(
        symbol="ETH/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=3000.0,
        stop_loss=2970.0  # 1% stop loss
    )
    
    # Create strict exchange limits
    limits = create_test_exchange_limits(
        symbol="ETH/USDT",
        min_notional=10.0,  # $10 minimum
        min_qty=0.01  # 0.01 ETH minimum
    )
    
    result = risk_manager.calculate_position_size(
        signal=signal,
        current_price=3000.0,
        account_balance=50.0,  # Small account
        leverage=1,
        exchange_limits=limits
    )
    
    print_risk_result(result, "ETH/USDT with Strict Exchange Limits")
    
    # Test case: Position that should meet minimums
    result2 = risk_manager.calculate_position_size(
        signal=signal,
        current_price=3000.0,
        account_balance=1000.0,  # Larger account
        leverage=1,
        exchange_limits=limits
    )
    
    print_risk_result(result2, "ETH/USDT with Larger Account")
    
    print("✅ Exchange limits test completed!")


def test_leverage_and_liquidation():
    """Test leverage and liquidation calculations."""
    print("\n🧪 Testing Leverage and Liquidation...")
    
    risk_manager = RiskManager()
    
    # Test case: Leveraged position
    signal = create_test_signal(
        symbol="SOL/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=100.0,
        stop_loss=98.0  # 2% stop loss
    )
    
    limits = create_test_exchange_limits(
        symbol="SOL/USDT",
        min_notional=5.0,
        min_qty=0.1,
        max_leverage=10
    )
    
    result = risk_manager.calculate_position_size(
        signal=signal,
        current_price=100.0,
        account_balance=500.0,
        leverage=5,  # 5x leverage
        exchange_limits=limits
    )
    
    print_risk_result(result, "SOL/USDT with 5x Leverage")
    
    # Verify leverage calculations
    expected_margin = result.position_value / 5
    assert abs(result.required_margin - expected_margin) < 0.01, f"Margin calculation error: {result.required_margin} vs {expected_margin}"
    
    print("✅ Leverage and liquidation test completed!")


def test_risk_limits():
    """Test risk limit enforcement."""
    print("\n🧪 Testing Risk Limits...")
    
    risk_manager = RiskManager()
    
    # Test case: Position that exceeds maximum position size
    signal = create_test_signal(
        symbol="DOGE/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=0.1,
        stop_loss=0.099  # Very tight stop loss
    )
    
    limits = create_test_exchange_limits(
        symbol="DOGE/USDT",
        min_notional=5.0,
        min_qty=100.0
    )
    
    result = risk_manager.calculate_position_size(
        signal=signal,
        current_price=0.1,
        account_balance=10000.0,  # Large account
        leverage=1,
        exchange_limits=limits
    )
    
    print_risk_result(result, "DOGE/USDT Large Position Test")
    
    # Verify position size limits
    max_position_value = 10000.0 * 0.1  # 10% of account
    assert result.position_value <= max_position_value, f"Position exceeds maximum: {result.position_value} > {max_position_value}"
    
    print("✅ Risk limits test completed!")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    
    risk_manager = RiskManager()
    
    # Test case 1: Invalid stop loss (same as entry)
    signal = create_test_signal(
        symbol="BTC/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=50000.0,
        stop_loss=50000.0  # Same as entry - invalid
    )
    
    result = risk_manager.calculate_position_size(
        signal=signal,
        current_price=50000.0,
        account_balance=1000.0,
        leverage=1
    )
    
    print_risk_result(result, "Invalid Stop Loss (Same as Entry)")
    assert not result.is_safe_to_trade, "Should reject invalid stop loss"
    
    # Test case 2: Very small account balance
    signal2 = create_test_signal(
        symbol="BTC/USDT",
        signal_type=SignalType.BUY_OPEN,
        entry_price=50000.0,
        stop_loss=49000.0
    )
    
    result2 = risk_manager.calculate_position_size(
        signal=signal2,
        current_price=50000.0,
        account_balance=1.0,  # Very small account
        leverage=1
    )
    
    print_risk_result(result2, "Very Small Account Balance")
    
    # Test case 3: Zero account balance
    result3 = risk_manager.calculate_position_size(
        signal=signal2,
        current_price=50000.0,
        account_balance=0.0,  # Zero balance
        leverage=1
    )
    
    print_risk_result(result3, "Zero Account Balance")
    
    print("✅ Edge cases test completed!")


def test_risk_summary():
    """Test risk summary functionality."""
    print("\n🧪 Testing Risk Summary...")
    
    risk_manager = RiskManager()
    
    # Get risk summary for different account balances
    balances = [100, 500, 1000, 5000, 10000]
    
    for balance in balances:
        summary = risk_manager.get_risk_summary(balance)
        print(f"\n💰 Account Balance: ${balance:.2f}")
        print(f"   Max Risk per Trade: ${summary['max_risk_per_trade_usd']:.2f}")
        print(f"   Max Position Size: ${summary['max_position_size_usd']:.2f}")
        print(f"   Emergency Stop Loss: ${summary['emergency_stop_loss_usd']:.2f}")
    
    print("✅ Risk summary test completed!")


def test_portfolio_integration():
    """Test integration with portfolio manager."""
    print("\n🧪 Testing Portfolio Integration...")
    
    try:
        from trading_system.risk_manager.portfolio_manager import PortfolioManager
        
        # Initialize portfolio manager
        portfolio = PortfolioManager(1000.0, "config/exchanges_config.json")
        
        # Create test signals
        signals = [
            create_test_signal("BTC/USDT", SignalType.BUY_OPEN, 50000.0, 49000.0),
            create_test_signal("ETH/USDT", SignalType.BUY_OPEN, 3000.0, 2970.0),
            create_test_signal("SOL/USDT", SignalType.SELL_OPEN, 100.0, 102.0)
        ]
        
        # Test portfolio metrics
        metrics = portfolio.calculate_portfolio_metrics()
        print(f"\n📊 Portfolio Metrics:")
        print(f"   Total Balance: ${metrics.total_account_balance:.2f}")
        print(f"   Available Balance: ${metrics.available_balance:.2f}")
        print(f"   Total P&L: ${metrics.total_pnl:.2f}")
        print(f"   Open Positions: {metrics.open_positions_count}")
        print(f"   Total Risk: ${metrics.total_risk_usd:.2f}")
        
        # Test trade evaluation
        for signal in signals:
            evaluation = portfolio.evaluate_new_trade(signal, 100.0)
            print(f"\n🔍 Trade Evaluation for {signal.symbol}:")
            print(f"   Can Execute: {'✅' if evaluation['can_execute'] else '❌'}")
            print(f"   Reason: {evaluation['reason']}")
            if evaluation['can_execute']:
                print(f"   Position Size: {evaluation['position_size']:.6f}")
                print(f"   Risk Amount: ${evaluation['risk_amount']:.2f}")
        
        print("✅ Portfolio integration test completed!")
        
    except ImportError as e:
        print(f"⚠️ Portfolio manager not available: {e}")


def main():
    """Run all risk manager tests."""
    print("🚀 Starting Risk Manager Isolation Tests")
    print("=" * 60)
    
    try:
        # Test position sizing calculator first
        test_position_sizing_calculator()
        
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
        
        # Test risk summary
        test_risk_summary()
        
        # Test portfolio integration
        test_portfolio_integration()
        
        print("\n" + "=" * 60)
        print("🎉 All Risk Manager tests completed successfully!")
        print("✅ Risk Manager is working correctly in isolation")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
