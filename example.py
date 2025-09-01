"""
Simple example demonstrating the trading system functionality.
"""
from src.data_feeder import BinanceDataFeeder
from src.strategy_engine import StrategyEngine, RSIStrategy, MACDStrategy
from src.core.models import StrategyType

def simple_example():
    """Simple example of fetching data and generating signals."""
    print("🚀 Simple Trading System Example\n")
    
    # Initialize components
    print("Initializing components...")
    data_feeder = BinanceDataFeeder()
    strategy_engine = StrategyEngine()
    
    # Test with a single symbol
    symbol = 'BTC/USDT'
    print(f"Fetching data for {symbol}...")
    
    # Fetch market data
    market_data = data_feeder.fetch_ohlcv(symbol, timeframe='1h', limit=50)
    
    if not market_data:
        print("❌ Failed to fetch market data")
        return
    
    print(f"✅ Fetched {len(market_data)} candles")
    print(f"Latest price: ${market_data[-1].close:.2f}")
    
    # Run RSI strategy
    print("\n📈 Running RSI Strategy...")
    rsi_signals = strategy_engine.run_single_strategy(StrategyType.RSI, market_data)
    
    if rsi_signals:
        signal = rsi_signals[0]
        print(f"RSI Signal: {signal.signal_type.value}")
        print(f"Confidence: {signal.confidence:.2%}")
        print(f"RSI Value: {signal.metadata.get('rsi_value', 'N/A'):.2f}")
    else:
        print("No RSI signals generated")
    
    # Run MACD strategy
    print("\n📊 Running MACD Strategy...")
    macd_signals = strategy_engine.run_single_strategy(StrategyType.MACD, market_data)
    
    if macd_signals:
        signal = macd_signals[0]
        print(f"MACD Signal: {signal.signal_type.value}")
        print(f"Confidence: {signal.confidence:.2%}")
        print(f"MACD Value: {signal.metadata.get('macd_value', 'N/A'):.4f}")
    else:
        print("No MACD signals generated")
    
    print("\n✅ Example completed!")

if __name__ == "__main__":
    simple_example()
