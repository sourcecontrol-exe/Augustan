# ==============================================================================
# File: data_service.py
# Description: Handles all connections and data fetching from exchanges.
# ==============================================================================
import ccxt
import pandas as pd
from config import ACTIVE_CONFIG # Import the consolidated config object

class DataService:
    def __init__(self):
        self.exchanges = {}
        self._connect_to_exchanges()

    def _connect_to_exchanges(self):
        """Initializes connections to all exchanges listed in the config."""
        print("Connecting to exchanges...")
        for ex_id, settings in ACTIVE_CONFIG['exchanges'].items():
            try:
                # Check if API keys are provided
                if not settings['api_key'] or not settings['api_secret']:
                    print(f"  - Warning: API keys for {ex_id} not found. Skipping.")
                    continue

                exchange_class = getattr(ccxt, ex_id)
                exchange = exchange_class({
                    'apiKey': settings['api_key'],
                    'secret': settings['api_secret'],
                    'options': {
                        'defaultType': settings.get('default_type', 'spot'),
                    },
                })

                if settings.get('testnet'):
                    exchange.set_sandbox_mode(True)
                
                self.exchanges[ex_id] = exchange
                print(f"  - Successfully connected to {ex_id}")
            except Exception as e:
                print(f"  - Error connecting to {ex_id}: {e}")

    def fetch_markets(self, ex_id):
        if ex_id in self.exchanges:
            try:
                return self.exchanges[ex_id].load_markets()
            except Exception as e:
                print(f"Error fetching markets for {ex_id}: {e}")
        return None

    def fetch_tickers(self, ex_id, symbols=None):
        if ex_id in self.exchanges:
            try:
                return self.exchanges[ex_id].fetch_tickers(symbols)
            except Exception as e:
                print(f"Error fetching tickers for {ex_id}: {e}")
        return None

    def fetch_ohlcv(self, ex_id, symbol, timeframe, limit=100):
        if ex_id in self.exchanges:
            try:
                ohlcv = self.exchanges[ex_id].fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            except Exception:
                pass # Suppress errors for pairs that might not exist
        return pd.DataFrame()
# Handles connecting and fetching data from exchanges.