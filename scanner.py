# The logic for scanning markets and finding opportunities.# ==============================================================================
# File: scanner.py
# Description: Scans exchanges for potential trading opportunities.
# ==============================================================================
from data_service import DataService
from config import ACTIVE_CONFIG

class Scanner:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.settings = ACTIVE_CONFIG['scanner']
        self.base_currency = self.settings.get('base_currency', 'USDT')
        self.market_limit = self.settings.get('market_limit', 150)
        self.min_24h_change = self.settings.get('min_24h_change', 5.0)

    def find_opportunities(self):
        """Scans all connected exchanges and returns a dynamic watchlist."""
        print("\n--- Starting Market Scan ---")
        watchlist = {}
        for ex_id in self.data_service.exchanges.keys():
            print(f"Scanning {ex_id}...")
            try:
                all_tickers = self.data_service.fetch_tickers(ex_id)
                if not all_tickers:
                    continue

                potential_pairs = {
                    symbol: ticker for symbol, ticker in all_tickers.items()
                    if symbol.endswith(f"/{self.base_currency}")
                }

                sorted_pairs = sorted(potential_pairs.items(), key=lambda item: item[1].get('quoteVolume', 0), reverse=True)
                top_pairs = dict(sorted_pairs[:self.market_limit])

                opportunities = []
                for symbol, ticker in top_pairs.items():
                    change_24h = ticker.get('percentage')
                    if change_24h and abs(change_24h) >= self.min_24h_change:
                        opportunities.append(symbol)
                
                watchlist[ex_id] = opportunities
                print(f"  - Found {len(opportunities)} potential opportunities on {ex_id}.")
            except Exception as e:
                print(f"  - An error occurred while scanning {ex_id}: {e}")
        return watchlist
