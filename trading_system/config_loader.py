import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class SecureConfigLoader:
    """Secure configuration loader that prioritizes environment variables for sensitive data."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.env_file = Path(".env")
        
    def load_config(self, config_name: str = "exchanges_config.json") -> Dict[str, Any]:
        """Load configuration with environment variable override for sensitive data."""
        config_path = self.config_dir / config_name
        
        # Load base config
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Override with environment variables for sensitive data
        self._override_with_env_vars(config)
        
        return config
    
    def _override_with_env_vars(self, config: Dict[str, Any]) -> None:
        """Override sensitive configuration with environment variables."""
        
        # Binance Spot API Keys
        if os.getenv('BINANCE_SPOT_API_KEY'):
            if 'binance' not in config:
                config['binance'] = {}
            config['binance']['api_key'] = os.getenv('BINANCE_SPOT_API_KEY')
            logger.info("Using Binance Spot API key from environment variable")
            
        if os.getenv('BINANCE_SPOT_SECRET_KEY'):
            if 'binance' not in config:
                config['binance'] = {}
            config['binance']['secret_key'] = os.getenv('BINANCE_SPOT_SECRET_KEY')
            logger.info("Using Binance Spot secret key from environment variable")
        
        # Binance Futures API Keys
        if os.getenv('BINANCE_FUTURES_API_KEY'):
            if 'futures' not in config:
                config['futures'] = {}
            config['futures']['api_key'] = os.getenv('BINANCE_FUTURES_API_KEY')
            logger.info("Using Binance Futures API key from environment variable")
            
        if os.getenv('BINANCE_FUTURES_SECRET_KEY'):
            if 'futures' not in config:
                config['futures'] = {}
            config['futures']['secret_key'] = os.getenv('BINANCE_FUTURES_SECRET_KEY')
            logger.info("Using Binance Futures secret key from environment variable")
        
        # Testnet configuration
        if os.getenv('BINANCE_TESTNET'):
            testnet_value = os.getenv('BINANCE_TESTNET').lower() == 'true'
            if 'binance' not in config:
                config['binance'] = {}
            config['binance']['testnet'] = testnet_value
            logger.info(f"Using testnet setting from environment variable: {testnet_value}")
    
    def save_config(self, config: Dict[str, Any], config_name: str = "exchanges_config.json") -> None:
        """Save configuration without sensitive data."""
        config_path = self.config_dir / config_name
        
        # Create a copy without sensitive data for saving
        safe_config = self._remove_sensitive_data(config.copy())
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(safe_config, f, indent=2)
        
        logger.info(f"Configuration saved to {config_path} (sensitive data excluded)")
    
    def _remove_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from config before saving."""
        sensitive_keys = ['api_key', 'secret_key', 'secret']
        
        def clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            cleaned = {}
            for key, value in d.items():
                if isinstance(value, dict):
                    cleaned[key] = clean_dict(value)
                elif key in sensitive_keys:
                    cleaned[key] = "***REDACTED***"
                else:
                    cleaned[key] = value
            return cleaned
        
        return clean_dict(config)
    
    def create_env_file(self) -> None:
        """Create .env file from current config (for user to fill in)."""
        if self.env_file.exists():
            logger.warning(".env file already exists. Skipping creation.")
            return
        
        env_content = """# Binance API Configuration
# Fill in your actual API keys here

# Spot Trading API Keys
BINANCE_SPOT_API_KEY=your_spot_api_key_here
BINANCE_SPOT_SECRET_KEY=your_spot_secret_key_here

# Futures Trading API Keys (if different from spot)
BINANCE_FUTURES_API_KEY=your_futures_api_key_here
BINANCE_FUTURES_SECRET_KEY=your_futures_secret_key_here

# Testnet Configuration
BINANCE_TESTNET=true

# Risk Management (optional - can be overridden in config files)
DEFAULT_BUDGET=1000.0
MAX_RISK_PER_TRADE=0.01
MIN_SAFETY_RATIO=2.0
DEFAULT_LEVERAGE=3
"""
        
        with open(self.env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"Created {self.env_file}. Please fill in your actual API keys.")
