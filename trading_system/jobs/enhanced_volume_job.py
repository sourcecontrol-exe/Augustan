"""
Enhanced Volume Analysis Job with Position Sizing Integration
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from pathlib import Path

from .daily_volume_job import DailyVolumeJob
from ..data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
from ..core.position_sizing import PositionSizingCalculator, RiskManagementConfig
from ..core.futures_models import ExchangeType


class EnhancedVolumeJob(DailyVolumeJob):
    """Enhanced volume analysis with position sizing and risk management."""
    
    def __init__(self, config_path: Optional[str] = None, output_dir: str = "volume_data",
                 risk_config: Optional[RiskManagementConfig] = None):
        """Initialize enhanced volume job."""
        super().__init__(config_path, output_dir)
        
        # Initialize position sizing components
        self.risk_config = risk_config or RiskManagementConfig()
        self.position_calculator = PositionSizingCalculator(self.risk_config)
        self.limits_fetcher = ExchangeLimitsFetcher(self.exchanges_config)
        
        logger.info(f"EnhancedVolumeJob initialized with budget: ${self.risk_config.max_budget}")
    
    def run_enhanced_volume_analysis(self) -> Dict:
        """Run enhanced volume analysis with position sizing."""
        logger.info("Starting enhanced futures volume analysis with position sizing...")
        start_time = datetime.now()
        
        try:
            # Step 1: Get volume metrics from all exchanges (from parent class)
            logger.info("Fetching volume metrics from all exchanges...")
            all_metrics = self.futures_feeder.get_all_exchanges_volume_metrics()
            
            if not all_metrics:
                logger.error("No volume metrics fetched from any exchange")
                return {}
            
            # Step 2: Create market rankings (from parent class)
            logger.info("Creating market rankings...")
            rankings = self.futures_feeder.create_market_rankings(all_metrics)
            
            # Step 3: Get top symbols for position sizing analysis
            logger.info("Selecting top symbols for position sizing analysis...")
            top_symbols = [r.symbol for r in rankings if r.is_recommended][:100]  # Top 100 for analysis
            
            # Step 4: Fetch exchange limits and current prices
            logger.info("Fetching exchange limits and current prices...")
            symbol_data = self.limits_fetcher.create_symbol_data_for_position_sizing(
                top_symbols, ExchangeType.BINANCE
            )
            
            if not symbol_data:
                logger.error("No symbol data available for position sizing")
                return super()._prepare_analysis_results(all_metrics, rankings)
            
            # Step 5: Run position sizing analysis
            logger.info("Running position sizing analysis...")
            position_results = self.position_calculator.filter_tradeable_symbols(
                symbol_data, self.risk_config
            )
            
            # Step 6: Prepare enhanced results
            enhanced_results = self._prepare_enhanced_analysis_results(
                all_metrics, rankings, position_results
            )
            
            # Step 7: Save results
            filename = self._save_enhanced_analysis_results(enhanced_results)
            
            # Step 8: Clean up old files
            self._cleanup_old_files()
            
            # Log summary
            execution_time = (datetime.now() - start_time).total_seconds()
            tradeable_count = sum(1 for r in position_results if r.is_tradeable)
            
            logger.info(f"Enhanced volume analysis completed in {execution_time:.2f} seconds")
            logger.info(f"Analyzed {len(position_results)} symbols for position sizing")
            logger.info(f"Found {tradeable_count} tradeable symbols within budget")
            logger.info(f"Results saved to {filename}")
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in enhanced volume analysis: {e}")
            return {}
    
    def _prepare_enhanced_analysis_results(self, all_metrics: Dict, rankings: List, 
                                         position_results: List) -> Dict:
        """Prepare enhanced analysis results with position sizing data."""
        # Get basic results from parent class
        basic_results = super()._prepare_analysis_results(all_metrics, rankings)
        
        # Add position sizing analysis
        tradeable_symbols = [r for r in position_results if r.is_tradeable]
        non_tradeable_symbols = [r for r in position_results if not r.is_tradeable]
        
        # Calculate aggregated statistics
        total_required_margin = sum(r.required_margin for r in tradeable_symbols)
        avg_safety_ratio = sum(r.safety_ratio for r in tradeable_symbols) / max(1, len(tradeable_symbols))
        
        # Group rejection reasons
        rejection_reasons = {}
        for result in non_tradeable_symbols:
            reason = result.rejection_reason or "Unknown"
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        # Enhanced results
        enhanced_results = basic_results.copy()
        enhanced_results.update({
            'position_sizing_analysis': {
                'total_symbols_analyzed': len(position_results),
                'tradeable_symbols_count': len(tradeable_symbols),
                'non_tradeable_symbols_count': len(non_tradeable_symbols),
                'total_required_margin': total_required_margin,
                'available_budget': self.risk_config.max_budget,
                'budget_utilization': (total_required_margin / self.risk_config.max_budget) * 100,
                'avg_safety_ratio': avg_safety_ratio,
                'min_safety_ratio_required': self.risk_config.min_safety_ratio,
            },
            
            'risk_management_config': self.risk_config.to_dict(),
            
            'tradeable_symbols': [r.to_dict() for r in tradeable_symbols[:50]],  # Top 50
            
            'rejection_analysis': {
                'rejection_reasons': rejection_reasons,
                'most_common_rejection': max(rejection_reasons.items(), key=lambda x: x[1])[0] if rejection_reasons else None,
                'rejection_examples': [
                    {
                        'symbol': r.symbol,
                        'reason': r.rejection_reason,
                        'min_feasible_notional': r.min_feasible_notional
                    }
                    for r in non_tradeable_symbols[:10]  # First 10 examples
                ]
            },
            
            'top_tradeable_by_safety': [
                {
                    'symbol': r.symbol,
                    'safety_ratio': r.safety_ratio,
                    'required_margin': r.required_margin,
                    'position_size_usdt': r.position_size_usdt,
                    'risk_amount': r.risk_amount
                }
                for r in tradeable_symbols[:20]  # Top 20 by safety ratio
            ]
        })
        
        return enhanced_results
    
    def _save_enhanced_analysis_results(self, results: Dict) -> str:
        """Save enhanced analysis results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"enhanced_volume_analysis_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Also save as latest
            latest_filename = self.output_dir / "latest_enhanced_analysis.json"
            with open(latest_filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Enhanced analysis results saved to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error saving enhanced analysis results: {e}")
            return ""
    
    def get_tradeable_symbols(self, limit: int = 50) -> List[str]:
        """Get list of tradeable symbols from latest enhanced analysis."""
        latest_file = self.output_dir / "latest_enhanced_analysis.json"
        
        if not latest_file.exists():
            logger.warning("No enhanced analysis file found, running analysis...")
            results = self.run_enhanced_volume_analysis()
            if not results:
                return []
        else:
            try:
                with open(latest_file, 'r') as f:
                    results = json.load(f)
            except Exception as e:
                logger.error(f"Error loading enhanced analysis: {e}")
                return []
        
        tradeable_symbols = results.get('tradeable_symbols', [])
        symbols = [item['symbol'] for item in tradeable_symbols[:limit]]
        
        logger.info(f"Retrieved {len(symbols)} tradeable symbols from enhanced analysis")
        return symbols
    
    def get_position_sizing_for_symbol(self, symbol: str) -> Optional[Dict]:
        """Get position sizing analysis for a specific symbol."""
        latest_file = self.output_dir / "latest_enhanced_analysis.json"
        
        if not latest_file.exists():
            logger.warning("No enhanced analysis file found")
            return None
        
        try:
            with open(latest_file, 'r') as f:
                results = json.load(f)
            
            tradeable_symbols = results.get('tradeable_symbols', [])
            for item in tradeable_symbols:
                if item['symbol'] == symbol:
                    return item
            
            logger.info(f"Symbol {symbol} not found in tradeable symbols")
            return None
            
        except Exception as e:
            logger.error(f"Error loading position sizing data: {e}")
            return None
    
    def print_enhanced_summary(self, results: Dict):
        """Print enhanced analysis summary."""
        if not results:
            print("No enhanced analysis results available.")
            return
        
        print(f"\n{'='*80}")
        print(f"ENHANCED FUTURES VOLUME ANALYSIS - {results['execution_date']}")
        print(f"{'='*80}")
        
        # Basic volume stats
        print(f"📊 Volume Analysis:")
        print(f"   • Total Markets: {results.get('total_markets', 0)}")
        print(f"   • Total Volume: ${results.get('total_volume_usd_24h', 0):,.0f}")
        print(f"   • Exchanges: {', '.join(results.get('exchanges_analyzed', []))}")
        
        # Position sizing stats
        pos_analysis = results.get('position_sizing_analysis', {})
        print(f"\n💰 Position Sizing Analysis:")
        print(f"   • Budget: ${pos_analysis.get('available_budget', 0):.2f}")
        print(f"   • Symbols Analyzed: {pos_analysis.get('total_symbols_analyzed', 0)}")
        print(f"   • Tradeable Symbols: {pos_analysis.get('tradeable_symbols_count', 0)}")
        print(f"   • Non-Tradeable: {pos_analysis.get('non_tradeable_symbols_count', 0)}")
        print(f"   • Budget Utilization: {pos_analysis.get('budget_utilization', 0):.1f}%")
        print(f"   • Avg Safety Ratio: {pos_analysis.get('avg_safety_ratio', 0):.2f}")
        
        # Top tradeable symbols
        top_tradeable = results.get('top_tradeable_by_safety', [])[:10]
        if top_tradeable:
            print(f"\n🎯 Top 10 Tradeable Symbols (by Safety Ratio):")
            for i, item in enumerate(top_tradeable, 1):
                print(f"   {i:2d}. {item['symbol']:<15} | Safety: {item['safety_ratio']:.2f} | "
                      f"Margin: ${item['required_margin']:.2f} | Risk: ${item['risk_amount']:.2f}")
        
        # Rejection analysis
        rejection_analysis = results.get('rejection_analysis', {})
        rejection_reasons = rejection_analysis.get('rejection_reasons', {})
        if rejection_reasons:
            print(f"\n❌ Top Rejection Reasons:")
            sorted_reasons = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:5]:
                print(f"   • {reason}: {count} symbols")
        
        print(f"{'='*80}\n")
