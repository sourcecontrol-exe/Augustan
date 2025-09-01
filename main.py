"""
Main application for the trading system.
Fetches data from Binance and runs trading strategies.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List
from loguru import logger
import sys

from src.data_feeder import BinanceDataFeeder
from src.strategy_engine import StrategyEngine
from src.core.models import TradingSignal


class TradingSystem:
    """Main trading system orchestrator."""
    
    def __init__(self):
        """Initialize the trading system."""
        self.data_feeder = BinanceDataFeeder()
        self.strategy_engine = StrategyEngine()
        
        # Configure logging
        logger.remove()
        logger.add(sys.stderr, level="INFO")
        logger.add("logs/trading_system.log", rotation="1 day", level="DEBUG")
        
        logger.info("Trading System initialized")
    
    def run_analysis(self, symbols: List[str] = None, timeframe: str = '1h', limit: int = 100) -> Dict:
        """
        Run complete analysis for given symbols.
        
        Args:
            symbols: List of symbols to analyze
            timeframe: Timeframe for data ('1m', '5m', '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            Dictionary containing all signals and analysis results
        """
        logger.info(f"Starting analysis for timeframe: {timeframe}, limit: {limit}")
        
        # Fetch market data
        logger.info("Fetching market data from Binance...")
        market_data_dict = self.data_feeder.fetch_multiple_symbols(symbols, timeframe, limit)
        
        if not market_data_dict:
            logger.error("No market data fetched")
            return {}
        
        logger.info(f"Fetched data for {len(market_data_dict)} symbols")
        
        # Run strategies
        logger.info("Running trading strategies...")
        all_signals = self.strategy_engine.get_latest_signals(market_data_dict)
        
        # Prepare results
        results = {
            'timestamp': datetime.now().isoformat(),
            'timeframe': timeframe,
            'symbols_analyzed': len(market_data_dict),
            'signals': {}
        }
        
        # Convert signals to dictionary format
        for symbol, signals in all_signals.items():
            results['signals'][symbol] = [signal.to_dict() for signal in signals]
        
        logger.info(f"Analysis complete. Generated signals for {len(all_signals)} symbols")
        return results
    
    def print_signals(self, results: Dict):
        """Print signals in a formatted way."""
        if not results or 'signals' not in results:
            print("No signals generated.")
            return
        
        print(f"\n{'='*80}")
        print(f"TRADING SIGNALS ANALYSIS - {results['timestamp']}")
        print(f"Timeframe: {results['timeframe']} | Symbols Analyzed: {results['symbols_analyzed']}")
        print(f"{'='*80}")
        
        for symbol, signals in results['signals'].items():
            if not signals:
                continue
                
            print(f"\n📊 {symbol}")
            print("-" * 40)
            
            for signal in signals:
                signal_emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴" if signal['signal_type'] == "SELL" else "⚪"
                print(f"{signal_emoji} {signal['strategy']} - {signal['signal_type']}")
                print(f"   Price: ${signal['price']:.4f}")
                print(f"   Confidence: {signal['confidence']:.2%}")
                print(f"   Time: {signal['timestamp']}")
                
                if signal.get('metadata'):
                    print(f"   Details: {signal['metadata']}")
                print()
        
        print(f"{'='*80}\n")
    
    def save_results(self, results: Dict, filename: str = None):
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"signals_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")


def main():
    """Main function to run the trading system."""
    # Initialize trading system
    system = TradingSystem()
    
    # Define symbols to analyze (you can modify this list)
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT',
        'SOL/USDT', 'XRP/USDT', 'DOT/USDT', 'AVAX/USDT'
    ]
    
    try:
        # Run analysis
        print("🚀 Starting Crypto Trading Analysis...")
        results = system.run_analysis(symbols=symbols, timeframe='1h', limit=100)
        
        if results:
            # Print signals
            system.print_signals(results)
            
            # Save results
            system.save_results(results)
            
            print("✅ Analysis completed successfully!")
        else:
            print("❌ No results generated. Check your internet connection and try again.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user.")
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"❌ Error occurred: {e}")


if __name__ == "__main__":
    main()
