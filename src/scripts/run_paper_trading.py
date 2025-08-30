#!/usr/bin/env python3
"""
Augustan Paper Trading Session
Run paper trading with live market data and automated signals
"""

import logging
import time
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager
from scanner import Scanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'paper_trading_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class PaperTradingSession:
    """Simple paper trading session with virtual portfolio"""
    
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # symbol -> quantity
        self.trades = []
        self.total_trades = 0
        
        # Initialize components
        self.data_service = DataService('ccxt', {
            'exchange_id': 'binance',
            'testnet': True,
            'enable_rate_limit': True
        })
        self.strategy = Strategy()
        self.risk_manager = RiskManager()
        self.scanner = Scanner(self.data_service)
        
        logger.info(f"Paper trading session initialized with ${initial_capital:,.2f}")
    
    def get_current_price(self, symbol):
        """Get current market price for symbol"""
        ticker = self.data_service.get_ticker(symbol)
        return ticker.get('last', 0) if ticker else 0
    
    def place_virtual_order(self, symbol, side, amount_usd):
        """Place a virtual order with USD amount"""
        try:
            current_price = self.get_current_price(symbol)
            if not current_price:
                logger.error(f"Could not get price for {symbol}")
                return False
            
            quantity = amount_usd / current_price
            commission = amount_usd * 0.001  # 0.1% commission
            
            if side.upper() == 'BUY':
                if self.cash >= amount_usd + commission:
                    self.cash -= (amount_usd + commission)
                    self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                    
                    trade = {
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'side': 'BUY',
                        'quantity': quantity,
                        'price': current_price,
                        'amount': amount_usd,
                        'commission': commission
                    }
                    self.trades.append(trade)
                    self.total_trades += 1
                    
                    logger.info(f"BUY {quantity:.6f} {symbol} at ${current_price:,.2f} (${amount_usd:,.2f})")
                    return True
                else:
                    logger.warning(f"Insufficient cash for BUY order: ${self.cash:,.2f} < ${amount_usd + commission:,.2f}")
                    return False
            
            elif side.upper() == 'SELL':
                if self.positions.get(symbol, 0) >= quantity:
                    self.cash += (amount_usd - commission)
                    self.positions[symbol] -= quantity
                    if self.positions[symbol] <= 0:
                        del self.positions[symbol]
                    
                    trade = {
                        'timestamp': datetime.now(),
                        'symbol': symbol,
                        'side': 'SELL',
                        'quantity': quantity,
                        'price': current_price,
                        'amount': amount_usd,
                        'commission': commission
                    }
                    self.trades.append(trade)
                    self.total_trades += 1
                    
                    logger.info(f"SELL {quantity:.6f} {symbol} at ${current_price:,.2f} (${amount_usd:,.2f})")
                    return True
                else:
                    logger.warning(f"Insufficient position for SELL order: {self.positions.get(symbol, 0):.6f} < {quantity:.6f}")
                    return False
            
        except Exception as e:
            logger.error(f"Error placing virtual order: {e}")
            return False
    
    def get_portfolio_value(self):
        """Calculate current portfolio value"""
        total_value = self.cash
        
        for symbol, quantity in self.positions.items():
            current_price = self.get_current_price(symbol)
            if current_price:
                position_value = quantity * current_price
                total_value += position_value
        
        return total_value
    
    def print_portfolio_summary(self):
        """Print current portfolio status"""
        total_value = self.get_portfolio_value()
        total_return = (total_value - self.initial_capital) / self.initial_capital
        
        logger.info("=" * 50)
        logger.info("PORTFOLIO SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Current Cash:    ${self.cash:,.2f}")
        logger.info(f"Total Value:     ${total_value:,.2f}")
        logger.info(f"Total Return:    {total_return:.2%}")
        logger.info(f"Total Trades:    {self.total_trades}")
        
        if self.positions:
            logger.info("\nCurrent Positions:")
            for symbol, quantity in self.positions.items():
                current_price = self.get_current_price(symbol)
                position_value = quantity * current_price if current_price else 0
                logger.info(f"  {symbol}: {quantity:.6f} @ ${current_price:,.2f} = ${position_value:,.2f}")
        
        logger.info("=" * 50)
    
    def run_trading_cycle(self, symbols, trade_amount=500):
        """Run one trading cycle on given symbols"""
        logger.info(f"Running trading cycle on {len(symbols)} symbols...")
        
        for symbol in symbols[:5]:  # Limit to top 5 to avoid rate limits
            try:
                # Get OHLCV data
                df = self.data_service.get_ohlcv(symbol, '3m', 100)
                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    continue
                
                # Generate signal
                signal = self.strategy.generate_signal(df)
                
                if signal == 'HOLD':
                    logger.debug(f"{symbol}: HOLD signal")
                    continue
                
                logger.info(f"{symbol}: {signal} signal generated")
                
                # Calculate trade details
                trade_details = self.risk_manager.calculate_trade_details(df, signal)
                if not trade_details:
                    logger.warning(f"Could not calculate trade details for {symbol}")
                    continue
                
                # Place virtual order
                if signal == 'BUY':
                    success = self.place_virtual_order(symbol, 'BUY', trade_amount)
                    if success:
                        logger.info(f"Virtual BUY order placed for {symbol}")
                elif signal == 'SELL' and symbol in self.positions:
                    # Only sell if we have a position
                    current_price = self.get_current_price(symbol)
                    position_value = self.positions[symbol] * current_price
                    success = self.place_virtual_order(symbol, 'SELL', min(position_value, trade_amount))
                    if success:
                        logger.info(f"Virtual SELL order placed for {symbol}")
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
    
    def run_session(self, duration_minutes=5, cycle_interval=60):
        """Run paper trading session"""
        logger.info(f"Starting paper trading session for {duration_minutes} minutes")
        logger.info(f"Cycle interval: {cycle_interval} seconds")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        cycle_count = 0
        
        try:
            while time.time() < end_time:
                cycle_count += 1
                logger.info(f"\n--- CYCLE {cycle_count} ---")
                
                # Find opportunities
                opportunities = self.scanner.find_opportunities()
                
                if opportunities:
                    # Get symbols from first exchange
                    exchange_symbols = list(opportunities.values())[0]
                    if exchange_symbols:
                        self.run_trading_cycle(exchange_symbols)
                    else:
                        logger.info("No opportunities found this cycle")
                else:
                    logger.info("No opportunities found this cycle")
                
                # Print portfolio summary every few cycles
                if cycle_count % 3 == 0:
                    self.print_portfolio_summary()
                
                # Wait for next cycle
                remaining_time = end_time - time.time()
                if remaining_time > cycle_interval:
                    logger.info(f"Waiting {cycle_interval} seconds for next cycle...")
                    time.sleep(cycle_interval)
                else:
                    logger.info(f"Session ending in {remaining_time:.0f} seconds...")
                    break
        
        except KeyboardInterrupt:
            logger.info("Session interrupted by user")
        
        # Final summary
        logger.info(f"\nSession completed after {cycle_count} cycles")
        self.print_portfolio_summary()
        
        # Show recent trades
        if self.trades:
            logger.info("\nRecent Trades:")
            for trade in self.trades[-10:]:  # Last 10 trades
                logger.info(f"  {trade['timestamp'].strftime('%H:%M:%S')} - "
                           f"{trade['side']} {trade['symbol']} @ ${trade['price']:,.2f} "
                           f"(${trade['amount']:,.2f})")

def main():
    """Main entry point"""
    try:
        # Create paper trading session
        session = PaperTradingSession(initial_capital=10000)
        
        # Print initial status
        session.print_portfolio_summary()
        
        # Run trading session
        session.run_session(duration_minutes=3, cycle_interval=30)
        
    except KeyboardInterrupt:
        logger.info("Paper trading stopped by user")
    except Exception as e:
        logger.error(f"Error in paper trading session: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
