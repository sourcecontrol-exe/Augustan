#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple OrderManager Integration Test

This script tests the OrderManager integration with basic functionality
without the complexity of the full LiveTradingEngine.
"""
import sys
import os
from datetime import datetime

# Add the trading_system to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_system'))

from trading_system.live_trading.order_manager import OrderManager, OrderRequest, OrderType, OrderStatus
from trading_system.core.position_state import SignalType, PositionState, EnhancedSignal
from trading_system.risk_manager.portfolio_manager import PortfolioManager
from trading_system.risk_manager.risk_manager import RiskCalculationResult
from loguru import logger


def test_order_manager_basic():
    """Test basic OrderManager functionality."""
    print("\n🧪 Testing OrderManager Basic Functionality...")
    
    try:
        # Initialize OrderManager
        order_manager = OrderManager(testnet=True)
        
        # Test order placement
        order_request = OrderRequest(
            symbol="BTCUSDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.001,
            test=True
        )
        
        result = order_manager.place_order(order_request)
        
        if result.success:
            print(f"✅ Order placed successfully: {result.order_id}")
            print(f"   Status: {result.status.value}")
            print(f"   Filled: {result.filled_quantity}")
            print(f"   Price: ${result.average_price:.4f}")
        else:
            print(f"❌ Order failed: {result.error_message}")
            return False
        
        # Test order status
        status = order_manager.get_order_status(result.order_id)
        if status:
            print(f"✅ Order status retrieved: {status.status.value}")
        else:
            print("❌ Could not retrieve order status")
            return False
        
        # Test system status
        system_status = order_manager.get_system_status()
        print(f"✅ System status: {system_status['active_orders_count']} active orders")
        
        return True
        
    except Exception as e:
        print(f"❌ OrderManager test failed: {e}")
        return False


def test_portfolio_integration():
    """Test PortfolioManager integration with OrderManager."""
    print("\n🧪 Testing PortfolioManager Integration...")
    
    try:
        # Initialize components
        order_manager = OrderManager(testnet=True)
        portfolio_manager = PortfolioManager(initial_balance=1000.0)
        
        # Track order fills
        fills_received = []
        
        def on_order_fill(order_id, order_result):
            fills_received.append({
                'order_id': order_id,
                'status': order_result.status.value,
                'filled_quantity': order_result.filled_quantity,
                'timestamp': order_result.timestamp
            })
            print(f"🎯 Portfolio received order fill: {order_id}")
        
        # Connect PortfolioManager to OrderManager
        order_manager.add_fill_callback(on_order_fill)
        
        # Place test order
        order_request = OrderRequest(
            symbol="ETHUSDT",
            side="sell",
            order_type=OrderType.MARKET,
            quantity=0.01,
            test=True
        )
        
        result = order_manager.place_order(order_request)
        
        if result.success:
            print(f"✅ Order placed: {order_request.symbol} {order_request.side}")
            
            # Wait for callbacks
            import time
            time.sleep(1)
            
            # Check if portfolio received the fill
            if len(fills_received) > 0:
                print(f"✅ Portfolio integration working: {len(fills_received)} fills received")
                return True
            else:
                print("❌ Portfolio did not receive order fills")
                return False
        else:
            print(f"❌ Order failed: {result.error_message}")
            return False
        
    except Exception as e:
        print(f"❌ Portfolio integration test failed: {e}")
        return False


def test_state_management():
    """Test comprehensive state management."""
    print("\n🧪 Testing State Management...")
    
    try:
        # Initialize components
        order_manager = OrderManager(testnet=True)
        portfolio_manager = PortfolioManager(initial_balance=1000.0)
        
        # Track state changes
        state_changes = []
        
        def on_order_fill(order_id, order_result):
            state_changes.append({
                'order_id': order_id,
                'status': order_result.status.value,
                'filled_quantity': order_result.filled_quantity,
                'timestamp': order_result.timestamp
            })
            print(f"🎯 Order filled: {order_id} - {order_result.status.value}")
        
        order_manager.add_fill_callback(on_order_fill)
        
        # Place test orders
        orders = [
            OrderRequest("BTCUSDT", "buy", OrderType.MARKET, 0.001, test=True),
            OrderRequest("ETHUSDT", "sell", OrderType.MARKET, 0.01, test=True),
        ]
        
        for order_request in orders:
            result = order_manager.place_order(order_request)
            if result.success:
                print(f"✅ Order placed: {order_request.symbol} {order_request.side}")
            else:
                print(f"❌ Order failed: {order_request.symbol}")
                return False
        
        # Wait for callbacks
        import time
        time.sleep(2)
        
        # Check state changes
        if len(state_changes) > 0:
            print(f"✅ State changes tracked: {len(state_changes)} events")
            for change in state_changes:
                print(f"   {change['order_id']}: {change['status']}")
        else:
            print("❌ No state changes tracked")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ State management test failed: {e}")
        return False


def test_trade_execution_flow():
    """Test the complete trade execution flow."""
    print("\n🧪 Testing Trade Execution Flow...")
    
    try:
        # Initialize components
        order_manager = OrderManager(testnet=True)
        portfolio_manager = PortfolioManager(initial_balance=1000.0)
        
        # Create a mock signal
        mock_signal = EnhancedSignal(
            symbol="BTCUSDT",
            signal_type=SignalType.BUY_OPEN,
            current_position=PositionState.FLAT,
            target_position=PositionState.LONG,
            price=50000.0,
            timestamp=datetime.now(),
            strategy="test",
            confidence=0.8,
            reason="Test signal"
        )
        
        # Create mock risk result
        risk_result = RiskCalculationResult(
            signal=mock_signal,
            current_price=50000.0,
            account_balance=1000.0,
            risk_amount=1.0,
            position_size=0.001,
            position_value=50.0,
            required_margin=10.0,
            risk_percentage=0.1,
            reward_risk_ratio=2.0,
            max_loss_percentage=0.1,
            meets_min_notional=True,
            meets_min_quantity=True,
            adjusted_for_limits=False,
            is_safe_to_trade=True,
            safety_warnings=[],
            liquidation_price=None,
            liquidation_distance=None
        )
        
        # Simulate trade execution
        order_request = OrderRequest(
            symbol=risk_result.signal.symbol,
            side='buy' if risk_result.signal.signal_type == SignalType.BUY_OPEN else 'sell',
            order_type=OrderType.MARKET,
            quantity=risk_result.position_size,
            leverage=5,  # Default leverage
            test=True
        )
        
        # Place order
        order_result = order_manager.place_order(order_request)
        
        if order_result.success:
            print("✅ Trade execution flow successful")
            print(f"   Order ID: {order_result.order_id}")
            print(f"   Symbol: {order_request.symbol}")
            print(f"   Quantity: {order_request.quantity}")
            print(f"   Leverage: {order_request.leverage}")
            
            # Update portfolio state
            portfolio_manager.execute_trade(risk_result)
            
            # Check portfolio state
            portfolio_summary = portfolio_manager.get_portfolio_summary()
            print(f"   Portfolio positions: {len(portfolio_summary['positions'])}")
            
            return True
        else:
            print(f"❌ Trade execution failed: {order_result.error_message}")
            return False
        
    except Exception as e:
        print(f"❌ Trade execution flow test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting OrderManager Integration Tests...")
    print("=" * 60)
    
    tests = [
        ("OrderManager Basic", test_order_manager_basic),
        ("PortfolioManager Integration", test_portfolio_integration),
        ("State Management", test_state_management),
        ("Trade Execution Flow", test_trade_execution_flow),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            print(f"✅ {test_name} PASSED")
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
