#!/usr/bin/env python3
# ==============================================================================
# File: main.py
# Description: Main entry point for the Augustan Trading Bot
# ==============================================================================

import logging
import time
import sys
from typing import Dict, Any

from config import config
from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager
from scanner import Scanner

# Configure logging
logging.basicConfig(                                                
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('augustan_bot.log')
    ]
)
logger = logging.getLogger(__name__)

class AugustanBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        """Initialize the trading bot components"""
        try:
            logger.info("Initializing Augustan Trading Bot...")
            
            # Validate configuration
            if not config.validate():
                raise RuntimeError("Configuration validation failed")
            
            # Initialize components
            self.data_service = None
            self.strategy = Strategy()
            self.risk_manager = RiskManager()
            self.scanner = None
            
            # Get trading configuration
            self.trading_config = config.get_trading_config()
            self.timeframe = self.trading_config.get('timeframe', '3m')
            
            # Initialize exchange connection
            self._initialize_exchange()
            
            # Initialize scanner
            self.scanner = Scanner(self.data_service)
            
            logger.info("Augustan Trading Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _initialize_exchange(self):
        """Initialize connection to the primary exchange"""
        try:
            # Get the first enabled exchange from configuration
            exchanges = config.get_all_exchanges()
            
            if not exchanges:
                raise RuntimeError("No exchanges configured")
            
            # Use the first available exchange
            exchange_name = list(exchanges.keys())[0]
            exchange_config = exchanges[exchange_name]
            
            logger.info(f"Connecting to {exchange_name}...")
            
            # Initialize data service with the exchange
            self.data_service = DataService('ccxt', {
                'exchange_id': exchange_config.get('exchange', exchange_name),
                'api_key': exchange_config.get('api_key'),
                'api_secret': exchange_config.get('api_secret'),
                'testnet': exchange_config.get('testnet', True),
                'default_type': exchange_config.get('default_type', 'future')
            })
            
            logger.info(f"Successfully connected to {exchange_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    def run_trading_cycle(self):
        """Execute one complete trading cycle"""
        try:
            logger.info("Starting trading cycle...")
            
            # Step 1: Scan for opportunities
            opportunities = self.scanner.find_opportunities()
            
            if not opportunities:
                logger.info("No trading opportunities found")
                return
            
            # Step 2: Process each opportunity
            for exchange_id, symbols in opportunities.items():
                for symbol in symbols[:5]:  # Limit to top 5 opportunities
                    try:
                        self._process_symbol(symbol)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")
                        continue
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def _process_symbol(self, symbol: str):
        """Process a single trading symbol"""
        try:
            logger.info(f"Processing {symbol}...")
            
            # Get market data
            df = self.data_service.get_ohlcv(symbol, self.timeframe, 100)
            
            if df.empty:
                logger.warning(f"No data available for {symbol}")
                return
            
            # Generate trading signal
            signal = self.strategy.generate_signal(df)
            
            if signal == 'HOLD':
                logger.debug(f"No signal for {symbol}")
                return
            
            logger.info(f"Generated {signal} signal for {symbol}")
            
            # Calculate trade details
            trade_details = self.risk_manager.calculate_trade_details(df, signal)
            
            if not trade_details:
                logger.warning(f"Could not calculate trade details for {symbol}")
                return
            
            # Log trade details (in live trading, this would place the order)
            logger.info(f"Trade details for {symbol}:")
            logger.info(f"  Signal: {signal}")
            logger.info(f"  Position size: {trade_details['position_size']:.4f}")
            logger.info(f"  Entry price: {trade_details['entry_price']:.4f}")
            logger.info(f"  Stop loss: {trade_details['stop_loss']:.4f}")
            logger.info(f"  Take profit: {trade_details['take_profit']:.4f}")
            
            # TODO: In live trading mode, place the actual order here
            # self._place_order(symbol, signal, trade_details)
            
        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
    
    def _place_order(self, symbol: str, signal: str, trade_details: Dict[str, Any]):
        """Place an order (placeholder for live trading)"""
        # This would be implemented for live trading
        # For now, just log the intended order
        logger.info(f"Would place {signal} order for {symbol} with details: {trade_details}")
    
    def run(self, cycles: int = None, interval: int = 60):
        """
        Run the trading bot
        
        Args:
            cycles: Number of trading cycles to run (None for infinite)
            interval: Seconds between cycles
        """
        try:
            logger.info(f"Starting Augustan Trading Bot (cycles: {cycles}, interval: {interval}s)")
            
            cycle_count = 0
            
            while cycles is None or cycle_count < cycles:
                try:
                    self.run_trading_cycle()
                    cycle_count += 1
                    
                    if cycles is None or cycle_count < cycles:
                        logger.info(f"Waiting {interval} seconds until next cycle...")
                        time.sleep(interval)
                        
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(interval)  # Wait before retrying
            
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.error(f"Fatal error in bot execution: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            if self.data_service:
                self.data_service.disconnect()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    try:
        # Create and run the bot
        bot = AugustanBot()
        
        # Run for a single cycle in demo mode
        # For continuous trading, use: bot.run()
        bot.run(cycles=1)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
