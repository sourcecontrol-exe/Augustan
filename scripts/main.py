#!/usr/bin/env python3
"""
Augustan Main Entry Point

Main script for live trading operations.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.trading import RSIMACDStrategy
from services.data import DataService
from services.risk import RiskManager
from core.config import ConfigManager
from core.exceptions import AugustanError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for live trading"""
    try:
        logger.info("Starting Augustan Trading Bot")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_active_config()
        
        # Initialize services
        data_service = DataService(config)
        risk_manager = RiskManager(config)
        strategy = RSIMACDStrategy()
        
        logger.info("Augustan services initialized successfully")
        logger.info("Live trading mode - use with caution!")
        
        # TODO: Implement live trading engine
        logger.warning("Live trading engine not yet implemented")
        logger.info("Use paper trading mode for testing strategies")
        
    except AugustanError as e:
        logger.error(f"Augustan error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
