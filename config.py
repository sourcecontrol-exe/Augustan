# ==============================================================================
# File: config.py
# Description: Loads and consolidates all configuration for the bot.
#              It fetches secrets from the environment and settings from constants.py.
# ==============================================================================
import os
from dotenv import load_dotenv
from constants import get_exchanges_config, get_trading_config, get_scanner_config, get_risk_config

# Load environment variables from a .env file (for local development)
load_dotenv()

# --- Load settings from your constants/JSON file ---
TRADING_SETTINGS = get_trading_config()
SCANNER_SETTINGS = get_scanner_config()
RISK_SETTINGS = get_risk_config()

# --- Load API Keys from Environment Variables ---
# This structure securely loads keys without hardcoding them.
EXCHANGES = {
    'binance': {
        'api_key': os.getenv('BINANCE_API_KEY'),
        'api_secret': os.getenv('BINANCE_API_SECRET'),
        'default_type': TRADING_SETTINGS.get('exchange_type', 'future'),
        'testnet': True, # Set to False for live trading
    },
    'bybit': {
        'api_key': os.getenv('BYBIT_API_KEY'),
        'api_secret': os.getenv('BYBIT_API_SECRET'),
        'default_type': TRADING_SETTINGS.get('exchange_type', 'future'),
        'testnet': True, # Set to False for live trading
    }
    # Add more exchanges here, ensuring you have corresponding environment variables
}

# --- Consolidate all settings into a single, accessible object ---
# This makes it easy for other modules to get the settings they need.
ACTIVE_CONFIG = {
    "exchanges": EXCHANGES,
    "trading": TRADING_SETTINGS,
    "scanner": SCANNER_SETTINGS,
    "risk": RISK_SETTINGS
}
