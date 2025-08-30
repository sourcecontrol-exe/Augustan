# ==============================================================================
# File: scanner.py
# Description: Scans exchanges for potential trading opportunities.
# ==============================================================================
import logging
from typing import Dict, List
from ...data.services.data_service import DataService
from ...config.config import config

logger = logging.getLogger(__name__)

class Scanner:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.settings = config.get_scanner_config()
        self.base_currency = self.settings.get('base_currency', 'USDT')
        self.market_limit = self.settings.get('market_limit', 150)
        self.min_24h_change = self.settings.get('min_24h_change', 5.0)
        self.max_24h_change = self.settings.get('max_24h_change', 20.0)

    def find_opportunities(self) -> Dict[str, List[str]]:
        """Scans the exchange and returns a dynamic watchlist."""
        logger.info("Starting market scan...")
        watchlist = {}
        
        try:
            # Get available markets from the data service
            markets = self.data_service.get_markets()
            
            if not markets:
                logger.warning("No markets available")
                return watchlist
            
            # Filter markets to only include those with the base currency
            potential_pairs = [
                symbol for symbol in markets 
                if symbol.endswith(f"/{self.base_currency}")
            ]
            
            logger.info(f"Found {len(potential_pairs)} {self.base_currency} pairs")
            
            # Get ticker data for each pair and filter by volume/volatility
            opportunities = []
            
            for symbol in potential_pairs[:self.market_limit]:  # Limit to avoid rate limits
                try:
                    ticker = self.data_service.get_ticker(symbol)
                    
                    if not ticker:
                        continue
                    
                    # Check 24h change criteria
                    change_24h = ticker.get('percentage', 0)
                    volume_24h = ticker.get('quoteVolume', 0)
                    
                    # Filter by volatility and volume
                    if (abs(change_24h) >= self.min_24h_change and 
                        abs(change_24h) <= self.max_24h_change and
                        volume_24h > 0):
                        
                        opportunities.append({
                            'symbol': symbol,
                            'change_24h': change_24h,
                            'volume_24h': volume_24h,
                            'price': ticker.get('last', 0)
                        })
                        
                except Exception as e:
                    logger.debug(f"Error getting ticker for {symbol}: {e}")
                    continue
            
            # Sort by volume (highest first)
            opportunities.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            # Extract just the symbols for the watchlist
            opportunity_symbols = [opp['symbol'] for opp in opportunities]
            
            # Use exchange name or 'default' as key
            exchange_name = getattr(self.data_service, 'exchange_name', 'default')
            watchlist[exchange_name] = opportunity_symbols
            
            logger.info(f"Found {len(opportunity_symbols)} opportunities on {exchange_name}")
            
            # Log top opportunities
            for i, opp in enumerate(opportunities[:5]):
                logger.info(f"  {i+1}. {opp['symbol']}: {opp['change_24h']:.2f}% change, "
                           f"${opp['volume_24h']:,.0f} volume")
            
        except Exception as e:
            logger.error(f"Error during market scan: {e}")
        
        return watchlist
