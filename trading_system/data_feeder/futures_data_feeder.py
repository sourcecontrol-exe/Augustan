"""
Futures Data Feeder - Fetches futures market data and volume metrics from multiple exchanges.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.models import MarketData
from ..core.futures_models import (
    FuturesMarketInfo, VolumeMetrics, FuturesMarketRanking, 
    ExchangeType
)


class FuturesDataFeeder:
    """Fetches futures market data from multiple exchanges."""
    
    def __init__(self, exchanges_config: Optional[Dict] = None):
        """Initialize futures data feeder with multiple exchanges."""
        self.exchanges = {}
        self.supported_exchanges = [
            ExchangeType.BINANCE,
            ExchangeType.BYBIT,
            ExchangeType.OKX,
            ExchangeType.BITGET,
            ExchangeType.GATE
        ]
        
        # Initialize exchanges
        self._init_exchanges(exchanges_config or {})
        
        # Volume thresholds for filtering
        self.min_volume_usd_24h = 1_000_000  # $1M minimum daily volume
        self.min_volume_rank = 200  # Top 200 by volume
        
        logger.info(f"FuturesDataFeeder initialized with {len(self.exchanges)} exchanges")
    
    def _init_exchanges(self, config: Dict):
        """Initialize exchange connections."""
        exchange_configs = {
            ExchangeType.BINANCE: {
                'class': ccxt.binance,
                'options': {
                    'defaultType': 'future',  # Use futures API
                    'sandbox': False,
                    'rateLimit': 1200,
                    'enableRateLimit': True,
                }
            },
            ExchangeType.BYBIT: {
                'class': ccxt.bybit,
                'options': {
                    'defaultType': 'future',
                    'sandbox': False,
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                }
            },
            ExchangeType.OKX: {
                'class': ccxt.okx,
                'options': {
                    'defaultType': 'swap',  # Perpetual futures
                    'sandbox': False,
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                }
            },
            ExchangeType.BITGET: {
                'class': ccxt.bitget,
                'options': {
                    'defaultType': 'swap',
                    'sandbox': False,
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                }
            },
            ExchangeType.GATE: {
                'class': ccxt.gate,
                'options': {
                    'defaultType': 'future',
                    'sandbox': False,
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                }
            }
        }
        
        for exchange_type in self.supported_exchanges:
            try:
                exchange_config = exchange_configs[exchange_type]
                
                # Add API keys if provided in config
                options = exchange_config['options'].copy()
                if exchange_type.value in config:
                    user_config = config[exchange_type.value]
                    if 'api_key' in user_config:
                        options['apiKey'] = user_config['api_key']
                    if 'secret' in user_config:
                        options['secret'] = user_config['secret']
                    if 'password' in user_config:  # For OKX
                        options['password'] = user_config['password']
                
                exchange = exchange_config['class'](options)
                self.exchanges[exchange_type] = exchange
                logger.info(f"Initialized {exchange_type.value} exchange")
                
            except Exception as e:
                logger.warning(f"Failed to initialize {exchange_type.value}: {e}")
    
    def get_futures_markets(self, exchange_type: ExchangeType) -> List[FuturesMarketInfo]:
        """Get all futures markets from an exchange."""
        if exchange_type not in self.exchanges:
            logger.error(f"Exchange {exchange_type.value} not available")
            return []
        
        try:
            exchange = self.exchanges[exchange_type]
            markets = exchange.load_markets()
            
            futures_markets = []
            for symbol, market in markets.items():
                # Filter for futures/swap markets only
                if market.get('type') in ['future', 'swap'] and market.get('active', False):
                    market_info = FuturesMarketInfo(
                        symbol=symbol,
                        exchange=exchange_type,
                        base_currency=market['base'],
                        quote_currency=market['quote'],
                        contract_type=market.get('type', 'unknown'),
                        contract_size=market.get('contractSize', 1.0),
                        min_order_size=market.get('limits', {}).get('amount', {}).get('min', 0),
                        tick_size=market.get('precision', {}).get('price', 0),
                        is_active=market.get('active', False)
                    )
                    futures_markets.append(market_info)
            
            logger.info(f"Found {len(futures_markets)} futures markets on {exchange_type.value}")
            return futures_markets
            
        except Exception as e:
            logger.error(f"Error fetching markets from {exchange_type.value}: {e}")
            return []
    
    def get_24h_volume_metrics(self, exchange_type: ExchangeType) -> List[VolumeMetrics]:
        """Get 24h volume metrics for all futures markets on an exchange."""
        if exchange_type not in self.exchanges:
            logger.error(f"Exchange {exchange_type.value} not available")
            return []
        
        try:
            exchange = self.exchanges[exchange_type]
            tickers = exchange.fetch_tickers()
            
            volume_metrics = []
            current_time = datetime.now()
            
            for symbol, ticker in tickers.items():
                # Skip if not a futures market
                if not self._is_futures_symbol(symbol, exchange_type):
                    continue
                
                try:
                    volume_24h = ticker.get('baseVolume', 0) or 0
                    volume_usd_24h = ticker.get('quoteVolume', 0) or 0
                    price = ticker.get('last', 0) or ticker.get('close', 0) or 0
                    price_change_24h = ticker.get('percentage', 0) or 0
                    
                    # Skip markets with very low volume
                    if volume_usd_24h < self.min_volume_usd_24h:
                        continue
                    
                    metrics = VolumeMetrics(
                        symbol=symbol,
                        exchange=exchange_type,
                        timestamp=current_time,
                        volume_24h=volume_24h,
                        volume_usd_24h=volume_usd_24h,
                        volume_7d_avg=volume_usd_24h,  # Placeholder - would need historical data
                        volume_30d_avg=volume_usd_24h,  # Placeholder - would need historical data
                        price=price,
                        price_change_24h=price_change_24h
                    )
                    volume_metrics.append(metrics)
                    
                except Exception as e:
                    logger.debug(f"Error processing ticker for {symbol}: {e}")
                    continue
            
            # Sort by volume descending
            volume_metrics.sort(key=lambda x: x.volume_usd_24h, reverse=True)
            
            logger.info(f"Fetched volume metrics for {len(volume_metrics)} futures markets on {exchange_type.value}")
            return volume_metrics
            
        except Exception as e:
            logger.error(f"Error fetching volume metrics from {exchange_type.value}: {e}")
            return []
    
    def _is_futures_symbol(self, symbol: str, exchange_type: ExchangeType) -> bool:
        """Check if a symbol is a futures market."""
        # Common futures symbol patterns
        futures_patterns = [
            'USDT',  # Perpetual futures usually end with USDT
            'USD',   # Some use USD
            'PERP',  # Some explicitly mark as perpetual
        ]
        
        # Exchange-specific patterns
        if exchange_type == ExchangeType.BINANCE:
            return symbol.endswith('USDT') and '/' not in symbol.replace('USDT', '')
        elif exchange_type == ExchangeType.BYBIT:
            return 'USDT' in symbol or 'USD' in symbol
        elif exchange_type == ExchangeType.OKX:
            return '-SWAP' in symbol or 'USDT-SWAP' in symbol
        elif exchange_type == ExchangeType.BITGET:
            return 'USDT' in symbol and 'UMCBL' in symbol
        elif exchange_type == ExchangeType.GATE:
            return '_USDT' in symbol or '_USD' in symbol
        
        return any(pattern in symbol for pattern in futures_patterns)
    
    def get_all_exchanges_volume_metrics(self) -> Dict[ExchangeType, List[VolumeMetrics]]:
        """Get volume metrics from all available exchanges."""
        all_metrics = {}
        
        with ThreadPoolExecutor(max_workers=len(self.exchanges)) as executor:
            # Submit tasks for each exchange
            future_to_exchange = {
                executor.submit(self.get_24h_volume_metrics, exchange_type): exchange_type
                for exchange_type in self.exchanges.keys()
            }
            
            # Collect results
            for future in as_completed(future_to_exchange):
                exchange_type = future_to_exchange[future]
                try:
                    metrics = future.result(timeout=30)  # 30 second timeout
                    all_metrics[exchange_type] = metrics
                except Exception as e:
                    logger.error(f"Error fetching metrics from {exchange_type.value}: {e}")
                    all_metrics[exchange_type] = []
        
        total_markets = sum(len(metrics) for metrics in all_metrics.values())
        logger.info(f"Fetched volume metrics for {total_markets} total futures markets across {len(all_metrics)} exchanges")
        
        return all_metrics
    
    def create_market_rankings(self, all_metrics: Dict[ExchangeType, List[VolumeMetrics]]) -> List[FuturesMarketRanking]:
        """Create unified market rankings across all exchanges."""
        # Combine all metrics
        all_markets = []
        for exchange_type, metrics_list in all_metrics.items():
            all_markets.extend(metrics_list)
        
        # Sort by volume descending
        all_markets.sort(key=lambda x: x.volume_usd_24h, reverse=True)
        
        rankings = []
        for rank, metrics in enumerate(all_markets, 1):
            # Calculate scores (0-100 scale)
            volume_score = min(100, (metrics.volume_usd_24h / 100_000_000) * 100)  # $100M = 100 points
            volatility_score = min(100, abs(metrics.price_change_24h))  # 1% = 1 point, cap at 100
            liquidity_score = volume_score  # Simplified - could be more sophisticated
            
            # Overall score (weighted average)
            overall_score = (volume_score * 0.5 + volatility_score * 0.2 + liquidity_score * 0.3)
            
            # Recommendation criteria
            is_recommended = (
                rank <= self.min_volume_rank and
                metrics.volume_usd_24h >= self.min_volume_usd_24h and
                overall_score >= 30  # Minimum overall score
            )
            
            ranking = FuturesMarketRanking(
                symbol=metrics.symbol,
                exchange=metrics.exchange,
                rank=rank,
                volume_rank=rank,
                volume_usd_24h=metrics.volume_usd_24h,
                volume_score=volume_score,
                volatility_score=volatility_score,
                liquidity_score=liquidity_score,
                overall_score=overall_score,
                is_recommended=is_recommended
            )
            rankings.append(ranking)
        
        logger.info(f"Created rankings for {len(rankings)} futures markets")
        recommended_count = sum(1 for r in rankings if r.is_recommended)
        logger.info(f"Recommended {recommended_count} markets for trading")
        
        return rankings
    
    def get_top_futures_symbols(self, limit: int = 50) -> List[str]:
        """Get top futures symbols by volume for trading."""
        all_metrics = self.get_all_exchanges_volume_metrics()
        rankings = self.create_market_rankings(all_metrics)
        
        # Filter recommended markets and get symbols
        recommended_markets = [r for r in rankings if r.is_recommended][:limit]
        symbols = [r.symbol for r in recommended_markets]
        
        logger.info(f"Selected top {len(symbols)} futures symbols for trading")
        return symbols
    
    def save_volume_analysis(self, filename: Optional[str] = None) -> str:
        """Save complete volume analysis to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"futures_volume_analysis_{timestamp}.json"
        
        # Get all data
        all_metrics = self.get_all_exchanges_volume_metrics()
        rankings = self.create_market_rankings(all_metrics)
        
        # Prepare data for JSON
        analysis_data = {
            'timestamp': datetime.now().isoformat(),
            'exchanges_analyzed': [e.value for e in all_metrics.keys()],
            'total_markets': sum(len(metrics) for metrics in all_metrics.values()),
            'recommended_markets': sum(1 for r in rankings if r.is_recommended),
            'volume_metrics_by_exchange': {
                exchange.value: [m.to_dict() for m in metrics]
                for exchange, metrics in all_metrics.items()
            },
            'market_rankings': [r.to_dict() for r in rankings[:100]],  # Top 100
            'top_recommended_symbols': [
                r.symbol for r in rankings if r.is_recommended
            ][:50]  # Top 50 recommended
        }
        
        # Save to file
        try:
            with open(filename, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            logger.info(f"Volume analysis saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving volume analysis: {e}")
            return ""
