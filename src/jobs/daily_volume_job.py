"""
Daily Volume Analysis Job - Fetches and analyzes futures market volumes daily.
"""
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import json
import os
from pathlib import Path

from ..data_feeder.futures_data_feeder import FuturesDataFeeder
from ..core.futures_models import ExchangeType, VolumeMetrics, FuturesMarketRanking


class DailyVolumeJob:
    """Daily job to analyze futures market volumes across exchanges."""
    
    def __init__(self, config_path: Optional[str] = None, output_dir: str = "volume_data"):
        """
        Initialize daily volume job.
        
        Args:
            config_path: Path to exchanges configuration file
            output_dir: Directory to save volume analysis files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load exchange configuration
        self.exchanges_config = self._load_config(config_path) if config_path else {}
        
        # Initialize futures data feeder
        self.futures_feeder = FuturesDataFeeder(self.exchanges_config)
        
        # Job settings
        self.job_time = "09:00"  # Run at 9 AM daily
        self.retention_days = 30  # Keep data for 30 days
        
        logger.info(f"DailyVolumeJob initialized - will run daily at {self.job_time}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load exchange configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded exchange configuration from {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            return {}
    
    def run_volume_analysis(self) -> Dict:
        """Run the complete volume analysis."""
        logger.info("Starting daily futures volume analysis...")
        start_time = datetime.now()
        
        try:
            # Get volume metrics from all exchanges
            logger.info("Fetching volume metrics from all exchanges...")
            all_metrics = self.futures_feeder.get_all_exchanges_volume_metrics()
            
            if not all_metrics:
                logger.error("No volume metrics fetched from any exchange")
                return {}
            
            # Create market rankings
            logger.info("Creating market rankings...")
            rankings = self.futures_feeder.create_market_rankings(all_metrics)
            
            # Prepare analysis results
            analysis_results = self._prepare_analysis_results(all_metrics, rankings)
            
            # Save results
            filename = self._save_analysis_results(analysis_results)
            
            # Clean up old files
            self._cleanup_old_files()
            
            # Log summary
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Volume analysis completed in {execution_time:.2f} seconds")
            logger.info(f"Analyzed {analysis_results['total_markets']} markets across {len(all_metrics)} exchanges")
            logger.info(f"Found {analysis_results['recommended_markets']} recommended markets")
            logger.info(f"Results saved to {filename}")
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in volume analysis: {e}")
            return {}
    
    def _prepare_analysis_results(self, all_metrics: Dict[ExchangeType, List[VolumeMetrics]], 
                                rankings: List[FuturesMarketRanking]) -> Dict:
        """Prepare analysis results for saving."""
        # Calculate summary statistics
        total_volume_usd = sum(
            sum(m.volume_usd_24h for m in metrics)
            for metrics in all_metrics.values()
        )
        
        recommended_markets = [r for r in rankings if r.is_recommended]
        
        # Top markets by exchange
        top_by_exchange = {}
        for exchange, metrics in all_metrics.items():
            sorted_metrics = sorted(metrics, key=lambda x: x.volume_usd_24h, reverse=True)
            top_by_exchange[exchange.value] = [
                {
                    'symbol': m.symbol,
                    'volume_usd_24h': m.volume_usd_24h,
                    'price_change_24h': m.price_change_24h,
                    'price': m.price
                }
                for m in sorted_metrics[:10]  # Top 10 per exchange
            ]
        
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'execution_date': datetime.now().strftime('%Y-%m-%d'),
            'exchanges_analyzed': [e.value for e in all_metrics.keys()],
            'total_markets': sum(len(metrics) for metrics in all_metrics.values()),
            'recommended_markets': len(recommended_markets),
            'total_volume_usd_24h': total_volume_usd,
            
            # Summary statistics
            'summary': {
                'avg_volume_per_market': total_volume_usd / max(1, sum(len(metrics) for metrics in all_metrics.values())),
                'top_volume_market': rankings[0].symbol if rankings else None,
                'top_volume_amount': rankings[0].volume_usd_24h if rankings else 0,
                'markets_over_10m_volume': sum(1 for r in rankings if r.volume_usd_24h > 10_000_000),
                'markets_over_100m_volume': sum(1 for r in rankings if r.volume_usd_24h > 100_000_000),
            },
            
            # Top markets by exchange
            'top_markets_by_exchange': top_by_exchange,
            
            # Overall rankings (top 100)
            'market_rankings': [r.to_dict() for r in rankings[:100]],
            
            # Recommended symbols for trading
            'recommended_symbols': [r.symbol for r in recommended_markets[:50]],
            
            # Exchange-specific metrics
            'exchange_metrics': {
                exchange.value: {
                    'markets_count': len(metrics),
                    'total_volume_usd': sum(m.volume_usd_24h for m in metrics),
                    'avg_volume_usd': sum(m.volume_usd_24h for m in metrics) / max(1, len(metrics)),
                    'top_symbol': max(metrics, key=lambda x: x.volume_usd_24h).symbol if metrics else None
                }
                for exchange, metrics in all_metrics.items()
            }
        }
        
        return analysis_results
    
    def _save_analysis_results(self, results: Dict) -> str:
        """Save analysis results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"futures_volume_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Also save as latest
            latest_filename = self.output_dir / "latest_volume_analysis.json"
            with open(latest_filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Analysis results saved to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            return ""
    
    def _cleanup_old_files(self):
        """Remove analysis files older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for file_path in self.output_dir.glob("futures_volume_analysis_*.json"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logger.info(f"Removed old analysis file: {file_path}")
                    
        except Exception as e:
            logger.warning(f"Error cleaning up old files: {e}")
    
    def get_latest_analysis(self) -> Optional[Dict]:
        """Get the latest volume analysis results."""
        latest_file = self.output_dir / "latest_volume_analysis.json"
        
        if not latest_file.exists():
            logger.warning("No latest volume analysis file found")
            return None
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Error loading latest analysis: {e}")
            return None
    
    def get_recommended_symbols(self, limit: int = 50) -> List[str]:
        """Get recommended symbols from latest analysis."""
        latest_analysis = self.get_latest_analysis()
        
        if not latest_analysis:
            logger.warning("No analysis data available, using default symbols")
            return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        
        recommended = latest_analysis.get('recommended_symbols', [])[:limit]
        logger.info(f"Retrieved {len(recommended)} recommended symbols from latest analysis")
        return recommended
    
    def schedule_daily_job(self):
        """Schedule the daily volume analysis job."""
        schedule.every().day.at(self.job_time).do(self.run_volume_analysis)
        logger.info(f"Scheduled daily volume analysis job at {self.job_time}")
    
    def run_scheduler(self):
        """Run the job scheduler (blocking)."""
        logger.info("Starting job scheduler...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Job scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in job scheduler: {e}")
                time.sleep(60)  # Continue after error
    
    def run_once(self) -> Dict:
        """Run the volume analysis once (for testing/manual execution)."""
        return self.run_volume_analysis()


def main():
    """Main function to run the daily volume job."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Futures Volume Analysis Job')
    parser.add_argument('--config', help='Path to exchange configuration file')
    parser.add_argument('--output-dir', default='volume_data', help='Output directory for analysis files')
    parser.add_argument('--run-once', action='store_true', help='Run analysis once and exit')
    parser.add_argument('--schedule', action='store_true', help='Run as scheduled job')
    
    args = parser.parse_args()
    
    # Initialize job
    job = DailyVolumeJob(config_path=args.config, output_dir=args.output_dir)
    
    if args.run_once:
        # Run once and exit
        results = job.run_once()
        if results:
            print(f"✅ Analysis completed. Found {results['recommended_markets']} recommended markets.")
        else:
            print("❌ Analysis failed.")
    
    elif args.schedule:
        # Run as scheduled job
        job.schedule_daily_job()
        job.run_scheduler()
    
    else:
        print("Please specify either --run-once or --schedule")


if __name__ == "__main__":
    main()
