"""
Paper Trading Demo for Augustan Trading Bot

Demonstrates real-time paper trading with live market data,
virtual portfolio management, and performance tracking.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager
from paper_trading import PaperTradingEngine, PaperTradingConfig
from paper_trading.paper_trader import OrderSide


def setup_logging():
    """Setup logging for paper trading demo"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('paper_trading_demo.log')
        ]
    )


async def run_paper_trading_demo():
    """Run paper trading demonstration"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== AUGUSTAN PAPER TRADING DEMO ===")
    
    try:
        # Initialize components
        logger.info("Initializing trading components...")
        
        # Data service with testnet
        data_service = DataService('ccxt', {
            'exchange_id': 'binance',
            'testnet': True,
            'enable_rate_limit': True
        })
        
        # Strategy and risk manager
        strategy = Strategy()
        risk_manager = RiskManager()
        
        # Paper trading configuration
        config = PaperTradingConfig(
            initial_capital=50000.0,      # $50k virtual capital
            commission_rate=0.001,        # 0.1% commission
            slippage_rate=0.0005,         # 0.05% slippage
            execution_delay_ms=100,       # 100ms execution delay
            max_orders_per_minute=5,      # Conservative rate limit
            max_position_size_pct=0.15    # Max 15% per position
        )
        
        # Initialize paper trading engine
        paper_trader = PaperTradingEngine(
            config=config,
            data_service=data_service,
            strategy=strategy,
            risk_manager=risk_manager
        )
        
        logger.info(f"Paper trading initialized with ${config.initial_capital:,.2f} virtual capital")
        
        # Trading symbols (popular crypto pairs)
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        logger.info(f"Trading symbols: {symbols}")
        
        # Test connectivity
        logger.info("Testing market data connectivity...")
        for symbol in symbols:
            ticker = data_service.get_ticker(symbol)
            if ticker:
                logger.info(f"{symbol}: ${ticker.get('last', 0):,.2f}")
            else:
                logger.warning(f"Could not fetch data for {symbol}")
        
        # Manual trading demonstration
        logger.info("\n=== MANUAL TRADING DEMONSTRATION ===")
        
        # Get current prices
        current_prices = {}
        for symbol in symbols:
            ticker = data_service.get_ticker(symbol)
            if ticker:
                current_prices[symbol] = ticker.get('last', 0)
        
        # Place some demo orders
        logger.info("Placing demonstration orders...")
        
        # Buy BTC
        btc_order = paper_trader.place_market_order('BTC/USDT', OrderSide.BUY, 0.01)
        if btc_order:
            logger.info(f"Placed BTC buy order: {btc_order}")
        
        # Buy ETH
        eth_order = paper_trader.place_market_order('ETH/USDT', OrderSide.BUY, 0.1)
        if eth_order:
            logger.info(f"Placed ETH buy order: {eth_order}")
        
        # Wait a moment for orders to process
        await asyncio.sleep(2)
        
        # Show portfolio status
        portfolio_summary = paper_trader.get_portfolio_summary(current_prices)
        logger.info(f"\nPortfolio Summary after demo orders:")
        logger.info(f"  Cash: ${portfolio_summary['cash']:,.2f}")
        logger.info(f"  Total Equity: ${portfolio_summary['total_equity']:,.2f}")
        logger.info(f"  Total Return: {portfolio_summary['total_return']:.2%}")
        logger.info(f"  Positions: {portfolio_summary['positions']}")
        logger.info(f"  Total Trades: {portfolio_summary['total_trades']}")
        
        # Automated trading session
        logger.info("\n=== STARTING AUTOMATED PAPER TRADING SESSION ===")
        logger.info("Running for 5 minutes with automated signals...")
        logger.info("Press Ctrl+C to stop early")
        
        # Run paper trading session
        await paper_trader.run_paper_trading(symbols, duration_minutes=5)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Error in paper trading demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Paper trading demo completed")


def run_quick_demo():
    """Run a quick synchronous demo"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== QUICK PAPER TRADING DEMO ===")
    
    try:
        # Initialize components
        data_service = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
        strategy = Strategy()
        risk_manager = RiskManager()
        
        config = PaperTradingConfig(initial_capital=10000.0)
        paper_trader = PaperTradingEngine(config, data_service, strategy, risk_manager)
        
        # Get current price
        ticker = data_service.get_ticker('BTC/USDT')
        if not ticker:
            logger.error("Could not fetch BTC price")
            return
            
        current_price = ticker.get('last', 0)
        logger.info(f"Current BTC price: ${current_price:,.2f}")
        
        # Place a small buy order
        order_id = paper_trader.place_market_order('BTC/USDT', OrderSide.BUY, 0.001)
        
        if order_id:
            order = paper_trader.orders[order_id]
            logger.info(f"Order placed: {order.side.value} {order.quantity} BTC")
            logger.info(f"Order status: {order.status.value}")
            
            if order.status == paper_trader.OrderStatus.FILLED:
                logger.info(f"Order filled at ${order.filled_price:.2f}")
                logger.info(f"Commission: ${order.commission:.4f}")
        
        # Show final portfolio
        portfolio_summary = paper_trader.get_portfolio_summary({'BTC/USDT': current_price})
        logger.info(f"\nFinal Portfolio:")
        logger.info(f"  Cash: ${portfolio_summary['cash']:,.2f}")
        logger.info(f"  Total Equity: ${portfolio_summary['total_equity']:,.2f}")
        logger.info(f"  Positions: {portfolio_summary['positions']}")
        
    except Exception as e:
        logger.error(f"Error in quick demo: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Augustan Paper Trading Demo')
    parser.add_argument('--quick', action='store_true', help='Run quick synchronous demo')
    parser.add_argument('--full', action='store_true', help='Run full automated demo')
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_demo()
    elif args.full:
        asyncio.run(run_paper_trading_demo())
    else:
        print("Usage:")
        print("  python demo_paper_trading.py --quick   # Quick demo")
        print("  python demo_paper_trading.py --full    # Full automated demo")
