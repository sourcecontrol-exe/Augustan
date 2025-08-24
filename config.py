# ==============================================================================
# File: config.py
# Description: Loads and consolidates all configuration for the bot.
#              It fetches secrets from the environment and settings from the configs package.
# ==============================================================================
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from configs import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file (for local development)
load_dotenv()

class ConfigManager:
    """Centralized configuration management for the Augustan Trading Bot"""
    
    def __init__(self):
        self._config_cache = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration sections"""
        try:
            # Load settings from the new configs package
            self._config_cache['trading'] = config_manager.get_trading_config()
            self._config_cache['scanner'] = config_manager.get_scanner_config()
            self._config_cache['risk'] = config_manager.get_risk_config()
            self._config_cache['exchanges'] = config_manager.get_exchanges_config()
            
            # Load API Keys from Environment Variables
            self._config_cache['api_keys'] = self._load_api_keys()
            
            # Load exchange configurations
            self._config_cache['exchanges_config'] = self._load_exchange_configs()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables"""
        api_keys = {}
        
        # Binance
        binance_key = os.getenv('BINANCE_API_KEY')
        binance_secret = os.getenv('BINANCE_API_SECRET')
        if binance_key and binance_secret:
            api_keys['binance'] = {
                'api_key': binance_key,
                'api_secret': binance_secret
            }
        
        # Bybit
        bybit_key = os.getenv('BYBIT_API_KEY')
        bybit_secret = os.getenv('BYBIT_API_SECRET')
        if bybit_key and bybit_secret:
            api_keys['bybit'] = {
                'api_key': bybit_key,
                'api_secret': bybit_secret
            }
        
        # Pi42 (if needed)
        pi42_key = os.getenv('PI42_API_KEY')
        pi42_secret = os.getenv('PI42_API_SECRET')
        if pi42_key and pi42_secret:
            api_keys['pi42'] = {
                'api_key': pi42_key,
                'api_secret': pi42_secret
            }
        
        return api_keys
    
    def _load_exchange_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load exchange-specific configurations"""
        exchanges = {}
        
        # Binance configuration
        if 'binance' in self._config_cache['exchanges'] and self._config_cache['exchanges']['binance']['enabled']:
            exchanges['binance'] = {
                'api_key': self._config_cache['api_keys'].get('binance', {}).get('api_key'),
                'api_secret': self._config_cache['api_keys'].get('binance', {}).get('api_secret'),
                'default_type': self._config_cache['trading'].get('exchange_type', 'future'),
                'testnet': self._config_cache['trading'].get('testnet', True),
                'exchange': 'binance'
            }
        
        # Bybit configuration
        if 'bybit' in self._config_cache['exchanges'] and self._config_cache['exchanges']['bybit']['enabled']:
            exchanges['bybit'] = {
                'api_key': self._config_cache['api_keys'].get('bybit', {}).get('api_key'),
                'api_secret': self._config_cache['api_keys'].get('bybit', {}).get('api_secret'),
                'default_type': self._config_cache['trading'].get('exchange_type', 'future'),
                'testnet': self._config_cache['trading'].get('testnet', True),
                'exchange': 'bybit'
            }
        
        return exchanges
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        try:
            keys = key.split('.')
            value = self._config_cache
            
            for k in keys:
                value = value[k]
            
            return value
        except (KeyError, TypeError):
            return default
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration"""
        return self._config_cache.get('trading', {})
    
    def get_scanner_config(self) -> Dict[str, Any]:
        """Get scanner configuration"""
        return self._config_cache.get('scanner', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return self._config_cache.get('risk', {})
    
    def get_exchange_config(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific exchange"""
        return self._config_cache.get('exchanges_config', {}).get(exchange_name)
    
    def get_all_exchanges(self) -> Dict[str, Dict[str, Any]]:
        """Get all exchange configurations"""
        return self._config_cache.get('exchanges_config', {})
    
    def get_api_keys(self) -> Dict[str, Dict[str, str]]:
        """Get all API keys"""
        return self._config_cache.get('api_keys', {})
    
    def reload(self):
        """Reload all configurations"""
        logger.info("Reloading configuration...")
        self._config_cache.clear()
        self._load_all_configs()
    
    def validate(self) -> bool:
        """Validate configuration completeness"""
        required_sections = ['trading', 'scanner', 'risk', 'exchanges']
        
        for section in required_sections:
            if section not in self._config_cache:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Check if at least one exchange is configured
        if not self._config_cache.get('exchanges_config'):
            logger.error("No exchanges configured")
            return False
        
        logger.info("Configuration validation passed")
        return True

# Global configuration instance
config = ConfigManager()

# Legacy compatibility - maintain existing interface
EXCHANGES = config.get_all_exchanges()
ACTIVE_CONFIG = {
    "exchanges": EXCHANGES,
    "trading": config.get_trading_config(),
    "scanner": config.get_scanner_config(),
    "risk": config.get_risk_config()
}

# Configuration validation on import
if not config.validate():
    logger.warning("Configuration validation failed - some features may not work correctly")
