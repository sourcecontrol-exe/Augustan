#!/usr/bin/env python3
"""
Example: Real-time Trading System with 1m/3m WebSocket Klines

This example demonstrates how to use the RealtimeFeeder in a trading system:
- Subscribe to 1m and 3m websocket klines
- Handle CANDLE_TICK and CANDLE_CLOSED events
- Perform real-time analysis on candle data
- Implement basic trading logic
"""
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
from loguru import logger

from trading_system.data_feeder.realtime_feeder import (
    create_realtime_feeder, 
    RealtimeEvent, 
    EventType,
    RealtimeCandle
)


class RealtimeTradingSystem:
    """
    Example trading system that uses real-time data.
    
    Features:
    - Real-time candle analysis
    - Multiple timeframe support
    - Event-driven architecture
    - Basic trading signals
    """
    
    def __init__(self, config: Dict):
        """Initialize the trading system."""
        self.config = config
        self.feeder = create_realtime_feeder(config)
        
        # Data storage
        self.candle_data: Dict[str, Dict[str, List[RealtimeCandle]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Trading state
        self.last_signals: Dict[str, Dict[str, datetime]] = defaultdict(
            lambda: defaultdict(lambda: datetime.min)
        )
        
        # Statistics
        self.event_count = 0
        self.candle_count = 0
        self.signal_count = 0
        
        # Thread safety
        self.data_lock = threading.Lock()
        
        # Add event callback
        self.feeder.add_event_callback(self.on_realtime_event)
        
        logger.info(f"RealtimeTradingSystem initialized for {config['symbol']}")
    
    def on_realtime_event(self, event: RealtimeEvent):
        """Handle real-time events from the feeder."""
        self.event_count += 1
        candle = event.data
        
        with self.data_lock:
            # Store candle data
            self.candle_data[candle.symbol][event.timeframe].append(candle)
            
            # Keep only last 100 candles per timeframe
            if len(self.candle_data[candle.symbol][event.timeframe]) > 100:
                self.candle_data[candle.symbol][event.timeframe].pop(0)
        
        if event.event_type == EventType.CANDLE_TICK:
            self.handle_candle_tick(event)
        
        elif event.event_type == EventType.CANDLE_CLOSED:
            self.handle_candle_closed(event)
    
    def handle_candle_tick(self, event: RealtimeEvent):
        """Handle CANDLE_TICK events (partial candle updates)."""
        candle = event.data
        
        # Log tick updates (less verbose)
        if self.event_count % 10 == 0:  # Log every 10th tick
            logger.debug(f"Tick: {event.timeframe} {candle.symbol} ${candle.close:.4f}")
    
    def handle_candle_closed(self, event: RealtimeEvent):
        """Handle CANDLE_CLOSED events (final candle data)."""
        self.candle_count += 1
        candle = event.data
        
        logger.info(f"✅ Candle Closed: {event.timeframe} {candle.symbol}")
        logger.info(f"   OHLC: ${candle.open:.4f}/${candle.high:.4f}/${candle.low:.4f}/${candle.close:.4f}")
        logger.info(f"   Volume: {candle.volume:.2f} | Trades: {candle.trades}")
        
        # Perform analysis on closed candle
        self.analyze_candle(event.timeframe, candle)
        
        # Generate trading signals
        self.generate_signals(event.timeframe, candle)
    
    def analyze_candle(self, timeframe: str, candle: RealtimeCandle):
        """Analyze a closed candle for patterns and indicators."""
        symbol = candle.symbol
        
        with self.data_lock:
            candles = self.candle_data[symbol][timeframe]
            
            if len(candles) < 2:
                return
            
            # Calculate basic indicators
            current_candle = candles[-1]
            prev_candle = candles[-2]
            
            # Price change
            price_change = current_candle.close - prev_candle.close
            price_change_pct = (price_change / prev_candle.close) * 100
            
            # Volume analysis
            avg_volume = sum(c.volume for c in candles[-10:]) / min(len(candles), 10)
            volume_ratio = current_candle.volume / avg_volume if avg_volume > 0 else 1.0
            
            # Log analysis
            logger.info(f"📊 Analysis ({timeframe}):")
            logger.info(f"   Price Change: {price_change_pct:+.2f}%")
            logger.info(f"   Volume Ratio: {volume_ratio:.2f}x average")
            
            # Detect patterns
            if price_change_pct > 1.0 and volume_ratio > 1.5:
                logger.warning(f"🚀 Bullish pattern detected: +{price_change_pct:.2f}% with {volume_ratio:.2f}x volume")
            
            elif price_change_pct < -1.0 and volume_ratio > 1.5:
                logger.warning(f"📉 Bearish pattern detected: {price_change_pct:.2f}% with {volume_ratio:.2f}x volume")
    
    def generate_signals(self, timeframe: str, candle: RealtimeCandle):
        """Generate trading signals based on candle analysis."""
        symbol = candle.symbol
        
        # Check cooldown period (avoid too many signals)
        cooldown_minutes = 5
        last_signal_time = self.last_signals[symbol][timeframe]
        
        if datetime.now() - last_signal_time < timedelta(minutes=cooldown_minutes):
            return
        
        with self.data_lock:
            candles = self.candle_data[symbol][timeframe]
            
            if len(candles) < 5:
                return
            
            # Simple moving average crossover
            short_ma = sum(c.close for c in candles[-3:]) / 3
            long_ma = sum(c.close for c in candles[-5:]) / 5
            
            # Generate signal
            if short_ma > long_ma * 1.001:  # 0.1% threshold
                logger.success(f"🟢 BUY Signal ({timeframe}): {symbol} @ ${candle.close:.4f}")
                logger.success(f"   Short MA: ${short_ma:.4f} | Long MA: ${long_ma:.4f}")
                self.signal_count += 1
                self.last_signals[symbol][timeframe] = datetime.now()
            
            elif short_ma < long_ma * 0.999:  # 0.1% threshold
                logger.error(f"🔴 SELL Signal ({timeframe}): {symbol} @ ${candle.close:.4f}")
                logger.error(f"   Short MA: ${short_ma:.4f} | Long MA: ${long_ma:.4f}")
                self.signal_count += 1
                self.last_signals[symbol][timeframe] = datetime.now()
    
    def start(self):
        """Start the trading system."""
        logger.info("Starting Realtime Trading System...")
        self.feeder.start()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Trading system started")
    
    def stop(self):
        """Stop the trading system."""
        logger.info("Stopping Trading System...")
        self.feeder.stop()
        logger.info("Trading system stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                # Print statistics every 60 seconds
                time.sleep(60)
                
                status = self.feeder.get_system_status()
                logger.info(f"📈 Statistics:")
                logger.info(f"   Events: {self.event_count}")
                logger.info(f"   Closed Candles: {self.candle_count}")
                logger.info(f"   Signals Generated: {self.signal_count}")
                logger.info(f"   System Running: {status['is_running']}")
                logger.info(f"   Connected: {status['exchanges']['binance']['connected']}")
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def get_statistics(self) -> Dict:
        """Get current system statistics."""
        return {
            'event_count': self.event_count,
            'candle_count': self.candle_count,
            'signal_count': self.signal_count,
            'system_status': self.feeder.get_system_status()
        }


def main():
    """Main function to run the example."""
    logger.info("Starting Realtime Trading Example")
    
    # Load configuration
    try:
        with open('config/exchanges_config.json', 'r') as f:
            config_data = json.load(f)
        
        realtime_config = config_data.get('realtime', {})
        logger.info(f"Loaded realtime config: {realtime_config}")
        
    except FileNotFoundError:
        logger.warning("Config file not found, using default config")
        realtime_config = {
            "timeframes": ["1m", "3m"],
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "max_lag_ms": 1500
        }
    
    # Create and start trading system
    trading_system = RealtimeTradingSystem(realtime_config)
    trading_system.start()
    
    try:
        # Run for 10 minutes
        logger.info("Running trading system for 10 minutes...")
        time.sleep(600)  # 10 minutes
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    
    finally:
        # Stop the system
        trading_system.stop()
        
        # Print final statistics
        stats = trading_system.get_statistics()
        logger.info("Final Statistics:")
        logger.info(f"   Total Events: {stats['event_count']}")
        logger.info(f"   Closed Candles: {stats['candle_count']}")
        logger.info(f"   Signals Generated: {stats['signal_count']}")
        
        logger.info("Example completed")


if __name__ == "__main__":
    main()
