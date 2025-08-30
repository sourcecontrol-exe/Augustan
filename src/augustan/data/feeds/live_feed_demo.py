"""
Live Data Feed Demo for Paper Trading

Demonstrates different ways to get real-time market data for paper trading:
1. WebSocket streams (fastest, real-time)
2. REST API polling (reliable fallback)
3. Combined approach with failover
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_service import DataService
from paper_trading.live_data_feed import LiveDataManager, create_simple_feed, MarketData


def setup_logging():
    """Setup logging for live feed demo"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('live_feed_demo.log')
        ]
    )


async def demo_websocket_feed():
    """Demonstrate WebSocket-based live feed"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== WEBSOCKET LIVE FEED DEMO ===")
    
    try:
        # Initialize data service
        data_service = DataService('ccxt', {
            'exchange_id': 'binance',
            'testnet': True,
            'enable_rate_limit': True
        })
        
        # Create live feed for popular symbols
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        feed = create_simple_feed(symbols, data_service)
        
        # Price update counter
        price_updates = {}
        
        def price_callback(data: MarketData):
            """Callback to handle price updates"""
            if data.symbol not in price_updates:
                price_updates[data.symbol] = 0
            price_updates[data.symbol] += 1
            
            logger.info(f"📈 {data.symbol}: ${data.price:,.2f} "
                       f"(bid: ${data.bid:,.2f}, ask: ${data.ask:,.2f}) "
                       f"[{data.source}] - Update #{price_updates[data.symbol]}")
        
        feed.add_price_callback(price_callback)
        
        logger.info(f"Starting WebSocket feed for: {symbols}")
        logger.info("Will run for 30 seconds...")
        
        # Start feed
        await feed.start_feed()
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
        # Show statistics
        logger.info("\n=== FEED STATISTICS ===")
        for symbol, count in price_updates.items():
            logger.info(f"{symbol}: {count} updates received")
        
        # Show latest prices
        latest_prices = feed.get_latest_prices()
        logger.info("\n=== LATEST PRICES ===")
        for symbol, data in latest_prices.items():
            age = (datetime.now() - data.timestamp).total_seconds()
            logger.info(f"{symbol}: ${data.price:,.2f} (age: {age:.1f}s)")
        
    except Exception as e:
        logger.error(f"Error in WebSocket demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'feed' in locals():
            await feed.stop_feed()
        logger.info("WebSocket demo completed")


async def demo_rest_fallback():
    """Demonstrate REST API fallback"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== REST API FALLBACK DEMO ===")
    
    try:
        # Initialize data service
        data_service = DataService('ccxt', {
            'exchange_id': 'binance',
            'testnet': True
        })
        
        symbols = ['BTC/USDT', 'ETH/USDT']
        
        # Create feed manager
        manager = LiveDataManager(data_service)
        feed = manager.create_feed(symbols, "rest_demo")
        
        # Disable WebSocket to force REST usage
        feed.config.enable_websocket = False
        feed.config.enable_rest_fallback = True
        feed.config.rest_poll_interval_seconds = 3
        
        def price_callback(data: MarketData):
            logger.info(f"🔄 {data.symbol}: ${data.price:,.2f} [{data.source}]")
        
        feed.add_price_callback(price_callback)
        
        logger.info("Starting REST-only feed (3-second intervals)")
        await feed.start_feed()
        
        # Run for 20 seconds
        await asyncio.sleep(20)
        
    except Exception as e:
        logger.error(f"Error in REST demo: {e}")
    finally:
        if 'manager' in locals():
            await manager.stop_all_feeds()
        logger.info("REST demo completed")


