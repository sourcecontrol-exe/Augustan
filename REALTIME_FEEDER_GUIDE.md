# Realtime Feeder Guide

## Overview

The RealtimeFeeder provides real-time market data streams from Binance WebSocket API with support for multiple timeframes (1m, 3m, etc.). It implements an event-driven architecture that emits `CANDLE_TICK` and `CANDLE_CLOSED` events for real-time trading applications.

## Features

- **Multiple Timeframes**: Subscribe to 1m, 3m, 5m, 15m, 1h, 4h, 1d timeframes
- **Event-Driven**: Emits `CANDLE_TICK` and `CANDLE_CLOSED` events
- **Duplicate Prevention**: Prevents duplicate `CANDLE_CLOSED` events for the same candle
- **Automatic Reconnection**: Handles WebSocket disconnections automatically
- **Thread-Safe**: Safe for multi-threaded applications
- **Configurable**: Supports configuration via JSON files

## Configuration

### Basic Configuration

Add the following to your `config/exchanges_config.json`:

```json
{
  "realtime": {
    "timeframes": ["1m", "3m"],
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "max_lag_ms": 1500
  }
}
```

### Configuration Parameters

- `timeframes`: List of timeframes to subscribe to (e.g., ["1m", "3m", "5m"])
- `symbol`: Trading symbol (e.g., "BTCUSDT", "ETHUSDT")
- `exchange`: Exchange name (currently supports "binance")
- `max_lag_ms`: Maximum acceptable lag in milliseconds (default: 1500)

## Usage

### Basic Usage

```python
from trading_system.data_feeder.realtime_feeder import create_realtime_feeder, EventType

# Configuration
config = {
    "timeframes": ["1m", "3m"],
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "max_lag_ms": 1500
}

# Create feeder
feeder = create_realtime_feeder(config)

# Event callback
def on_event(event):
    if event.event_type == EventType.CANDLE_TICK:
        print(f"Tick: {event.timeframe} - ${event.data.close}")
    elif event.event_type == EventType.CANDLE_CLOSED:
        print(f"Closed: {event.timeframe} - OHLC: ${event.data.open}/${event.data.high}/${event.data.low}/${event.data.close}")

# Add callback and start
feeder.add_event_callback(on_event)
feeder.start()
```

### Advanced Usage with Trading System

```python
import threading
from trading_system.data_feeder.realtime_feeder import (
    create_realtime_feeder, 
    RealtimeEvent, 
    EventType
)

class TradingSystem:
    def __init__(self, config):
        self.feeder = create_realtime_feeder(config)
        self.feeder.add_event_callback(self.on_event)
        
    def on_event(self, event: RealtimeEvent):
        if event.event_type == EventType.CANDLE_CLOSED:
            # Perform analysis on closed candle
            self.analyze_candle(event.timeframe, event.data)
            
    def analyze_candle(self, timeframe: str, candle):
        # Your trading logic here
        pass
        
    def start(self):
        self.feeder.start()
        
    def stop(self):
        self.feeder.stop()

# Usage
config = {
    "timeframes": ["1m", "3m"],
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "max_lag_ms": 1500
}

system = TradingSystem(config)
system.start()
```

## Event Types

### CANDLE_TICK

Emitted for every kline update (partial candle data).

```python
@dataclass
class RealtimeEvent:
    event_type: EventType.CANDLE_TICK
    timeframe: str  # e.g., "1m", "3m"
    data: RealtimeCandle
    timestamp: datetime
```

### CANDLE_CLOSED

Emitted exactly when the exchange flags `isFinal=true` for a kline.

```python
@dataclass
class RealtimeEvent:
    event_type: EventType.CANDLE_CLOSED
    timeframe: str  # e.g., "1m", "3m"
    data: RealtimeCandle
    timestamp: datetime
```

## Data Structures

### RealtimeCandle

```python
@dataclass
class RealtimeCandle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: int
    is_final: bool  # True when candle is complete
    timeframe: str  # e.g., "1m", "3m"
```

## API Reference

### RealtimeFeeder

#### Methods

- `add_event_callback(callback)`: Add event callback function
- `start()`: Start the WebSocket connection
- `stop()`: Stop the WebSocket connection
- `get_current_price(symbol)`: Get current price for symbol
- `get_recent_data(symbol, timeframe, count)`: Get recent candlestick data
- `get_system_status()`: Get connection and system status

