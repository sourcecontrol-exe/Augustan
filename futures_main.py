"""
Futures Trading System - Optimized for futures markets with volume analysis.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import sys
from pathlib import Path

from src.data_feeder.futures_data_feeder import FuturesDataFeeder
from src.jobs.daily_volume_job import DailyVolumeJob
from src.strategy_engine import StrategyEngine
from src.core.models import TradingSignal
from src.core.futures_models import ExchangeType


class FuturesTradingSystem:
    """Futures-optimized trading system with volume-based market selection."""
    
    def __init__(self, config_path: str = "config/exchanges_config.json"):
        """Initialize the futures trading system."""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize components
        self.futures_feeder = FuturesDataFeeder(self.config)
        self.volume_job = DailyVolumeJob(config_path, self.config.get('job_settings', {}).get('output_directory', 'volume_data'))
        self.strategy_engine = StrategyEngine()
        
        # Configure logging
        logger.remove()
        logger.add(sys.stderr, level="INFO")
        logger.add("logs/futures_trading_system.log", rotation="1 day", level="DEBUG")
        
        logger.info("Futures Trading System initialized")
    
    def _load_config(self) -> Dict:
        """Load system configuration."""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def run_volume_analysis(self) -> Dict:
        """Run volume analysis across all exchanges."""
        logger.info("🔍 Running futures volume analysis...")
        
        try:
            results = self.volume_job.run_volume_analysis()
            
            if results:
                self._print_volume_summary(results)
                return results
            else:
                logger.error("Volume analysis failed")
                return {}
                
        except Exception as e:
            logger.error(f"Error in volume analysis: {e}")
            return {}
    
    def _print_volume_summary(self, results: Dict):
        """Print volume analysis summary."""
        print(f"\n{'='*80}")
        print(f"FUTURES VOLUME ANALYSIS - {results['execution_date']}")
        print(f"{'='*80}")
        
        summary = results.get('summary', {})
        
        print(f"📊 Total Markets Analyzed: {results.get('total_markets', 0)}")
        print(f"🏆 Recommended Markets: {results.get('recommended_markets', 0)}")
        print(f"💰 Total 24h Volume: ${results.get('total_volume_usd_24h', 0):,.0f}")
        print(f"📈 Markets >$10M Volume: {summary.get('markets_over_10m_volume', 0)}")
        print(f"🚀 Markets >$100M Volume: {summary.get('markets_over_100m_volume', 0)}")
        
        if summary.get('top_volume_market'):
            print(f"👑 Top Volume Market: {summary['top_volume_market']} (${summary.get('top_volume_amount', 0):,.0f})")
        
        print(f"\n📋 Exchanges Analyzed:")
        for exchange, metrics in results.get('exchange_metrics', {}).items():
            print(f"  • {exchange.upper()}: {metrics['markets_count']} markets, ${metrics['total_volume_usd']:,.0f} volume")
        
        print(f"\n🎯 Top 10 Recommended Symbols:")
        recommended = results.get('recommended_symbols', [])[:10]
        for i, symbol in enumerate(recommended, 1):
            print(f"  {i:2d}. {symbol}")
        
        print(f"{'='*80}\n")
    
    def run_futures_analysis(self, symbols: Optional[List[str]] = None, timeframe: str = '1h', limit: int = 100) -> Dict:
        """
        Run complete futures trading analysis.
        
        Args:
            symbols: List of symbols to analyze (uses volume-based selection if None)
            timeframe: Timeframe for data ('1m', '5m', '1h', '4h', '1d')
            limit: Number of candles to fetch
        """
        logger.info(f"🚀 Starting futures trading analysis...")
        
        # Get symbols to analyze
        if symbols is None:
            logger.info("Getting recommended symbols from volume analysis...")
            symbols = self.volume_job.get_recommended_symbols(limit=20)  # Top 20 by volume
            
            if not symbols:
                logger.warning("No recommended symbols found, running volume analysis...")
                volume_results = self.run_volume_analysis()
                symbols = volume_results.get('recommended_symbols', [])[:20] if volume_results else []
            
            if not symbols:
                logger.error("Could not get any symbols for analysis")
                return {}
        
        logger.info(f"Analyzing {len(symbols)} futures symbols: {symbols[:5]}{'...' if len(symbols) > 5 else ''}")
        
        # For futures, we'll use the primary exchange (Binance) for now
        # In a full implementation, you'd select the best exchange per symbol
        try:
            # Convert futures symbols to spot-like format for the existing data feeder
            spot_symbols = []
            for symbol in symbols:
                # Convert BTCUSDT -> BTC/USDT format
                if 'USDT' in symbol and '/' not in symbol:
                    base = symbol.replace('USDT', '')
                    spot_symbol = f"{base}/USDT"
                    spot_symbols.append(spot_symbol)
                else:
                    spot_symbols.append(symbol)
            
            # Use the existing binance feeder for now (futures data feeder needs OHLCV method)
            from src.data_feeder import BinanceDataFeeder
            binance_feeder = BinanceDataFeeder()
            
            # Fetch market data
            logger.info("Fetching futures market data...")
            market_data_dict = binance_feeder.fetch_multiple_symbols(spot_symbols, timeframe, limit)
            
            if not market_data_dict:
                logger.error("No market data fetched")
                return {}
            
            logger.info(f"Fetched data for {len(market_data_dict)} symbols")
            
            # Run strategies
            logger.info("Running trading strategies on futures data...")
            all_signals = self.strategy_engine.get_latest_signals(market_data_dict)
            
            # Prepare results
            results = {
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'futures',
                'timeframe': timeframe,
                'symbols_analyzed': len(market_data_dict),
                'futures_symbols': symbols[:len(market_data_dict)],  # Original futures symbols
                'signals': {}
            }
            
            # Convert signals to dictionary format and map back to futures symbols
            symbol_mapping = dict(zip(spot_symbols, symbols))
            for spot_symbol, signals in all_signals.items():
                futures_symbol = symbol_mapping.get(spot_symbol, spot_symbol)
                results['signals'][futures_symbol] = [signal.to_dict() for signal in signals]
            
            logger.info(f"Futures analysis complete. Generated signals for {len(all_signals)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error in futures analysis: {e}")
            return {}
    
    def print_futures_signals(self, results: Dict):
        """Print futures trading signals in a formatted way."""
        if not results or 'signals' not in results:
            print("No futures signals generated.")
            return
        
        print(f"\n{'='*80}")
        print(f"FUTURES TRADING SIGNALS - {results['timestamp']}")
        print(f"Analysis Type: {results.get('analysis_type', 'futures').upper()}")
        print(f"Timeframe: {results['timeframe']} | Symbols Analyzed: {results['symbols_analyzed']}")
        print(f"{'='*80}")
        
        for symbol, signals in results['signals'].items():
            if not signals:
                continue
                
            print(f"\n📊 {symbol} (FUTURES)")
            print("-" * 40)
            
            for signal in signals:
                signal_emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴" if signal['signal_type'] == "SELL" else "⚪"
                print(f"{signal_emoji} {signal['strategy']} - {signal['signal_type']}")
                print(f"   Price: ${signal['price']:.4f}")
                print(f"   Confidence: {signal['confidence']:.2%}")
                print(f"   Time: {signal['timestamp']}")
                
                if signal.get('metadata'):
                    # Show key futures-relevant metadata
                    metadata = signal['metadata']
                    if 'rsi_value' in metadata:
                        print(f"   RSI: {metadata['rsi_value']:.2f}")
                    if 'macd_value' in metadata:
                        print(f"   MACD: {metadata['macd_value']:.4f}")
                print()
        
        print(f"{'='*80}\n")
    
    def save_results(self, results: Dict, filename: str = None):
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_type = results.get('analysis_type', 'futures')
            filename = f"{analysis_type}_signals_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def run_daily_volume_job(self):
        """Run the daily volume analysis job."""
        logger.info("🕘 Starting daily volume analysis job...")
        self.volume_job.schedule_daily_job()
        self.volume_job.run_scheduler()


def main():
    """Main function to run the futures trading system."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Futures Trading System')
    parser.add_argument('--config', default='config/exchanges_config.json', help='Path to configuration file')
    parser.add_argument('--volume-analysis', action='store_true', help='Run volume analysis only')
    parser.add_argument('--trading-analysis', action='store_true', help='Run trading analysis only')
    parser.add_argument('--daily-job', action='store_true', help='Run daily volume job scheduler')
    parser.add_argument('--timeframe', default='1h', help='Timeframe for analysis (1m, 5m, 1h, 4h, 1d)')
    parser.add_argument('--symbols', nargs='+', help='Specific symbols to analyze')
    
    args = parser.parse_args()
    
    # Initialize system
    system = FuturesTradingSystem(config_path=args.config)
    
    try:
        if args.volume_analysis:
            # Run volume analysis only
            print("🔍 Running futures volume analysis...")
            results = system.run_volume_analysis()
            if results:
                print("✅ Volume analysis completed successfully!")
            else:
                print("❌ Volume analysis failed.")
        
        elif args.trading_analysis:
            # Run trading analysis only
            print("📈 Running futures trading analysis...")
            results = system.run_futures_analysis(
                symbols=args.symbols,
                timeframe=args.timeframe
            )
            
            if results:
                system.print_futures_signals(results)
                system.save_results(results)
                print("✅ Trading analysis completed successfully!")
            else:
                print("❌ Trading analysis failed.")
        
        elif args.daily_job:
            # Run daily job scheduler
            print("🕘 Starting daily volume job scheduler...")
            system.run_daily_volume_job()
        
        else:
            # Run complete analysis (default)
            print("🚀 Running complete futures analysis...")
            
            # First run volume analysis
            volume_results = system.run_volume_analysis()
            
            if volume_results:
                # Then run trading analysis with recommended symbols
                trading_results = system.run_futures_analysis(timeframe=args.timeframe)
                
                if trading_results:
                    system.print_futures_signals(trading_results)
                    system.save_results(trading_results)
                    print("✅ Complete analysis finished successfully!")
                else:
                    print("⚠️  Volume analysis completed, but trading analysis failed.")
            else:
                print("❌ Analysis failed.")
                
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user.")
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"❌ Error occurred: {e}")


if __name__ == "__main__":
    main()