async def demo_combined_feed():
    """Demonstrate combined WebSocket + REST with failover"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== COMBINED FEED WITH FAILOVER DEMO ===")
    
    try:
        data_service = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
        symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        
        feed = create_simple_feed(symbols, data_service)
        
        # Track data sources
        source_counts = {'websocket': 0, 'rest_api': 0}
        
        def price_callback(data: MarketData):
            source_counts[data.source] = source_counts.get(data.source, 0) + 1
            
            # Show different icons for different sources
            icon = "⚡" if data.source == "websocket" else "🔄"
            logger.info(f"{icon} {data.symbol}: ${data.price:,.2f} [{data.source}]")
        
        feed.add_price_callback(price_callback)
        
        logger.info("Starting combined feed (WebSocket + REST fallback)")
        await feed.start_feed()
        
        # Run for 25 seconds
        await asyncio.sleep(25)
        
        # Show source statistics
        logger.info("\n=== DATA SOURCE STATISTICS ===")
        total_updates = sum(source_counts.values())
        for source, count in source_counts.items():
            percentage = (count / total_updates * 100) if total_updates > 0 else 0
            logger.info(f"{source}: {count} updates ({percentage:.1f}%)")
        
    except Exception as e:
        logger.error(f"Error in combined demo: {e}")
    finally:
        if 'feed' in locals():
            await feed.stop_feed()
        logger.info("Combined demo completed")


async def demo_paper_trading_with_live_feed():
    """Demonstrate paper trading with live data feed"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== PAPER TRADING WITH LIVE FEED DEMO ===")
    
    try:
        # Import paper trading components
        from strategy import Strategy
        from risk_manager import RiskManager
        from paper_trading import PaperTradingEngine, PaperTradingConfig
        
        # Initialize components
        data_service = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
        strategy = Strategy()
        risk_manager = RiskManager()
        
        # Paper trading config
        config = PaperTradingConfig(
            initial_capital=25000.0,
            commission_rate=0.001,
            slippage_rate=0.0005,
            max_position_size_pct=0.2
        )
        
        # Create paper trader
        paper_trader = PaperTradingEngine(config, data_service, strategy, risk_manager)
        
        symbols = ['BTC/USDT', 'ETH/USDT']
        logger.info(f"Starting paper trading with live feed for: {symbols}")
        logger.info("Duration: 2 minutes")
        
        # Run paper trading with live feed enabled
        await paper_trader.run_paper_trading(
            symbols=symbols, 
            duration_minutes=2, 
            use_live_feed=True
        )
        
    except Exception as e:
        logger.error(f"Error in paper trading demo: {e}")
        import traceback
        traceback.print_exc()


def show_live_feed_options():
    """Show available live feed options"""
    print("=== AUGUSTAN LIVE DATA FEED OPTIONS ===\n")
    
    print("📊 Available Data Sources:")
    print("1. WebSocket Streams (Real-time)")
    print("   - Binance WebSocket API")
    print("   - Sub-second price updates")
    print("   - Automatic reconnection")
    print()
    
    print("2. REST API Polling (Reliable)")
    print("   - Exchange REST endpoints")
    print("   - Configurable intervals (1-60s)")
    print("   - Fallback for WebSocket failures")
    print()
    
    print("3. Combined Approach (Recommended)")
    print("   - WebSocket for speed")
    print("   - REST API for reliability")
    print("   - Automatic failover")
    print()
    
    print("🔧 Configuration Options:")
    print("- Update intervals: 100ms - 60s")
    print("- Reconnection attempts: 1-10")
    print("- Rate limiting: 1-60 requests/minute")
    print("- Data freshness: 5-300 seconds")
    print()
    
    print("💡 Usage Examples:")
    print("python paper_trading/live_feed_demo.py --websocket")
    print("python paper_trading/live_feed_demo.py --rest")
    print("python paper_trading/live_feed_demo.py --combined")
    print("python paper_trading/live_feed_demo.py --paper-trading")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Data Feed Demo')
    parser.add_argument('--websocket', action='store_true', help='Demo WebSocket feed')
    parser.add_argument('--rest', action='store_true', help='Demo REST API feed')
    parser.add_argument('--combined', action='store_true', help='Demo combined feed')
    parser.add_argument('--paper-trading', action='store_true', help='Demo paper trading with live feed')
    parser.add_argument('--info', action='store_true', help='Show live feed options')
    
    args = parser.parse_args()
    
    if args.websocket:
        asyncio.run(demo_websocket_feed())
    elif args.rest:
        asyncio.run(demo_rest_fallback())
    elif args.combined:
        asyncio.run(demo_combined_feed())
    elif args.paper_trading:
        asyncio.run(demo_paper_trading_with_live_feed())
    elif args.info:
        show_live_feed_options()
    else:
        print("Live Data Feed Demo Options:")
        print("  --websocket      WebSocket real-time demo")
        print("  --rest           REST API polling demo")
        print("  --combined       Combined approach demo")
        print("  --paper-trading  Paper trading with live feed")
        print("  --info           Show all available options")
        print()
        print("Example: python live_feed_demo.py --websocket")
