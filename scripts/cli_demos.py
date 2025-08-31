#!/usr/bin/env python3
"""
CLI Demo Scripts for Augustan Trading Bot
Provides quick access to common trading operations
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def demo_quick_backtest():
    """Run a quick backtesting demo"""
    print("🚀 Quick Backtest Demo")
    print("=" * 50)
    
    try:
        from backtesting.demo_backtest import run_single_strategy_demo
        run_single_strategy_demo()
        print("\n✅ Quick backtest completed!")
    except Exception as e:
        print(f"❌ Error in quick backtest: {e}")

def demo_strategy_comparison():
    """Run strategy comparison demo"""
    print("📊 Strategy Comparison Demo")
    print("=" * 50)
    
    try:
        from backtesting.demo_backtest import run_multi_strategy_demo
        run_multi_strategy_demo()
        print("\n✅ Strategy comparison completed!")
    except Exception as e:
        print(f"❌ Error in strategy comparison: {e}")

def demo_paper_trading_quick():
    """Run quick paper trading demo"""
    print("💰 Quick Paper Trading Demo")
    print("=" * 50)
    
    try:
        from paper_trading.demo_paper_trading import run_quick_demo
        run_quick_demo()
        print("\n✅ Quick paper trading completed!")
    except Exception as e:
        print(f"❌ Error in paper trading: {e}")

def demo_market_scanner():
    """Run market scanner demo"""
    print("🔍 Market Scanner Demo")
    print("=" * 50)
    
    try:
        from scanner import Scanner
        from data_service import DataService
        from config import config
        
        # Initialize data service
        exchanges = config.get_all_exchanges()
        if not exchanges:
            print("❌ No exchanges configured")
            return
            
        exchange_name = list(exchanges.keys())[0]
        exchange_config = exchanges[exchange_name]
        
        print(f"🏦 Connecting to {exchange_name}...")
        
        data_service = DataService('ccxt', {
            'exchange_id': exchange_config.get('exchange', exchange_name),
            'api_key': exchange_config.get('api_key'),
            'api_secret': exchange_config.get('api_secret'),
            'testnet': exchange_config.get('testnet', True),
            'default_type': exchange_config.get('default_type', 'future')
        })
        
        scanner = Scanner(data_service)
        print("🔍 Scanning for opportunities...")
        opportunities = scanner.find_opportunities()
        
        print("\n📈 Top Trading Opportunities:")
        for exchange_id, symbols in opportunities.items():
            print(f"\n{exchange_id.upper()}:")
            for i, symbol in enumerate(symbols[:5], 1):
                print(f"  {i}. {symbol}")
                
        print("\n✅ Market scan completed!")
        
    except Exception as e:
        print(f"❌ Error in market scanner: {e}")

def demo_risk_analysis():
    """Run risk analysis demo"""
    print("⚠️  Risk Analysis Demo")
    print("=" * 50)
    
    try:
        from risk_manager import RiskManager
        import pandas as pd
        import numpy as np
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        prices = 50000 + np.cumsum(np.random.randn(100) * 100)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        risk_manager = RiskManager()
        
        print("📊 Analyzing BTC/USDT sample data...")
        
        # Calculate trade details for a buy signal
        trade_details = risk_manager.calculate_trade_details(df, 'BUY')
        
        if trade_details:
            print(f"\n💡 Trade Analysis Results:")
            print(f"  Signal: BUY")
            print(f"  Position Size: {trade_details['position_size']:.4f}")
            print(f"  Entry Price: ${trade_details['entry_price']:.2f}")
            print(f"  Stop Loss: ${trade_details['stop_loss']:.2f}")
            print(f"  Take Profit: ${trade_details['take_profit']:.2f}")
            print(f"  Risk Amount: ${trade_details.get('risk_amount', 0):.2f}")
            print(f"  Potential Reward: ${trade_details.get('potential_reward', 0):.2f}")
            
        print("\n✅ Risk analysis completed!")
        
    except Exception as e:
        print(f"❌ Error in risk analysis: {e}")

def main():
    """Main CLI entry point for demos"""
    parser = argparse.ArgumentParser(
        description="Augustan Trading Bot - CLI Demos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Demos:
  quick-backtest      Run a quick backtesting demo
  strategy-compare    Compare multiple strategies
  paper-trading       Run paper trading demo
  market-scan         Scan for trading opportunities
  risk-analysis       Analyze risk management
        """
    )
    
    parser.add_argument('demo', choices=[
        'quick-backtest', 'strategy-compare', 'paper-trading', 
        'market-scan', 'risk-analysis'
    ], help='Demo to run')
    
    args = parser.parse_args()
    
    demos = {
        'quick-backtest': demo_quick_backtest,
        'strategy-compare': demo_strategy_comparison,
        'paper-trading': demo_paper_trading_quick,
        'market-scan': demo_market_scanner,
        'risk-analysis': demo_risk_analysis
    }
    
    try:
        print(f"🤖 Augustan Trading Bot - {args.demo.replace('-', ' ').title()} Demo")
        print("=" * 60)
        demos[args.demo]()
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