#### Properties

- `config`: Configuration object
- `is_running`: Whether the feeder is running

### BinanceWebsocketFeeder

Lower-level class that handles WebSocket connections to Binance.

## Examples

### Example 1: Simple Price Monitor

```python
from trading_system.data_feeder.realtime_feeder import create_realtime_feeder, EventType

def price_monitor():
    config = {
        "timeframes": ["1m"],
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "max_lag_ms": 1500
    }
    
    feeder = create_realtime_feeder(config)
    
    def on_event(event):
        if event.event_type == EventType.CANDLE_CLOSED:
            print(f"BTC Price: ${event.data.close:.2f}")
    
    feeder.add_event_callback(on_event)
    feeder.start()
    
    return feeder
```

### Example 2: Multi-Timeframe Analysis

```python
def multi_timeframe_analysis():
    config = {
        "timeframes": ["1m", "3m", "5m"],
        "symbol": "ETHUSDT",
        "exchange": "binance",
        "max_lag_ms": 1500
    }
    
    feeder = create_realtime_feeder(config)
    
    def on_event(event):
        if event.event_type == EventType.CANDLE_CLOSED:
            candle = event.data
            print(f"{event.timeframe} - ETH: ${candle.close:.2f} "
                  f"(Vol: {candle.volume:.2f})")
    
    feeder.add_event_callback(on_event)
    feeder.start()
    
    return feeder
```

### Example 3: Trading Signal Generator

```python
import pandas as pd
from collections import deque

class SignalGenerator:
    def __init__(self, config):
        self.feeder = create_realtime_feeder(config)
        self.candles = deque(maxlen=100)
        self.feeder.add_event_callback(self.on_event)
        
    def on_event(self, event):
        if event.event_type == EventType.CANDLE_CLOSED:
            self.candles.append(event.data)
            self.generate_signals(event.timeframe)
    
    def generate_signals(self, timeframe):
        if len(self.candles) < 20:
            return
            
        # Calculate moving averages
        closes = [c.close for c in self.candles]
        ma_short = sum(closes[-5:]) / 5
        ma_long = sum(closes[-20:]) / 20
        
        if ma_short > ma_long:
            print(f"BUY Signal ({timeframe}): MA crossover")
        elif ma_short < ma_long:
            print(f"SELL Signal ({timeframe}): MA crossover")
    
    def start(self):
        self.feeder.start()
    
    def stop(self):
        self.feeder.stop()
```

## Testing

### Run Basic Test

```bash
python test_realtime_feeder.py
```

### Run Trading Example

```bash
python examples/realtime_trading_example.py
```

## Error Handling

The feeder includes automatic error handling:

- **WebSocket Disconnections**: Automatic reconnection with exponential backoff
- **Rate Limiting**: Built-in rate limiting to respect exchange limits
- **Invalid Data**: Graceful handling of malformed WebSocket messages
- **Network Issues**: Retry logic for network connectivity problems

## Performance Considerations

- **Memory Usage**: Candle data is limited to 1000 candles per timeframe
- **CPU Usage**: Event processing is asynchronous and non-blocking
- **Network**: WebSocket connections are optimized for low latency
- **Threading**: Thread-safe design for concurrent access

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check internet connectivity
   - Verify API credentials (if using authenticated endpoints)
   - Check firewall settings

2. **No Events Received**
   - Verify symbol is valid and trading
   - Check timeframe format (must be valid Binance timeframe)
   - Ensure callback function is properly registered

3. **High Latency**
   - Check `max_lag_ms` setting
   - Monitor network connection quality
   - Consider reducing number of timeframes

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Always handle exceptions** in your event callbacks
2. **Use thread-safe data structures** when sharing data between threads
3. **Implement proper cleanup** by calling `stop()` when done
4. **Monitor system status** regularly using `get_system_status()`
5. **Test with paper trading** before using real funds

## Integration with Trading System

The RealtimeFeeder integrates seamlessly with the existing trading system:

- **Signal Generation**: Use closed candles for technical analysis
- **Risk Management**: Real-time price monitoring for stop-losses
- **Portfolio Management**: Live position tracking
- **Backtesting**: Historical data collection for strategy validation
