#!/usr/bin/env python3
"""
Test Real-Time Fix - Demonstrates the bottleneck resolution

Before Fix: Timestamps stuck at same minute (e.g., 00:03:00)
After Fix: Real-time timestamps updating every second
"""
import time
from datetime import datetime
from trading_system.data_feeder.realtime_feeder import BinanceWebsocketFeeder

def test_realtime_updates():
    """Test that we get real-time updates with proper timestamps."""
    print("🧪 Testing Real-Time WebSocket Updates")
    print("=" * 50)
    
    # Track updates
    update_count = 0
    price_changes = []
    timestamps = []
    
    def on_price_update(symbol: str, candle):
        nonlocal update_count, price_changes, timestamps
        update_count += 1
        
        current_time = candle.timestamp.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
        price = candle.close
        
        timestamps.append(current_time)
        price_changes.append(price)
        
        print(f"  📊 {symbol}: ${price:.4f} at {current_time}")
        
        # Stop after 10 updates
        if update_count >= 10:
            return
    
    # Initialize feeder with ticker stream for real-time updates
    feeder = BinanceWebsocketFeeder(['BTC/USDT'], stream_type='ticker')
    feeder.add_callback(on_price_update)
    
    print("🚀 Starting WebSocket with ticker stream...")
    feeder.start()
    
    # Wait for updates
    start_time = time.time()
    while update_count < 10 and (time.time() - start_time) < 30:
        time.sleep(0.1)
    
    # Stop the feeder immediately to prevent more callbacks
    feeder.stop()
    feeder.cleanup()
    
    # Analysis
    print("\n📊 RESULTS ANALYSIS:")
    print("=" * 30)
    
    if update_count > 0:
        print(f"✅ Updates received: {update_count}")
        print(f"✅ Time range: {timestamps[0]} to {timestamps[-1]}")
        
        # Check if timestamps are updating (not stuck)
        unique_timestamps = len(set(timestamps))
        if unique_timestamps > 1:
            print(f"✅ Timestamps updating: {unique_timestamps} unique timestamps")
            print("🎉 BOTTLENECK RESOLVED - Real-time updates working!")
        else:
            print(f"❌ Timestamps stuck: Only 1 unique timestamp")
            print("⚠️ Bottleneck still exists")
        
        # Check price variations
        unique_prices = len(set(price_changes))
        if unique_prices > 1:
            min_price = min(price_changes)
            max_price = max(price_changes)
            print(f"✅ Price movement: ${min_price:.4f} to ${max_price:.4f}")
        else:
            print(f"📊 Price stable: ${price_changes[0]:.4f}")
        
    else:
        print("❌ No updates received - connection issue")
    
    print(f"\n⏱️ Test completed in {time.time() - start_time:.1f} seconds")

if __name__ == "__main__":
    test_realtime_updates()
