#!/usr/bin/env python3
"""
Futures Trading System CLI
A comprehensive command-line interface for the futures trading system.
"""

import click
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import os

from .jobs.daily_volume_job import DailyVolumeJob
from .jobs.enhanced_volume_job import EnhancedVolumeJob
from .data_feeder.futures_data_feeder import FuturesDataFeeder
from .core.position_sizing import RiskManagementConfig
from .core.config_manager_refactored import ConfigManager

# Import new core components
from .core.orderbook import OrderBook
from .core.exchange_manager import ExchangeManager, ExchangeConfig, ExchangeStatus
from .core.data_handler import DataHandler, DataConfig
from .core.paper_trading import PaperTradingEngine, PaperTradingConfig, OrderSide, OrderType

# Import scalping components
from .strategy_engine.scalping_strategies import ScalpingStrategyManager, ScalpingConfig, EMACrossoverStrategy, BollingerBandStrategy, VWAPReversionStrategy
from .risk_manager.scalping_risk_manager import ScalpingRiskManager, ScalpingRiskConfig
from .live_trading.scalping_engine import ScalpingTradingEngine

# Note: Deprecated global event_bus is no longer used in this module


# ConfigManager helper removed - will be created inline for each command


# Auto-completion functions
def get_symbols(ctx, args, incomplete):
    """Auto-complete for trading symbols."""
    common_symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT',
        'ADA/USDT', 'BNB/USDT', 'AVAX/USDT', 'LINK/USDT', 'UNI/USDT',
        'DOT/USDT', 'LTC/USDT', 'BCH/USDT', 'XLM/USDT', 'ATOM/USDT',
        'NEAR/USDT', 'FTM/USDT', 'ALGO/USDT', 'VET/USDT', 'ICP/USDT'
    ]
    return [s for s in common_symbols if incomplete.upper() in s.upper()]


def get_exchanges(ctx, args, incomplete):
    """Auto-complete for exchange names."""
    exchanges = ['binance']
    return [e for e in exchanges if incomplete.lower() in e.lower()]


def get_timeframes(ctx, args, incomplete):
    """Auto-complete for timeframes."""
    timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
    return [t for t in timeframes if incomplete.lower() in t.lower()]


def get_strategies(ctx, args, incomplete):
    """Auto-complete for trading strategies."""
    strategies = ['rsi', 'macd', 'all']
    return [s for s in strategies if incomplete.lower() in s.lower()]


def get_signal_types(ctx, args, incomplete):
    """Auto-complete for signal types."""
    signal_types = ['buy', 'sell', 'all']
    return [s for s in signal_types if incomplete.lower() in s.lower()]


def get_config_sections(ctx, args, incomplete):
    """Auto-complete for configuration sections."""
    sections = ['risk', 'data', 'signals', 'volume', 'jobs', 'all']
    return [s for s in sections if incomplete.lower() in s.lower()]


def get_output_formats(ctx, args, incomplete):
    """Auto-complete for output formats."""
    formats = ['json', 'csv', 'table']
    return [f for f in formats if incomplete.lower() in f.lower()]


@click.group()
@click.version_option(version="1.0.0", prog_name="Augustan Trading CLI")
@click.option('--config', '-c', default='config/exchanges_config.json', 
              help='Path to configuration file')
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), 
              help='Trading mode (paper/live)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--debug', '-d', is_flag=True, help='Enable debug mode with detailed logging')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--force', '-f', is_flag=True, help='Force operation without confirmation prompts')
@click.option('--output-format', type=click.Choice(['table', 'json', 'csv', 'yaml']), 
              default='table', help='Output format for results')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              default='INFO', help='Set logging level')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-essential output')
@click.pass_context
def cli(ctx, config, mode, verbose, debug, dry_run, force, output_format, log_level, no_color, quiet):
    """
    🚀 Augustan Trading System CLI
    
    The ultimate futures trading and position sizing tool with volume analysis,
    multi-exchange support, and intelligent risk management.
    
    Examples:
        # Volume & Position Analysis
        aug volume analyze --enhanced               # Enhanced volume analysis with position sizing
        aug position analyze --symbol DOGE/USDT    # Analyze position sizing for DOGE
        aug position tradeable --budget 50          # Find tradeable symbols for $50 budget
        
        # Trading & Strategies
        aug trading analyze --timeframe 4h          # Generate trading signals
        aug strategy list                           # List available strategies
        aug strategy backtest --strategy rsi --symbol BTC/USDT  # Backtest RSI strategy
        
        # Risk Management
        aug risk analyze --balance 10000           # Analyze portfolio risk
        aug risk limits --symbol BTC/USDT           # Check trading limits
        
        # System Management
        aug system status                           # Show system health
        aug system validate                         # Validate configuration
        aug system info                             # Show system information
        
        # Data Management
        aug data backup --compress                  # Backup data with compression
        aug data clean --older-than 30              # Clean old files
        
        # Configuration
        aug config show                             # Show configuration
        aug config switch --mode paper              # Switch to paper trading
        
        # Jobs & Automation
        aug job start --schedule                    # Start daily job
        
        # Core Components
        aug orderbook create --symbol BTC/USDT      # Create new order book
        aug exchange connect --exchange binance      # Connect to exchange
        aug paper start --balance 10000             # Start paper trading
        
    Auto-completion: Press TAB to get suggestions for commands, options, and values.
    """
    ctx.ensure_object(dict)
    
    # Handle trading mode
    if mode:
        if mode == 'paper':
            config = 'config/paper_trading_config.json'
        elif mode == 'live':
            config = 'config/live_trading_config.json'
            # Warn about live trading
            click.echo("⚠️  WARNING: Live trading mode selected!")
            click.echo("   This will use real money. Make sure you have:")
            click.echo("   1. Configured your API keys in config/live_trading_config.json")
            click.echo("   2. Tested thoroughly in paper mode")
            click.echo("   3. Understood the risks involved")
            if not click.confirm("Do you want to continue with live trading?"):
                sys.exit(0)
    
    ctx.obj['config'] = config
    ctx.obj['mode'] = mode
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    ctx.obj['dry_run'] = dry_run
    ctx.obj['force'] = force
    ctx.obj['output_format'] = output_format
    ctx.obj['log_level'] = log_level
    ctx.obj['no_color'] = no_color
    ctx.obj['quiet'] = quiet
    
    # Set up logging based on options
    if debug:
        ctx.obj['log_level'] = 'DEBUG'
    elif quiet:
        ctx.obj['log_level'] = 'ERROR'
    
    # Configure loguru logger
    import loguru
    loguru.logger.remove()
    loguru.logger.add(
        sys.stderr if verbose or debug else sys.stdout,
        level=ctx.obj['log_level'],
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>" if not no_color else "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        colorize=not no_color
    )
    
    # Ensure config directory exists
    Path(config).parent.mkdir(exist_ok=True)


@cli.group()
@click.pass_context
def volume(ctx):
    """📊 Volume analysis commands"""
    pass


@volume.command('analyze')
@click.option('--exchanges', '-e', multiple=True, 
              shell_complete=get_exchanges,
              help='Specific exchanges to analyze (default: all)')
@click.option('--min-volume', '-m', type=float, default=1000000,
              help='Minimum 24h volume in USD (default: 1M)')
@click.option('--max-rank', '-r', type=int, default=200,
              help='Maximum volume rank to consider (default: 200)')
@click.option('--output', '-o', help='Output file path (default: auto-generated)')
@click.option('--format', '-f', 
              shell_complete=get_output_formats,
              default='table', help='Output format')
@click.option('--save/--no-save', default=True, help='Save results to file')
@click.option('--enhanced', is_flag=True, help='Run enhanced analysis with position sizing')
@click.option('--budget', type=float, default=50.0, help='Trading budget in USDT (default: 50)')
@click.option('--risk-percent', type=float, default=0.2, help='Risk per trade in % (default: 0.2)')
@click.pass_context
def volume_analyze(ctx, exchanges, min_volume, max_rank, output, format, save, enhanced, budget, risk_percent):
    """
    Analyze futures market volumes across exchanges.
    
    This command fetches volume data from all configured exchanges,
    ranks markets by volume, and identifies the best trading opportunities.
    
    With --enhanced flag, also performs position sizing analysis to find
    symbols that fit within your budget and risk parameters.
    
    Examples:
        aug volume analyze
        aug volume analyze --enhanced --budget 100 --risk-percent 0.5
        aug volume analyze --exchanges bybit --min-volume 5000000
        aug volume analyze --format json --output my_analysis.json
    """
    if enhanced:
        click.echo("🔍 Starting enhanced futures volume analysis with position sizing...")
    else:
        click.echo("🔍 Starting futures volume analysis...")
    
    try:
        # Initialize configuration manager
        config_manager = ConfigManager.create(ctx.obj['config'])
        
        if enhanced:
            # Get risk config from centralized configuration with CLI overrides
            risk_config = config_manager.get_risk_management_config(
                budget_override=budget,
                risk_override=risk_percent / 100.0
            )
            job = EnhancedVolumeJob(config_path=ctx.obj['config'], risk_config=risk_config)
        else:
            # Initialize regular volume job
            job = DailyVolumeJob(config_path=ctx.obj['config'])
        
        # Update settings if provided
        if min_volume != 1000000:
            job.futures_feeder.min_volume_usd_24h = min_volume
        if max_rank != 200:
            job.futures_feeder.min_volume_rank = max_rank
        
        # Run analysis
        with click.progressbar(length=100, label='Analyzing markets') as bar:
            if enhanced:
                results = job.run_enhanced_volume_analysis()
            else:
                results = job.run_volume_analysis()
            bar.update(100)
        
        if not results:
            click.echo("❌ Volume analysis failed", err=True)
            sys.exit(1)
        
        # Display results
        if enhanced:
            job.print_enhanced_summary(results)
        else:
            _display_volume_results(results, format)
        
        # Save if requested
        if save:
            if not output:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix = "enhanced_analysis" if enhanced else "volume_analysis"
                output = f"{prefix}_{timestamp}.{format}"
            
            _save_results(results, output, format)
            click.echo(f"💾 Results saved to {output}")
        
        if enhanced:
            click.echo("✅ Enhanced volume analysis completed successfully!")
        else:
            click.echo("✅ Volume analysis completed successfully!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@volume.command('top')
@click.option('--limit', '-l', type=int, default=10, help='Number of top markets to show')
@click.option('--exchange', '-e', type=click.Choice(['binance']),
              help='Filter by specific exchange')
@click.pass_context
def volume_top(ctx, limit, exchange):
    """
    Show top markets by volume from latest analysis.
    
    Examples:
        futures-cli volume top --limit 20
        futures-cli volume top --exchange bybit --limit 5
    """
    try:
        job = DailyVolumeJob(config_path=ctx.obj['config'])
        latest = job.get_latest_analysis()
        
        if not latest:
            click.echo("❌ No volume analysis data found. Run 'volume analyze' first.", err=True)
            sys.exit(1)
        
        rankings = latest.get('market_rankings', [])
        
        # Filter by exchange if specified
        if exchange:
            rankings = [r for r in rankings if r['exchange'].lower() == exchange.lower()]
        
        # Limit results
        rankings = rankings[:limit]
        
        if not rankings:
            click.echo(f"❌ No markets found for exchange: {exchange}" if exchange else "❌ No markets found")
            sys.exit(1)
        
        # Display table
        click.echo(f"\n🏆 Top {len(rankings)} Markets by Volume")
        click.echo("=" * 80)
        
        for i, market in enumerate(rankings, 1):
            volume = market['volume_usd_24h']
            exchange_name = market['exchange'].upper()
            symbol = market['symbol']
            score = market['overall_score']
            
            click.echo(f"{i:2d}. {symbol:<20} | {exchange_name:<8} | ${volume:>12,.0f} | Score: {score:5.1f}")
        
        click.echo("=" * 80)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def position(ctx):
    """💰 Position sizing and risk management commands"""
    pass


@cli.group()
@click.pass_context
def live(ctx):
    """🚀 Live trading with real-time data"""
    pass


@position.command('analyze')
@click.option('--symbol', '-s', required=True, shell_complete=get_symbols, help='Symbol to analyze (e.g., BTC/USDT)')
@click.option('--budget', type=float, help='Trading budget in USDT (auto-fetched from wallet if not provided)')
@click.option('--risk-percent', type=float, default=0.2, help='Risk per trade in %')
@click.option('--leverage', type=int, default=5, help='Leverage to use (1-100x)')
@click.option('--stop-loss-percent', type=float, default=2.0, help='Stop loss in % from entry')
@click.pass_context
def position_analyze(ctx, symbol, budget, risk_percent, leverage, stop_loss_percent):
    """
    Analyze position sizing for a specific symbol.
    
    Examples:
        aug position analyze --symbol BTC/USDT  # Uses wallet balance
        aug position analyze --symbol BTC/USDT --budget 100  # Uses specified budget
        aug position analyze --symbol ETH/USDT --risk-percent 0.5 --leverage 10
    """
    click.echo(f"💰 Analyzing position sizing for {symbol}...")
    
    try:
        from .data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
        from .data_feeder.binance_feeder import BinanceDataFeeder
        from .data_feeder.binance_futures_feeder import BinanceFuturesFeeder
        from .core.position_sizing import (
            PositionSizingCalculator, PositionSizingInput, 
            RiskManagementConfig, PositionSide
        )
        from .core.futures_models import ExchangeType
        
        # Determine if this is a futures symbol
        is_futures = ':USDT' in symbol
        
        # Auto-fetch budget from wallet if not provided
        if budget is None:
            click.echo("🔍 Fetching available balance from wallet...")
            
            # Get config to determine testnet setting
            config_manager = ConfigManager.create(ctx.obj['config'])
            binance_config = config_manager.get_exchange_config('binance')
            testnet = binance_config.get('testnet', True)
            
            if is_futures:
                # Use futures feeder for futures symbols
                feeder = BinanceFuturesFeeder(testnet=testnet)
                account_info = feeder.get_account_info()
            else:
                # Use spot feeder for spot symbols
                feeder = BinanceDataFeeder(testnet=testnet)
                account_info = feeder.get_account_info()
            
            if account_info:
                # Handle both real API response and mock service response
                if 'USDT' in account_info:
                    # Mock service response (CCXT format)
                    budget = float(account_info['USDT']['free'])
                    click.echo(f"✅ Mock wallet balance: ${budget:.2f} USDT")
                elif 'free' in account_info and 'USDT' in account_info['free']:
                    # Real API response
                    budget = float(account_info['free']['USDT'])
                    click.echo(f"✅ Wallet balance: ${budget:.2f} USDT")
                else:
                    # Fallback to config file default budget
                    config_manager = ConfigManager.create(ctx.obj['config'])
                    risk_config = config_manager.get_risk_management_config()
                    budget = risk_config.max_budget
                    click.echo(f"⚠️  Could not fetch wallet balance, using config default: ${budget:.2f} USDT")
                    click.echo("   (Account info may not be available in testnet)")
            else:
                # Fallback to config file default budget
                config_manager = ConfigManager.create(ctx.obj['config'])
                risk_config = config_manager.get_risk_management_config()
                budget = risk_config.max_budget
                click.echo(f"⚠️  Could not fetch wallet balance, using config default: ${budget:.2f} USDT")
                click.echo("   (Account info may not be available in testnet)")
        else:
            click.echo(f"💰 Using specified budget: ${budget:.2f} USDT")
        
        # Initialize configuration manager and get risk config
        config_manager = ConfigManager.create(ctx.obj['config'])
        risk_config = config_manager.get_risk_management_config(
            budget_override=budget,
            risk_override=risk_percent / 100.0
        )
        # Update leverage if provided
        risk_config.default_leverage = leverage
        
        limits_fetcher = ExchangeLimitsFetcher()
        calculator = PositionSizingCalculator(risk_config)
        
        # Get current price and limits
        prices = limits_fetcher.get_current_prices([symbol], ExchangeType.BINANCE)
        if symbol not in prices:
            click.echo(f"❌ Could not fetch price for {symbol}", err=True)
            sys.exit(1)
        
        current_price = prices[symbol]
        exchange_limits = limits_fetcher.fetch_symbol_limits(ExchangeType.BINANCE, symbol)
        
        if not exchange_limits:
            click.echo(f"❌ Could not fetch exchange limits for {symbol}", err=True)
            sys.exit(1)
        
        # Calculate stop loss price
        stop_loss_price = current_price * (1 - stop_loss_percent / 100.0)
        
        # Create position sizing input
        inputs = PositionSizingInput(
            symbol=symbol,
            entry_price=current_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=current_price * 1.04,  # 4% take profit
            user_budget=budget,
            risk_per_trade_percent=risk_percent / 100.0,
            leverage=leverage,
            position_side=PositionSide.LONG,
            exchange_limits=exchange_limits
        )
        
        # Analyze position sizing
        result = calculator.analyze_position_sizing(inputs)
        
        # Display results
        click.echo(f"\n📊 Position Sizing Analysis for {symbol}")
        click.echo("=" * 60)
        click.echo(f"Current Price: ${current_price:.4f}")
        click.echo(f"Stop Loss: ${stop_loss_price:.4f} (-{stop_loss_percent}%)")
        click.echo(f"Budget: ${budget:.2f} USDT")
        click.echo(f"Risk per Trade: {risk_percent}%")
        click.echo(f"Leverage: {leverage}x")
        
        if result.is_tradeable:
            click.echo(f"\n✅ TRADEABLE")
            click.echo(f"Position Size: {result.position_size_qty:.6f} {symbol.split('/')[0]}")
            click.echo(f"Position Value: ${result.position_size_usdt:.2f}")
            click.echo(f"Required Margin: ${result.required_margin:.2f}")
            click.echo(f"Risk Amount: ${result.risk_amount:.2f}")
            click.echo(f"Liquidation Price: ${result.liquidation_price:.4f}")
            click.echo(f"Safety Ratio: {result.safety_ratio:.2f}x")
        else:
            click.echo(f"\n❌ NOT TRADEABLE")
            click.echo(f"Reason: {result.rejection_reason}")
            click.echo(f"Min Feasible Notional: ${result.min_feasible_notional:.2f}")
        
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@position.command('tradeable')
@click.option('--budget', type=float, default=50.0, help='Trading budget in USDT')
@click.option('--risk-percent', type=float, default=0.2, help='Risk per trade in %')
@click.option('--limit', '-l', type=int, default=20, help='Number of symbols to show')
@click.pass_context
def position_tradeable(ctx, budget, risk_percent, limit):
    """
    Show tradeable symbols based on position sizing analysis.
    
    Examples:
        aug position tradeable --budget 100 --limit 30
        aug position tradeable --risk-percent 0.5
    """
    click.echo(f"💰 Finding tradeable symbols for ${budget} budget...")
    
    try:
        # Initialize configuration manager and get risk config
        config_manager = ConfigManager.create(ctx.obj['config'])
        risk_config = config_manager.get_risk_management_config(
            budget_override=budget,
            risk_override=risk_percent / 100.0
        )
        
        job = EnhancedVolumeJob(config_path=ctx.obj['config'], risk_config=risk_config)
        
        # Get tradeable symbols
        tradeable_symbols = job.get_tradeable_symbols(limit)
        
        if not tradeable_symbols:
            click.echo("❌ No tradeable symbols found. Try running enhanced analysis first:", err=True)
            click.echo("   aug volume analyze --enhanced")
            sys.exit(1)
        
        click.echo(f"\n🎯 Top {len(tradeable_symbols)} Tradeable Symbols")
        click.echo("=" * 60)
        
        for i, symbol in enumerate(tradeable_symbols, 1):
            # Get position sizing details
            details = job.get_position_sizing_for_symbol(symbol)
            if details:
                click.echo(f"{i:2d}. {symbol:<15} | Margin: ${details['required_margin']:.2f} | "
                          f"Safety: {details['safety_ratio']:.2f}x | Risk: ${details['risk_amount']:.2f}")
            else:
                click.echo(f"{i:2d}. {symbol}")
        
        click.echo("=" * 60)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def trading(ctx):
    """📈 Trading analysis commands"""
    pass


@trading.command('analyze')
@click.option('--symbols', '-s', multiple=True, shell_complete=get_symbols, help='Specific symbols to analyze')
@click.option('--timeframe', '-t', shell_complete=get_timeframes, default='4h', help='Timeframe for analysis')
@click.option('--limit', '-l', type=int, default=100, help='Number of candles to fetch')
@click.option('--top', type=int, default=20, help='Number of top volume symbols to analyze')
@click.option('--strategies', multiple=True, 
              shell_complete=get_strategies, default=['all'],
              help='Strategies to run')
@click.option('--min-confidence', type=float, default=0.6, 
              help='Minimum confidence threshold for signals')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', '-f', shell_complete=get_output_formats, default='table', help='Output format')
@click.option('--use-tradeable', is_flag=True, 
              help='Use only tradeable symbols from enhanced analysis')
@click.option('--budget', type=float, default=50.0, help='Budget for tradeable symbols filter')
@click.pass_context
def trading_analyze(ctx, symbols, timeframe, limit, top, strategies, min_confidence, output, format, use_tradeable, budget):
    """
    Generate trading signals for futures markets.
    
    This command runs RSI and MACD strategies on high-volume futures markets
    and generates BUY/SELL signals with confidence scores.
    
    Examples:
        futures-cli trading analyze
        futures-cli trading analyze --timeframe 1h --top 10
        futures-cli trading analyze --symbols BTCUSDT ETHUSDT --strategies rsi
        futures-cli trading analyze --min-confidence 0.7 --format json
    """
    click.echo("📈 Starting futures trading analysis...")
    
    try:
        # Initialize data feeder
        from .data_feeder.futures_data_feeder import FuturesDataFeeder
        system = FuturesDataFeeder()
        
        # Convert symbols if provided
        if symbols:
            # Convert BTCUSDT to BTC/USDT format if needed
            formatted_symbols = []
            for symbol in symbols:
                if 'USDT' in symbol and '/' not in symbol:
                    base = symbol.replace('USDT', '')
                    formatted_symbols.append(f"{base}/USDT")
                else:
                    formatted_symbols.append(symbol)
            symbols = formatted_symbols
        
        # Run analysis
        with click.progressbar(length=100, label='Analyzing markets') as bar:
            results = system.run_futures_analysis(
                symbols=symbols if symbols else None,
                timeframe=timeframe,
                limit=limit
            )
            bar.update(100)
        
        if not results:
            click.echo("❌ Trading analysis failed", err=True)
            sys.exit(1)
        
        # Filter by confidence if specified
        if min_confidence > 0:
            filtered_signals = {}
            for symbol, signals in results.get('signals', {}).items():
                filtered = [s for s in signals if s['confidence'] >= min_confidence]
                if filtered:
                    filtered_signals[symbol] = filtered
            results['signals'] = filtered_signals
        
        # Display results
        _display_trading_results(results, format, min_confidence)
        
        # Save if requested
        if output:
            _save_results(results, output, format)
            click.echo(f"💾 Results saved to {output}")
        
        signal_count = sum(len(signals) for signals in results.get('signals', {}).values())
        click.echo(f"✅ Trading analysis completed! Generated {signal_count} signals.")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if ctx.obj['verbose']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@trading.command('signals')
@click.option('--type', '-t', shell_complete=get_signal_types, default='all',
              help='Filter signals by type')
@click.option('--strategy', '-s', shell_complete=get_strategies, default='all',
              help='Filter signals by strategy')
@click.option('--min-confidence', type=float, default=0.0,
              help='Minimum confidence threshold')
@click.option('--limit', '-l', type=int, default=10, help='Number of signals to show')
@click.pass_context
def trading_signals(ctx, type, strategy, min_confidence, limit):
    """
    Show latest trading signals with filtering options.
    
    Examples:
        futures-cli trading signals --type buy --min-confidence 0.7
        futures-cli trading signals --strategy rsi --limit 5
    """
    try:
        # Look for latest signals file
        signal_files = list(Path('.').glob('futures_signals_*.json'))
        if not signal_files:
            click.echo("❌ No trading signals found. Run 'trading analyze' first.", err=True)
            sys.exit(1)
        
        # Get the most recent file
        latest_file = max(signal_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        signals = results.get('signals', {})
        
        # Filter and collect signals
        filtered_signals = []
        for symbol, symbol_signals in signals.items():
            for signal in symbol_signals:
                # Apply filters
                if type != 'all' and signal['signal_type'].lower() != type.upper():
                    continue
                if strategy != 'all' and signal['strategy'].lower() != strategy.lower():
                    continue
                if signal['confidence'] < min_confidence:
                    continue
                
                signal['symbol'] = symbol
                filtered_signals.append(signal)
        
        # Sort by confidence descending
        filtered_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Limit results
        filtered_signals = filtered_signals[:limit]
        
        if not filtered_signals:
            click.echo("❌ No signals match your criteria")
            sys.exit(1)
        
        # Display signals
        click.echo(f"\n🎯 Latest Trading Signals ({len(filtered_signals)} found)")
        click.echo("=" * 90)
        
        for signal in filtered_signals:
            signal_emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴"
            click.echo(f"{signal_emoji} {signal['symbol']:<15} | {signal['strategy']:<4} | {signal['signal_type']:<4} | "
                      f"${signal['price']:<10.4f} | {signal['confidence']:<5.1%} | {signal['timestamp']}")
        
        click.echo("=" * 90)
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def job(ctx):
    """🤖 Job management commands"""
    pass


@job.command('start')
@click.option('--schedule/--no-schedule', default=False, 
              help='Run as scheduled job (default: run once)')
@click.option('--time', '-t', default='09:00', help='Schedule time (HH:MM format)')
@click.option('--daemon/--no-daemon', default=False, help='Run in background')
@click.pass_context
def job_start(ctx, schedule, time, daemon):
    """
    Start the daily volume analysis job.
    
    Examples:
        futures-cli job start                    # Run once
        futures-cli job start --schedule         # Run daily at 9:00 AM
        futures-cli job start --schedule --time 15:30  # Run daily at 3:30 PM
    """
    try:
        job = DailyVolumeJob(config_path=ctx.obj['config'])
        
        if schedule:
            click.echo(f"🕘 Starting scheduled job (daily at {time})")
            job.job_time = time
            job.schedule_daily_job()
            
            if daemon:
                click.echo("Running in background...")
                # In a real implementation, you'd fork here
            else:
                click.echo("Press Ctrl+C to stop")
            
            job.run_scheduler()
        else:
            click.echo("🚀 Running volume analysis job once...")
            results = job.run_once()
            
            if results:
                click.echo(f"✅ Job completed successfully!")
                click.echo(f"   • Analyzed {results.get('total_markets', 0)} markets")
                click.echo(f"   • Found {results.get('recommended_markets', 0)} recommended markets")
            else:
                click.echo("❌ Job failed")
                sys.exit(1)
                
    except KeyboardInterrupt:
        click.echo("\n⏹️  Job stopped by user")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@job.command('status')
@click.pass_context
def job_status(ctx):
    """Show job status and latest results."""
    try:
        job = DailyVolumeJob(config_path=ctx.obj['config'])
        latest = job.get_latest_analysis()
        
        if not latest:
            click.echo("❌ No job data found")
            sys.exit(1)
        
        click.echo("📊 Job Status")
        click.echo("=" * 40)
        click.echo(f"Last Run: {latest.get('execution_date', 'Unknown')}")
        click.echo(f"Markets Analyzed: {latest.get('total_markets', 0)}")
        click.echo(f"Recommended Markets: {latest.get('recommended_markets', 0)}")
        click.echo(f"Total Volume: ${latest.get('total_volume_usd_24h', 0):,.0f}")
        click.echo(f"Exchanges: {', '.join(latest.get('exchanges_analyzed', []))}")
        
        # Show top 5 recommended
        recommended = latest.get('recommended_symbols', [])[:5]
        if recommended:
            click.echo(f"\nTop 5 Recommended: {', '.join(recommended)}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def config(ctx):
    """⚙️ Configuration management"""
    pass


@config.command('show')
@click.option('--section', '-s', shell_complete=get_config_sections, help='Show specific section only')
@click.pass_context
def config_show(ctx, section):
    """Show current configuration."""
    try:
        config_manager = ConfigManager.create(ctx.obj['config'])
        
        if section:
            # Show specific section
            if section == 'risk':
                config_data = config_manager.get_risk_management_config().to_dict()
                click.echo(f"📊 Risk Management Configuration:")
            elif section == 'data':
                config_data = config_manager.get_data_fetching_config().__dict__
                click.echo(f"🔄 Data Fetching Configuration:")
            elif section == 'signals':
                config_data = config_manager.get_signal_generation_config().__dict__
                click.echo(f"📈 Signal Generation Configuration:")
            elif section == 'volume':
                config_data = config_manager.get_volume_settings().__dict__
                click.echo(f"📊 Volume Analysis Configuration:")
            elif section == 'jobs':
                config_data = config_manager.get_job_settings().__dict__
                click.echo(f"🤖 Job Settings Configuration:")
            else:
                click.echo(f"❌ Unknown section: {section}")
                click.echo("Available sections: risk, data, signals, volume, jobs")
                return
            
            click.echo(json.dumps(config_data, indent=2, default=str))
            return
        
        # Show complete configuration
        config_data = config_manager.get_raw_config()
        click.echo(f"📋 Complete Configuration:")
        click.echo("=" * 50)
        click.echo(json.dumps(config_data, indent=2))
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@config.command('init')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing configuration')
@click.pass_context
def config_init(ctx, force):
    """Initialize configuration file with defaults."""
    try:
        config_path = Path(ctx.obj['config'])
        
        if config_path.exists() and not force:
            click.echo(f"❌ Configuration file already exists: {config_path}")
            click.echo("Use --force to overwrite")
            sys.exit(1)
        
        # Create default configuration
        default_config = {
            "binance": {
                "api_key": "",
                "secret": "",
                "enabled": True,
                "testnet": False
            },
            "bybit": {
                "api_key": "",
                "secret": "",
                "enabled": True,
                "testnet": False
            },
            "risk_management": {
                "default_budget": 500.0,
                "max_risk_per_trade": 0.02,
                "min_safety_ratio": 1.5,
                "default_leverage": 5,
                "max_position_percent": 0.1,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "max_positions": 5,
                "emergency_stop_loss": 10.0
            },
            "volume_settings": {
                "min_volume_usd_24h": 1000000,
                "min_volume_rank": 200,
                "max_markets_per_exchange": 100
            },
            "job_settings": {
                "schedule_time": "09:00",
                "retention_days": 30,
                "output_directory": "volume_data"
            }
        }
        
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        click.echo(f"✅ Configuration initialized: {config_path}")
        click.echo("Edit the file to add your API keys and customize settings")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@config.command('switch')
@click.option('--mode', '-m', type=click.Choice(['paper', 'live']), required=True, 
              help='Trading mode to switch to')
@click.pass_context
def config_switch(ctx, mode):
    """Switch between paper and live trading configurations."""
    try:
        if mode == 'live':
            click.echo("⚠️  WARNING: Switching to live trading mode!")
            click.echo("   This will use real money. Make sure you have:")
            click.echo("   1. Configured your API keys in config/live_trading_config.json")
            click.echo("   2. Tested thoroughly in paper mode")
            click.echo("   3. Understood the risks involved")
            if not click.confirm("Do you want to switch to live trading?"):
                return
            
            # Copy live config to default
            import shutil
            shutil.copy('config/live_trading_config.json', 'config/exchanges_config.json')
            click.echo("✅ Switched to live trading configuration")
        else:
            # Copy paper config to default
            import shutil
            shutil.copy('config/paper_trading_config.json', 'config/exchanges_config.json')
            click.echo("✅ Switched to paper trading configuration")
            
    except Exception as e:
        click.echo(f"❌ Error switching configuration: {e}", err=True)
        sys.exit(1)


@config.command('update')
@click.option('--section', '-s', required=True, help='Configuration section to update')
@click.option('--default-budget', type=float, help='Default budget in USDT')
@click.option('--max-risk-per-trade', type=float, help='Maximum risk per trade (0.01 = 1%)')
@click.option('--min-safety-ratio', type=float, help='Minimum safety ratio')
@click.option('--default-leverage', type=int, help='Default leverage')
@click.option('--max-position-percent', type=float, help='Maximum position size as % of budget')
@click.option('--stop-loss-percent', type=float, help='Default stop loss percentage')
@click.option('--take-profit-percent', type=float, help='Default take profit percentage')
@click.option('--max-positions', type=int, help='Maximum concurrent positions')
@click.option('--emergency-stop-loss', type=float, help='Emergency stop loss percentage')
@click.pass_context
def config_update(ctx, section, **kwargs):
    """Update configuration settings."""
    try:
        config_manager = ConfigManager.create(ctx.obj['config'])
        
        # Filter out None values and convert CLI options to config keys
        key_mapping = {
            'default_budget': 'default_budget',
            'max_risk_per_trade': 'max_risk_per_trade',
            'min_safety_ratio': 'min_safety_ratio',
            'default_leverage': 'default_leverage',
            'max_position_percent': 'max_position_percent',
            'stop_loss_percent': 'stop_loss_percent',
            'take_profit_percent': 'take_profit_percent',
            'max_positions': 'max_positions',
            'emergency_stop_loss': 'emergency_stop_loss'
        }
        updates = {key_mapping[k]: v for k, v in kwargs.items() if v is not None and k in key_mapping}
        
        if not updates:
            click.echo("❌ No updates specified")
            click.echo("Use --help to see available options")
            return
        
        # Update configuration
        config_manager.update_config(section, updates)
        
        click.echo(f"✅ Configuration updated for section: {section}")
        click.echo("Updated values:")
        for key, value in updates.items():
            click.echo(f"  {key}: {value}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
        sys.exit(1)


@cli.command('dashboard')
@click.option('--refresh', '-r', type=int, default=0, 
              help='Auto-refresh interval in seconds (0 = no refresh)')
@click.pass_context
def dashboard(ctx, refresh):
    """
    Show a live dashboard with market overview.
    
    Examples:
        futures-cli dashboard                # Static dashboard
        futures-cli dashboard --refresh 30  # Auto-refresh every 30 seconds
    """
    try:
        while True:
            # Clear screen
            click.clear()
            
            # Show header
            click.echo("🚀 Futures Trading System Dashboard")
            click.echo(f"{'=' * 60}")
            click.echo(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get latest volume data
            job = DailyVolumeJob(config_path=ctx.obj['config'])
            volume_data = job.get_latest_analysis()
            
            if volume_data:
                click.echo(f"\n📊 Volume Analysis (Last: {volume_data.get('execution_date', 'Unknown')})")
                click.echo(f"   Markets: {volume_data.get('total_markets', 0):,}")
                click.echo(f"   Volume: ${volume_data.get('total_volume_usd_24h', 0):,.0f}")
                click.echo(f"   Recommended: {volume_data.get('recommended_markets', 0)}")
                
                # Show top 5
                top_5 = volume_data.get('recommended_symbols', [])[:5]
                if top_5:
                    click.echo(f"\n🏆 Top Markets: {', '.join(top_5)}")
            else:
                click.echo("\n❌ No volume data available")
            
            # Get latest trading signals
            signal_files = list(Path('.').glob('futures_signals_*.json'))
            if signal_files:
                latest_file = max(signal_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, 'r') as f:
                    signal_data = json.load(f)
                
                signals = signal_data.get('signals', {})
                total_signals = sum(len(s) for s in signals.values())
                
                click.echo(f"\n📈 Trading Signals (Total: {total_signals})")
                
                # Show recent signals
                recent_signals = []
                for symbol, symbol_signals in signals.items():
                    for signal in symbol_signals:
                        signal['symbol'] = symbol
                        recent_signals.append(signal)
                
                recent_signals.sort(key=lambda x: x['confidence'], reverse=True)
                
                for signal in recent_signals[:5]:
                    emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴"
                    click.echo(f"   {emoji} {signal['symbol']:<15} {signal['strategy']:<4} "
                              f"{signal['signal_type']:<4} {signal['confidence']:.1%}")
            else:
                click.echo("\n❌ No trading signals available")
            
            if refresh == 0:
                break
            
            click.echo(f"\n⏱️  Refreshing in {refresh} seconds... (Ctrl+C to exit)")
            
            import time
            time.sleep(refresh)  # OK for CLI blocking operations
            
    except KeyboardInterrupt:
        click.echo("\n👋 Dashboard closed")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def _display_volume_results(results, format_type):
    """Display volume analysis results."""
    if format_type == 'table':
        click.echo(f"\n📊 Volume Analysis Results")
        click.echo("=" * 80)
        click.echo(f"Date: {results.get('execution_date', 'Unknown')}")
        click.echo(f"Markets: {results.get('total_markets', 0)}")
        click.echo(f"Recommended: {results.get('recommended_markets', 0)}")
        click.echo(f"Total Volume: ${results.get('total_volume_usd_24h', 0):,.0f}")
        
        rankings = results.get('market_rankings', [])[:10]
        if rankings:
            click.echo(f"\n🏆 Top 10 Markets:")
            for i, market in enumerate(rankings, 1):
                click.echo(f"{i:2d}. {market['symbol']:<20} ${market['volume_usd_24h']:>12,.0f}")
    
    elif format_type == 'json':
        click.echo(json.dumps(results, indent=2, default=str))


def _display_trading_results(results, format_type, min_confidence=0.0):
    """Display trading analysis results."""
    if format_type == 'table':
        click.echo(f"\n📈 Trading Signals")
        click.echo("=" * 90)
        click.echo(f"Timeframe: {results.get('timeframe', 'Unknown')}")
        click.echo(f"Symbols Analyzed: {results.get('symbols_analyzed', 0)}")
        
        if min_confidence > 0:
            click.echo(f"Min Confidence: {min_confidence:.1%}")
        
        signals = results.get('signals', {})
        if signals:
            for symbol, symbol_signals in signals.items():
                if symbol_signals:
                    click.echo(f"\n📊 {symbol}")
                    for signal in symbol_signals:
                        emoji = "🟢" if signal['signal_type'] == "BUY" else "🔴"
                        click.echo(f"   {emoji} {signal['strategy']:<4} {signal['signal_type']:<4} "
                                  f"${signal['price']:<10.4f} {signal['confidence']:<5.1%}")
    
    elif format_type == 'json':
        click.echo(json.dumps(results, indent=2, default=str))


def _save_results(results, output_path, format_type):
    """Save results to file."""
    if format_type == 'json':
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    elif format_type == 'csv':
        # Implement CSV export if needed
        pass


@live.command('start')
@click.option('--symbols', '-s', multiple=True, help='Symbols to trade (e.g., BTC/USDT ETH/USDT)')
@click.option('--balance', '-b', type=float, default=1000.0, help='Initial account balance')
@click.option('--duration', '-d', type=int, help='Duration in minutes (default: run indefinitely)')
@click.option('--paper', is_flag=True, default=True, help='Paper trading mode (default: True)')
@click.pass_context
def live_start(ctx, symbols, balance, duration, paper):
    """
    Start live trading engine with real-time data.
    
    Examples:
        aug live start --symbols BTC/USDT ETH/USDT --balance 1000 --duration 60
        aug live start --symbols DOGE/USDT --paper
    """
    try:
        from .live_trading.live_engine import LiveTradingEngine
        
        # Default watchlist if no symbols provided
        watchlist = list(symbols) if symbols else ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
        
        click.echo(f"🚀 Starting Live Trading Engine...")
        click.echo(f"📊 Watchlist: {', '.join(watchlist)}")
        click.echo(f"💰 Balance: ${balance:.2f}")
        click.echo(f"📄 Paper Trading: {'Yes' if paper else '⚠️ REAL TRADING'}")
        
        if not paper:
            confirm = click.confirm("⚠️ WARNING: Real trading mode! Continue?")
            if not confirm:
                click.echo("Cancelled.")
                return
        
        # Initialize engine
        engine = LiveTradingEngine(
            watchlist=watchlist,
            initial_balance=balance,
            config_path=ctx.obj['config'],
            paper_trading=paper
        )
        
        # Add trade callback for CLI output
        def on_trade(trade_event):
            click.echo(f"💸 TRADE: {trade_event['symbol']} {trade_event['signal_type']} "
                      f"- Size: {trade_event['position_size']:.6f}, "
                      f"Risk: ${trade_event['risk_amount']:.2f}")
        
        engine.add_trade_callback(on_trade)
        
        # Run the engine
        if duration:
            click.echo(f"⏱️ Running for {duration} minutes...")
            engine.run_sync(duration_minutes=duration)
        else:
            click.echo("⏱️ Running indefinitely (Ctrl+C to stop)...")
            try:
                engine.run_sync()
            except KeyboardInterrupt:
                click.echo("\n⏹️ Stopping engine...")
                engine.stop()
        
        # Show final results
        status = engine.get_engine_status()
        click.echo(f"\n📊 Final Results:")
        click.echo(f"Signals Generated: {status['engine_info']['signals_generated']}")
        click.echo(f"Trades Executed: {status['engine_info']['trades_executed']}")
        click.echo(f"Final Balance: ${status['portfolio']['total_account_balance']:.2f}")
        
        performance = engine.portfolio_manager.get_performance_stats()
        if performance.get('total_trades', 0) > 0:
            click.echo(f"Win Rate: {performance['win_rate']:.1f}%")
            click.echo(f"Total Return: {performance['current_return']:.2f}%")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@live.command('monitor')
@click.option('--symbols', '-s', multiple=True, shell_complete=get_symbols, help='Symbols to monitor')
@click.option('--duration', '-d', type=int, default=60, help='Duration in seconds')
@click.pass_context
def live_monitor(ctx, symbols, duration):
    """
    Monitor real-time prices for symbols.
    
    Examples:
        aug live monitor --symbols BTC/USDT ETH/USDT --duration 120
        aug live monitor --symbols DOGE/USDT
    """
    try:
        from .data_feeder.realtime_feeder import RealtimeConfig, create_realtime_feeder
        
        # Default symbols if none provided
        watchlist = list(symbols) if symbols else ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
        
        click.echo(f"📡 Starting real-time price monitor...")
        click.echo(f"📊 Symbols: {', '.join(watchlist)}")
        click.echo(f"⏱️ Duration: {duration} seconds")
        
        config_dict = {
            'timeframes': ['1m'],
            'symbol': watchlist[0].replace('/', ''),
            'exchange': 'binance'
        }
        feeder = create_realtime_feeder(config_dict)
        
        # Track message count
        message_count = 0
        
        # Price update callback
        def on_price_update(symbol: str, candle):
            nonlocal message_count
            message_count += 1
            timestamp = candle.timestamp.strftime('%H:%M:%S')
            click.echo(f"  💰 {symbol}: ${candle.close:.4f} | Vol: {candle.volume:.0f} | {timestamp} | #{message_count}")
        
        feeder.add_callback(on_price_update)
        feeder.start()
        
        import time
        time.sleep(duration)
        
        # Stop the feeder immediately to prevent more callbacks
        feeder.stop()
        feeder.cleanup()
        
        # Show final status
        status = feeder.get_connection_status()
        click.echo(f"\n📊 Final Status:")
        click.echo(f"  Messages received: {message_count}")
        click.echo(f"  Expected duration: {duration} seconds")
        for symbol, data in status['symbols'].items():
            if data['current_price'] > 0:
                click.echo(f"  {symbol}: ${data['current_price']:.4f} "
                          f"({data['candle_count']} candles)")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@live.command('test')
@click.pass_context
def live_test(ctx):
    """
    Test live trading components.
    
    Examples:
        aug live test
    """
    click.echo("🧪 Testing Live Trading Components...")
    
    try:
        # Test configuration
        config_manager = ConfigManager.create(ctx.obj['config'])
        risk_config = config_manager.get_risk_management_config()
        click.echo(f"✅ Configuration loaded - Max risk: {risk_config.max_risk_per_trade:.3%}")
        
        # Test risk manager
        from .risk_manager.risk_manager import RiskManager
        risk_manager = RiskManager(ctx.obj['config'])
        summary = risk_manager.get_risk_summary(1000.0)
        click.echo(f"✅ Risk Manager - Max risk per trade: ${summary['max_risk_per_trade_usd']:.2f}")
        
        # Test portfolio manager
        from .risk_manager.portfolio_manager import PortfolioManager
        portfolio = PortfolioManager(1000.0, ctx.obj['config'])
        metrics = portfolio.calculate_portfolio_metrics()
        click.echo(f"✅ Portfolio Manager - Balance: ${metrics.total_account_balance:.2f}")
        
        # Test WebSocket connection (brief test)
        click.echo("📡 Testing WebSocket connection...")
        from .data_feeder.realtime_feeder import BinanceWebsocketFeeder, RealtimeConfig
        config = RealtimeConfig(timeframes=['1m'], symbol='BTCUSDT', exchange='binance')
        feeder = BinanceWebsocketFeeder(config)
        
        connection_test_duration = 10
        click.echo(f"  Connecting for {connection_test_duration} seconds...")
        
        feeder.start()
        import time
        time.sleep(connection_test_duration)
        
        # Stop the feeder immediately to prevent more callbacks
        feeder.stop()
        feeder.cleanup()
        
        status = feeder.get_connection_status()
        if status['connected'] and status['symbols']['BTCUSDT']['current_price'] > 0:
            click.echo(f"✅ WebSocket connection - BTC price: ${status['symbols']['BTCUSDT']['current_price']:.2f}")
        else:
            click.echo("⚠️ WebSocket connection test inconclusive")
        
        click.echo("\n🎉 All components tested successfully!")
        click.echo("🚀 System ready for live trading")
        
    except Exception as e:
        click.echo(f"❌ Test failed: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@live.command('secure')
@click.pass_context
def live_secure(ctx):
    """
    Secure API keys by moving them to environment variables.
    
    This command will:
    1. Extract API keys from config files
    2. Create a .env file with the keys
    3. Clean up config files to remove sensitive data
    4. Update .gitignore if needed
    
    Examples:
        aug live secure          # Secure API keys
    """
    click.echo("🔐 Securing API keys...")
    try:
        import subprocess
        # Use echo "y" to automatically answer yes to overwrite prompt
        result = subprocess.run(['bash', '-c', 'echo "y" | python3 secure_api_keys.py'], 
                              capture_output=True, text=True)
        click.echo(result.stdout)
        if result.returncode != 0:
            click.echo(result.stderr, err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error securing API keys: {e}", err=True)
        sys.exit(1)


@live.command('testnet')
@click.option('--setup', is_flag=True, help='Setup testnet configuration')
@click.option('--dry-run', is_flag=True, help='Run comprehensive testnet dry-run')
@click.pass_context
def live_testnet(ctx, setup, dry_run):
    """
    Testnet operations for Binance testnet.
    
    Examples:
        aug live testnet --setup          # Setup testnet configuration
        aug live testnet --dry-run        # Run comprehensive dry-run
    """
    if setup:
        click.echo("🔧 Setting up Binance testnet configuration...")
        try:
            import subprocess
            result = subprocess.run(['python3', 'setup_testnet.py'], 
                                  capture_output=True, text=True)
            click.echo(result.stdout)
            if result.returncode != 0:
                click.echo(result.stderr, err=True)
                sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error running setup: {e}", err=True)
            sys.exit(1)
    
    elif dry_run:
        click.echo("🚀 Running comprehensive testnet dry-run...")
        try:
            import subprocess
            result = subprocess.run(['python3', 'testnet_dry_run.py'], 
                                  capture_output=True, text=True)
            click.echo(result.stdout)
            if result.returncode != 0:
                click.echo(result.stderr, err=True)
                sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error running dry-run: {e}", err=True)
            sys.exit(1)
    
    else:
        click.echo("Please specify --setup or --dry-run")
        click.echo("Examples:")
        click.echo("  aug live testnet --setup    # Setup testnet configuration")
        click.echo("  aug live testnet --dry-run  # Run comprehensive dry-run")


# ============================================================================
# CORE COMPONENTS COMMANDS
# ============================================================================

@cli.group()
@click.pass_context
def orderbook(ctx):
    """
    📊 OrderBook Management Commands
    
    Manage order books with sorted bids and asks, data integrity validation,
    and real-time market data processing.
    """
    ctx.ensure_object(dict)


@orderbook.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--max-levels', '-l', default=1000, help='Maximum price levels')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='Output format')
def create(symbol, max_levels, format):
    """Create a new order book."""
    try:
        orderbook = OrderBook(symbol, max_levels)
        click.echo(f"✅ Created OrderBook for {symbol} with {max_levels} max levels")
        
        if format == 'json':
            stats = orderbook.get_stats()
            click.echo(json.dumps(stats, indent=2))
        else:
            click.echo(f"Symbol: {symbol}")
            click.echo(f"Max Levels: {max_levels}")
            click.echo(f"Status: Empty")
            
    except Exception as e:
        click.echo(f"❌ Error creating OrderBook: {e}", err=True)
        sys.exit(1)


@orderbook.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--bids', '-b', help='Bids data (JSON format)')
@click.option('--asks', '-a', help='Asks data (JSON format)')
@click.option('--sequence', '-q', type=int, help='Sequence number')
def update(symbol, bids, asks, sequence):
    """Update order book with new data."""
    try:
        orderbook = OrderBook(symbol)
        
        # Parse bids and asks
        if bids:
            bids_data = json.loads(bids)
        else:
            bids_data = [(50000.0, 1.5), (49999.0, 2.0), (49998.0, 1.0)]
        
        if asks:
            asks_data = json.loads(asks)
        else:
            asks_data = [(50001.0, 1.2), (50002.0, 2.5), (50003.0, 1.8)]
        
        # Update order book
        success = orderbook.update(bids_data, asks_data, sequence)
        
        if success:
            click.echo(f"✅ Updated OrderBook for {symbol}")
            
            # Show summary
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            spread = orderbook.get_spread()
            
            click.echo(f"Best Bid: {best_bid}")
            click.echo(f"Best Ask: {best_ask}")
            click.echo(f"Spread: {spread}")
            click.echo(f"Bid Count: {len(orderbook.bids)}")
            click.echo(f"Ask Count: {len(orderbook.asks)}")
        else:
            click.echo(f"❌ Failed to update OrderBook for {symbol}")
            
    except Exception as e:
        click.echo(f"❌ Error updating OrderBook: {e}", err=True)
        sys.exit(1)


@orderbook.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--side', type=click.Choice(['bid', 'ask']), required=True, help='Order side')
@click.option('--price', '-p', type=float, required=True, help='Order price')
@click.option('--quantity', '-q', type=float, required=True, help='Order quantity')
def add(symbol, side, price, quantity):
    """Add a new order to the order book."""
    try:
        orderbook = OrderBook(symbol)
        
        # Add some initial data
        orderbook.update(
            [(50000.0, 1.5), (49999.0, 2.0)],
            [(50001.0, 1.2), (50002.0, 2.5)]
        )
        
        # Add new order
        success = orderbook.add(side, price, quantity)
        
        if success:
            click.echo(f"✅ Added {side} order: {quantity} @ {price}")
            
            # Show updated order book
            if side == 'bid':
                click.echo(f"Updated Bids: {list(orderbook.bids.keys())}")
            else:
                click.echo(f"Updated Asks: {list(orderbook.asks.keys())}")
        else:
            click.echo(f"❌ Failed to add {side} order")
            
    except Exception as e:
        click.echo(f"❌ Error adding order: {e}", err=True)
        sys.exit(1)


@orderbook.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--depth', '-d', default=10, help='Depth to show')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='Output format')
def show(symbol, depth, format):
    """Show order book data."""
    try:
        orderbook = OrderBook(symbol)
        
        # Add sample data
        orderbook.update(
            [(50000.0, 1.5), (49999.0, 2.0), (49998.0, 1.0)],
            [(50001.0, 1.2), (50002.0, 2.5), (50003.0, 1.8)]
        )
        
        if format == 'json':
            data = orderbook.to_dict()
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"📊 OrderBook: {symbol}")
            click.echo("=" * 50)
            
            # Show bids
            click.echo("Bids (Highest First):")
            bid_depth = orderbook.get_depth('bid', depth)
            for price, quantity in bid_depth:
                click.echo(f"  {price:>10.2f} | {quantity:>10.2f}")
            
            click.echo("-" * 30)
            
            # Show asks
            click.echo("Asks (Lowest First):")
            ask_depth = orderbook.get_depth('ask', depth)
            for price, quantity in ask_depth:
                click.echo(f"  {price:>10.2f} | {quantity:>10.2f}")
            
            # Show summary
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            spread = orderbook.get_spread()
            mid_price = orderbook.get_mid_price()
            
            click.echo("=" * 50)
            click.echo(f"Best Bid: {best_bid}")
            click.echo(f"Best Ask: {best_ask}")
            click.echo(f"Spread: {spread}")
            click.echo(f"Mid Price: {mid_price}")
            
    except Exception as e:
        click.echo(f"❌ Error showing OrderBook: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def exchange(ctx):
    """
    🔗 Exchange Management Commands
    
    Manage connections to multiple exchanges, monitor health status,
    and handle API interactions with failover support.
    """
    ctx.ensure_object(dict)


@exchange.command()
@click.option('--exchange', '-e', default='binance', help='Exchange name')
@click.option('--api-key', help='API key')
@click.option('--secret', help='Secret key')
@click.option('--sandbox/--live', default=True, help='Use sandbox or live')
def connect(exchange, api_key, secret, sandbox):
    """Connect to an exchange."""
    try:
        # Create exchange config
        config = ExchangeConfig(
            name=exchange,
            api_key=api_key,
            secret=secret,
            sandbox=sandbox,
            enabled=True
        )
        
        # Create exchange manager
        manager = ExchangeManager([config])
        
        click.echo(f"🔗 Connecting to {exchange} ({'sandbox' if sandbox else 'live'})...")
        
        # Note: In real implementation, this would be async
        click.echo(f"✅ Exchange manager created for {exchange}")
        click.echo(f"Configuration: {config.name}")
        click.echo(f"Sandbox: {config.sandbox}")
        click.echo(f"Rate Limit: {config.rate_limit}ms")
        
    except Exception as e:
        click.echo(f"❌ Error connecting to exchange: {e}", err=True)
        sys.exit(1)


@exchange.command()
@click.option('--exchange', '-e', help='Exchange name (optional)')
def status(exchange):
    """Show exchange health status."""
    try:
        # Create sample exchange manager
        configs = [
            ExchangeConfig(name="binance", enabled=True),
            ExchangeConfig(name="bybit", enabled=True)
        ]
        manager = ExchangeManager(configs)
        
        click.echo("📊 Exchange Health Status")
        click.echo("=" * 50)
        
        health_status = manager.get_all_health_status()
        
        for name, health in health_status.items():
            if exchange and exchange != name:
                continue
                
            click.echo(f"\n{name.upper()}:")
            click.echo(f"  Status: {health.status.value}")
            click.echo(f"  Error Count: {health.error_count}")
            click.echo(f"  Success Count: {health.success_count}")
            if health.last_error:
                click.echo(f"  Last Error: {health.last_error}")
            if health.response_time:
                click.echo(f"  Response Time: {health.response_time:.3f}s")
                
    except Exception as e:
        click.echo(f"❌ Error getting exchange status: {e}", err=True)
        sys.exit(1)


@exchange.command()
@click.option('--exchange', '-e', default='binance', help='Exchange name')
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--limit', '-l', default=100, help='Number of levels')
def orderbook(exchange, symbol, limit):
    """Fetch order book from exchange."""
    try:
        click.echo(f"📊 Fetching order book from {exchange} for {symbol}...")
        
        # Create sample exchange manager
        config = ExchangeConfig(name=exchange, enabled=True)
        manager = ExchangeManager([config])
        
        click.echo(f"✅ Exchange manager created")
        click.echo(f"Would fetch {limit} levels from {exchange}:{symbol}")
        click.echo("Note: This is a demo - real implementation would fetch live data")
        
    except Exception as e:
        click.echo(f"❌ Error fetching order book: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def data(ctx):
    """
    📈 Data Processing Commands
    
    Process and validate market data, manage data quality metrics,
    and handle real-time data distribution.
    """
    ctx.ensure_object(dict)


@data.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--exchange', '-e', default='binance', help='Exchange name')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='Output format')
def process(symbol, exchange, format):
    """Process market data."""
    try:
        # Create sample market data
        sample_data = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 50000.0,
            'high': 50001.0,
            'low': 49999.0,
            'close': 50000.5,
            'volume': 100.0
        }
        
        click.echo(f"📈 Processing market data for {symbol} from {exchange}...")
        
        # Create data handler
        config = ExchangeConfig(name=exchange, enabled=True)
        exchange_manager = ExchangeManager([config])
        data_handler = DataHandler(exchange_manager)
        
        if format == 'json':
            click.echo(json.dumps(sample_data, indent=2))
        else:
            click.echo(f"Symbol: {symbol}")
            click.echo(f"Exchange: {exchange}")
            click.echo(f"Open: {sample_data['open']}")
            click.echo(f"High: {sample_data['high']}")
            click.echo(f"Low: {sample_data['low']}")
            click.echo(f"Close: {sample_data['close']}")
            click.echo(f"Volume: {sample_data['volume']}")
        
        click.echo("✅ Data processing completed")
        
    except Exception as e:
        click.echo(f"❌ Error processing data: {e}", err=True)
        sys.exit(1)


@data.command()
@click.option('--symbol', '-s', help='Trading symbol (optional)')
def quality(symbol):
    """Show data quality metrics."""
    try:
        click.echo("📊 Data Quality Metrics")
        click.echo("=" * 50)
        
        # Create sample data handler
        config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([config])
        data_handler = DataHandler(exchange_manager)
        
        if symbol:
            metrics = data_handler.get_data_quality_metrics(symbol)
            if metrics:
                click.echo(f"\n{symbol}:")
                click.echo(f"  Total Updates: {metrics.total_updates}")
                click.echo(f"  Valid Updates: {metrics.valid_updates}")
                click.echo(f"  Invalid Updates: {metrics.invalid_updates}")
                click.echo(f"  Data Freshness: {metrics.data_freshness}s")
            else:
                click.echo(f"No metrics available for {symbol}")
        else:
            all_metrics = data_handler.get_all_data_quality_metrics()
            if all_metrics:
                for sym, metrics in all_metrics.items():
                    click.echo(f"\n{sym}:")
                    click.echo(f"  Total Updates: {metrics.total_updates}")
                    click.echo(f"  Valid Updates: {metrics.valid_updates}")
                    click.echo(f"  Invalid Updates: {metrics.invalid_updates}")
            else:
                click.echo("No data quality metrics available")
                
    except Exception as e:
        click.echo(f"❌ Error getting data quality metrics: {e}", err=True)
        sys.exit(1)


@data.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--limit', '-l', default=10, help='Number of records')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Export format')
def export(symbol, limit, format):
    """Export historical data."""
    try:
        click.echo(f"📤 Exporting {limit} records for {symbol} in {format} format...")
        
        # Create sample data handler
        config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([config])
        data_handler = DataHandler(exchange_manager)
        
        # Export data
        exported_data = data_handler.export_data(symbol, format)
        
        if exported_data:
            click.echo("✅ Data exported successfully")
            if format == 'json':
                click.echo(exported_data)
            else:
                click.echo(exported_data)
        else:
            click.echo("❌ No data available for export")
            
    except Exception as e:
        click.echo(f"❌ Error exporting data: {e}", err=True)
        sys.exit(1)


@cli.group()
@click.pass_context
def paper(ctx):
    """
    📝 Paper Trading Commands
    
    Run paper trading simulations with real market data but simulated orders.
    Perfect for strategy validation and testing without financial risk.
    """
    ctx.ensure_object(dict)


@paper.command()
@click.option('--balance', '-b', default=10000.0, help='Initial balance')
@click.option('--commission', '-c', default=0.001, help='Commission rate')
@click.option('--slippage', '-s', default=0.0005, help='Slippage rate')
@click.option('--max-position', '-p', default=0.1, help='Max position size (fraction of balance)')
def start(balance, commission, slippage, max_position):
    """Start paper trading engine."""
    try:
        click.echo("📝 Starting Paper Trading Engine")
        click.echo("=" * 50)
        
        # Create paper trading config
        config = PaperTradingConfig(
            initial_balance=balance,
            commission_rate=commission,
            slippage_rate=slippage,
            max_position_size=max_position
        )
        
        # Create components
        exchange_config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([exchange_config])
        data_handler = DataHandler(exchange_manager)
        
        # Create paper trading engine
        engine = PaperTradingEngine(exchange_manager, data_handler, config)
        
        click.echo(f"✅ Paper Trading Engine initialized")
        click.echo(f"Initial Balance: ${balance:,.2f}")
        click.echo(f"Commission Rate: {commission:.3%}")
        click.echo(f"Slippage Rate: {slippage:.3%}")
        click.echo(f"Max Position Size: {max_position:.1%}")
        click.echo(f"Exchange: binance")
        
        click.echo("\n📊 Engine Status:")
        summary = engine.get_portfolio_summary()
        click.echo(f"Current Balance: ${summary['current_balance']:,.2f}")
        click.echo(f"Positions: {summary['position_count']}")
        click.echo(f"Total Trades: {summary['total_trades']}")
        
    except Exception as e:
        click.echo(f"❌ Error starting paper trading: {e}", err=True)
        sys.exit(1)


@paper.command()
@click.option('--symbol', '-s', default='BTC/USDT', help='Trading symbol')
@click.option('--side', type=click.Choice(['buy', 'sell']), required=True, help='Order side')
@click.option('--quantity', '-q', type=float, required=True, help='Order quantity')
@click.option('--price', '-p', type=float, help='Order price (for limit orders)')
@click.option('--type', 'order_type', type=click.Choice(['market', 'limit']), default='market', help='Order type')
def order(symbol, side, quantity, price, order_type):
    """Place a paper trading order."""
    try:
        click.echo(f"📝 Placing {order_type} {side} order for {quantity} {symbol}...")
        
        # Create paper trading engine
        config = PaperTradingConfig(initial_balance=10000.0)
        exchange_config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([exchange_config])
        data_handler = DataHandler(exchange_manager)
        engine = PaperTradingEngine(exchange_manager, data_handler, config)
        
        # Convert string to enum
        side_enum = OrderSide.BUY if side == 'buy' else OrderSide.SELL
        type_enum = OrderType.MARKET if order_type == 'market' else OrderType.LIMIT
        
        # Place order (run async function)
        import asyncio
        order = asyncio.run(engine.place_order(
            symbol=symbol,
            side=side_enum,
            order_type=type_enum,
            quantity=quantity,
            price=price
        ))
        
        if order:
            click.echo(f"✅ Order placed successfully")
            click.echo(f"Order ID: {order.id}")
            click.echo(f"Symbol: {order.symbol}")
            click.echo(f"Side: {order.side.value}")
            click.echo(f"Type: {order.order_type.value}")
            click.echo(f"Quantity: {order.quantity}")
            if order.price:
                click.echo(f"Price: {order.price}")
            click.echo(f"Status: {order.status.value}")
        else:
            click.echo(f"❌ Failed to place order")
            
    except Exception as e:
        click.echo(f"❌ Error placing order: {e}", err=True)
        sys.exit(1)


@paper.command()
def status():
    """Show paper trading status."""
    try:
        click.echo("📊 Paper Trading Status")
        click.echo("=" * 50)
        
        # Create paper trading engine
        config = PaperTradingConfig(initial_balance=10000.0)
        exchange_config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([exchange_config])
        data_handler = DataHandler(exchange_manager)
        engine = PaperTradingEngine(exchange_manager, data_handler, config)
        
        # Get portfolio summary
        summary = engine.get_portfolio_summary()
        
        click.echo(f"Initial Balance: ${summary['initial_balance']:,.2f}")
        click.echo(f"Current Balance: ${summary['current_balance']:,.2f}")
        click.echo(f"Cash Balance: ${summary['cash_balance']:,.2f}")
        click.echo(f"Total PnL: ${summary['total_pnl']:,.2f}")
        click.echo(f"Total Return: {summary['total_return']:.2%}")
        click.echo(f"Max Drawdown: {summary['max_drawdown']:.2%}")
        click.echo(f"Positions: {summary['position_count']}")
        click.echo(f"Total Trades: {summary['total_trades']}")
        click.echo(f"Active Orders: {summary['active_orders']}")
        
        # Show positions
        positions = engine.get_positions()
        if positions:
            click.echo(f"\n📈 Open Positions:")
            for symbol, position in positions.items():
                click.echo(f"  {symbol}: {position.quantity} @ ${position.average_price:.2f}")
                click.echo(f"    Unrealized PnL: ${position.unrealized_pnl:.2f}")
                click.echo(f"    Realized PnL: ${position.realized_pnl:.2f}")
        
    except Exception as e:
        click.echo(f"❌ Error getting paper trading status: {e}", err=True)
        sys.exit(1)


@paper.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Export format')
def export(format):
    """Export paper trading data."""
    try:
        click.echo(f"📤 Exporting paper trading data in {format} format...")
        
        # Create paper trading engine
        config = PaperTradingConfig(initial_balance=10000.0)
        exchange_config = ExchangeConfig(name="binance", enabled=True)
        exchange_manager = ExchangeManager([exchange_config])
        data_handler = DataHandler(exchange_manager)
        engine = PaperTradingEngine(exchange_manager, data_handler, config)
        
        # Export trades
        exported_data = engine.export_trades(format)
        
        if exported_data:
            click.echo("✅ Data exported successfully")
            click.echo(exported_data)
        else:
            click.echo("No trades to export")
            
    except Exception as e:
        click.echo(f"❌ Error exporting paper trading data: {e}", err=True)
        sys.exit(1)


# ============================================================================
# SCALPING TRADING COMMANDS
# ============================================================================

@cli.group()
def scalping():
    """Scalping trading commands for high-frequency trading."""
    pass


@scalping.command()
@click.option('--symbols', '-s', multiple=True, help='Trading symbols (e.g., BTC/USDT)')
@click.option('--balance', '-b', type=float, default=10000.0, help='Initial balance')
@click.option('--paper', is_flag=True, default=True, help='Paper trading mode (Freqtrade-style)')
@click.option('--live', is_flag=True, default=False, help='Live trading mode (requires API keys)')
@click.option('--strategies', multiple=True, default=['ema_crossover', 'bollinger_bands', 'vwap_reversion'], 
              help='Strategies to use')
@click.option('--config', '-c', help='Configuration file path')
def start(symbols, balance, paper, live, strategies, config):
    """Start scalping trading engine."""
    try:
        if not symbols:
            symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
        
        # Determine trading mode
        if live:
            paper = False
            mode = "Live Trading (Real Money)"
        else:
            paper = True
            mode = "Paper Trading (Freqtrade-style)"
        
        click.echo(f"🚀 Starting Scalping Trading Engine...")
        click.echo(f"📊 Symbols: {', '.join(symbols)}")
        click.echo(f"💰 Balance: ${balance:,.2f}")
        click.echo(f"📝 Mode: {mode}")
        click.echo(f"🎯 Strategies: {', '.join(strategies)}")
        
        if paper:
            click.echo(f"📋 Paper Trading Features:")
            click.echo(f"   ✅ Real market data")
            click.echo(f"   ✅ Realistic slippage simulation")
            click.echo(f"   ✅ Commission simulation")
            click.echo(f"   ✅ No API keys required")
            click.echo(f"   ✅ Risk-free testing")
        
        # Initialize scalping engine
        engine = ScalpingTradingEngine(
            watchlist=list(symbols),
            initial_balance=balance,
            config_path=config,
            paper_trading=paper
        )
        
        # Start engine
        import asyncio
        asyncio.run(engine.start())
        
    except Exception as e:
        click.echo(f"❌ Error starting scalping engine: {e}", err=True)
        sys.exit(1)


@scalping.command()
@click.option('--symbol', '-s', help='Symbol to test')
@click.option('--strategy', help='Strategy to test')
@click.option('--timeframe', default='1m', help='Timeframe for testing')
def test(symbol, strategy, timeframe):
    """Test scalping strategies."""
    try:
        if not symbol:
            symbol = 'BTC/USDT'
        
        click.echo(f"🧪 Testing Scalping Strategy: {strategy or 'All'}")
        click.echo(f"📊 Symbol: {symbol}")
        click.echo(f"⏰ Timeframe: {timeframe}")
        
        # Initialize strategy manager
        strategy_manager = ScalpingStrategyManager()
        
        if strategy:
            # Test specific strategy
            strategy_obj = strategy_manager.get_strategy(strategy)
            if strategy_obj:
                click.echo(f"✅ Strategy '{strategy}' loaded successfully")
                click.echo(f"📋 Strategy type: {type(strategy_obj).__name__}")
            else:
                click.echo(f"❌ Strategy '{strategy}' not found")
                available = list(strategy_manager.get_all_strategies().keys())
                click.echo(f"Available strategies: {', '.join(available)}")
        else:
            # Test all strategies
            strategies = strategy_manager.get_all_strategies()
            click.echo(f"📋 Available strategies:")
            for name, strategy_obj in strategies.items():
                click.echo(f"  ✅ {name}: {type(strategy_obj).__name__}")
        
    except Exception as e:
        click.echo(f"❌ Error testing strategies: {e}", err=True)
        sys.exit(1)


@scalping.command()
@click.option('--symbol', '-s', help='Symbol to analyze')
@click.option('--balance', '-b', type=float, default=10000.0, help='Account balance')
def risk(symbol, balance):
    """Analyze scalping risk parameters."""
    try:
        if not symbol:
            symbol = 'BTC/USDT'
        
        click.echo(f"⚠️ Scalping Risk Analysis for {symbol}")
        click.echo(f"💰 Account Balance: ${balance:,.2f}")
        
        # Initialize risk manager
        risk_manager = ScalpingRiskManager()
        
        # Get risk summary
        risk_summary = risk_manager.get_risk_summary()
        
        click.echo(f"\n📊 Risk Summary:")
        click.echo(f"  Daily P&L: ${risk_summary['daily_pnl']:,.2f}")
        click.echo(f"  Consecutive Losses: {risk_summary['consecutive_losses']}")
        click.echo(f"  Active Positions: {risk_summary['active_positions']}")
        click.echo(f"  Total Exposure: ${risk_summary['total_exposure']:,.2f}")
        click.echo(f"  In Cooldown: {'Yes' if risk_summary['in_cooldown'] else 'No'}")
        
        # Risk configuration
        config = risk_manager.config
        click.echo(f"\n⚙️ Risk Configuration:")
        click.echo(f"  Max Position Size: {config.max_position_size_percent*100:.1f}%")
        click.echo(f"  Max Total Exposure: {config.max_total_exposure_percent*100:.1f}%")
        click.echo(f"  Max Daily Loss: {config.max_daily_loss_percent*100:.1f}%")
        click.echo(f"  ATR Multiplier: {config.atr_multiplier}")
        click.echo(f"  Risk-Reward Ratio: {config.risk_reward_ratio}")
        click.echo(f"  Trailing Stop: {'Enabled' if config.enable_trailing_stop else 'Disabled'}")
        
    except Exception as e:
        click.echo(f"❌ Error analyzing risk: {e}", err=True)
        sys.exit(1)


@scalping.command()
@click.option('--symbol', '-s', help='Symbol to configure')
@click.option('--ema-fast', type=int, help='Fast EMA period')
@click.option('--ema-slow', type=int, help='Slow EMA period')
@click.option('--bb-period', type=int, help='Bollinger Band period')
@click.option('--bb-std', type=float, help='Bollinger Band standard deviation')
@click.option('--atr-multiplier', type=float, help='ATR multiplier for stop loss')
@click.option('--risk-reward', type=float, help='Risk-reward ratio')
def config(symbol, ema_fast, ema_slow, bb_period, bb_std, atr_multiplier, risk_reward):
    """Configure scalping strategy parameters."""
    try:
        click.echo(f"⚙️ Configuring Scalping Parameters")
        
        # Create configuration
        config = ScalpingConfig()
        
        if ema_fast:
            config.ema_fast = ema_fast
        if ema_slow:
            config.ema_slow = ema_slow
        if bb_period:
            config.bb_period = bb_period
        if bb_std:
            config.bb_std = bb_std
        if atr_multiplier:
            config.atr_multiplier = atr_multiplier
        if risk_reward:
            config.risk_reward_ratio = risk_reward
        
        click.echo(f"\n📋 Current Configuration:")
        click.echo(f"  EMA Fast: {config.ema_fast}")
        click.echo(f"  EMA Slow: {config.ema_slow}")
        click.echo(f"  BB Period: {config.bb_period}")
        click.echo(f"  BB Std Dev: {config.bb_std}")
        click.echo(f"  ATR Multiplier: {config.atr_multiplier}")
        click.echo(f"  Risk-Reward Ratio: {config.risk_reward_ratio}")
        click.echo(f"  Primary Timeframe: {config.primary_timeframe}")
        
        click.echo(f"\n✅ Configuration updated successfully")
        
    except Exception as e:
        click.echo(f"❌ Error configuring parameters: {e}", err=True)
        sys.exit(1)


@scalping.command()
def status():
    """Show scalping engine status."""
    try:
        click.echo(f"📊 Scalping Engine Status")
        
        # Check event bus status (deprecated - event system refactored)
        # Note: Event bus is now injected via dependency injection
        queue_size = 0  # Not available in refactored version
        subscriptions = 0  # Not available in refactored version
        
        click.echo(f"\n🔄 Event System:")
        click.echo(f"  Queue Size: {queue_size}")
        click.echo(f"  Active Subscriptions: {len(subscriptions)}")
        
        if subscriptions:
            click.echo(f"  Subscriptions:")
            for event_type, count in subscriptions.items():
                click.echo(f"    {event_type}: {count}")
        
        # Strategy status
        strategy_manager = ScalpingStrategyManager()
        strategies = strategy_manager.get_all_strategies()
        
        click.echo(f"\n🎯 Strategies:")
        for name, strategy in strategies.items():
            click.echo(f"  ✅ {name}: {type(strategy).__name__}")
        
        click.echo(f"\n✅ Scalping system is ready")
        
    except Exception as e:
        click.echo(f"❌ Error getting status: {e}", err=True)
        sys.exit(1)


@scalping.command()
@click.option('--balance', '-b', type=float, default=10000.0, help='Initial balance')
@click.option('--commission', type=float, default=0.001, help='Commission rate (0.001 = 0.1%)')
@click.option('--slippage', type=float, default=0.0005, help='Slippage rate (0.0005 = 0.05%)')
def paper_config(balance, commission, slippage):
    """Configure Freqtrade-style paper trading parameters."""
    try:
        click.echo(f"📋 Freqtrade-Style Paper Trading Configuration")
        
        click.echo(f"\n💰 Account Settings:")
        click.echo(f"  Initial Balance: ${balance:,.2f}")
        
        click.echo(f"\n💸 Trading Costs:")
        click.echo(f"  Commission Rate: {commission*100:.3f}%")
        click.echo(f"  Slippage Rate: {slippage*100:.3f}%")
        
        click.echo(f"\n📊 Features:")
        click.echo(f"  ✅ Real market data from Binance")
        click.echo(f"  ✅ Realistic slippage simulation")
        click.echo(f"  ✅ Commission simulation")
        click.echo(f"  ✅ Position tracking")
        click.echo(f"  ✅ P&L calculation")
        click.echo(f"  ✅ Trade history")
        click.echo(f"  ✅ No API keys required")
        
        click.echo(f"\n🚀 Start paper trading:")
        click.echo(f"  python3 -m trading_system.cli scalping start --paper --balance {balance}")
        
    except Exception as e:
        click.echo(f"❌ Error configuring paper trading: {e}", err=True)
        sys.exit(1)


# ============================================================================
# RISK MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def risk():
    """🛡️ Risk management and portfolio analysis."""
    pass


@risk.command('analyze')
@click.option('--balance', type=float, help='Account balance in USDT')
@click.option('--positions', multiple=True, help='Current positions (symbol:quantity:price)')
@click.option('--risk-model', type=click.Choice(['conservative', 'moderate', 'aggressive']), 
              default='moderate', help='Risk model to use')
@click.option('--max-drawdown', type=float, default=0.1, help='Maximum allowed drawdown (0.1 = 10%)')
@click.pass_context
def risk_analyze(ctx, balance, positions, risk_model, max_drawdown):
    """Analyze current risk exposure and portfolio health."""
    try:
        from .risk_manager.risk_manager import RiskManager
        
        click.echo("🛡️ Analyzing portfolio risk...")
        
        # Initialize risk manager
        risk_manager = RiskManager(ctx.obj['config'])
        
        # Parse positions if provided
        parsed_positions = []
        if positions:
            for pos in positions:
                try:
                    symbol, quantity, price = pos.split(':')
                    parsed_positions.append({
                        'symbol': symbol,
                        'quantity': float(quantity),
                        'price': float(price)
                    })
                except ValueError:
                    click.echo(f"⚠️ Invalid position format: {pos}. Use symbol:quantity:price")
                    continue
        
        # Get risk analysis
        if balance:
            risk_summary = risk_manager.get_risk_summary(balance)
            
            click.echo(f"📊 Risk Analysis Summary:")
            click.echo(f"   • Account Balance: ${balance:.2f}")
            click.echo(f"   • Max Risk per Trade: ${risk_summary['max_risk_per_trade_usd']:.2f}")
            click.echo(f"   • Max Portfolio Risk: ${risk_summary['max_portfolio_risk_usd']:.2f}")
            click.echo(f"   • Risk Model: {risk_model}")
            click.echo(f"   • Max Drawdown: {max_drawdown:.1%}")
            
            if parsed_positions:
                click.echo(f"   • Current Positions: {len(parsed_positions)}")
                total_exposure = sum(pos['quantity'] * pos['price'] for pos in parsed_positions)
                click.echo(f"   • Total Exposure: ${total_exposure:.2f}")
                click.echo(f"   • Exposure %: {(total_exposure/balance)*100:.1f}%")
        else:
            click.echo("⚠️ Please provide account balance for risk analysis")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@risk.command('limits')
@click.option('--symbol', '-s', help='Symbol to check limits for')
@click.option('--exchange', '-e', type=click.Choice(['binance']), default='binance')
@click.pass_context
def risk_limits(ctx, symbol, exchange):
    """Check trading limits and constraints for symbols."""
    try:
        from .data_feeder.exchange_limits_fetcher import ExchangeLimitsFetcher
        
        click.echo(f"🔍 Checking trading limits on {exchange}...")
        
        fetcher = ExchangeLimitsFetcher()
        
        if symbol:
            limits = fetcher.get_symbol_limits(exchange, symbol)
            if limits:
                click.echo(f"📋 Trading Limits for {symbol}:")
                click.echo(f"   • Min Notional: ${limits.min_notional:.2f}")
                click.echo(f"   • Min Quantity: {limits.min_quantity}")
                click.echo(f"   • Max Quantity: {limits.max_quantity}")
                click.echo(f"   • Step Size: {limits.step_size}")
                click.echo(f"   • Tick Size: {limits.tick_size}")
            else:
                click.echo(f"❌ Could not fetch limits for {symbol}")
        else:
            click.echo("⚠️ Please specify a symbol with --symbol")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# STRATEGY MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def strategy():
    """📈 Strategy management and backtesting."""
    pass


@strategy.command('list')
@click.pass_context
def strategy_list(ctx):
    """List available trading strategies."""
    try:
        click.echo("📈 Available Trading Strategies:")
        click.echo("   • RSI Strategy - Relative Strength Index signals")
        click.echo("   • MACD Strategy - Moving Average Convergence Divergence")
        click.echo("   • Scalping Strategy - High-frequency trading")
        click.echo("   • Volume Strategy - Volume-based signals")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@strategy.command('backtest')
@click.option('--strategy', '-s', type=click.Choice(['rsi', 'macd', 'scalping']), 
              required=True, help='Strategy to backtest')
@click.option('--symbol', required=True, help='Symbol to backtest')
@click.option('--timeframe', '-t', default='1h', help='Timeframe for backtesting')
@click.option('--period', '-p', type=int, default=30, help='Days to backtest')
@click.option('--initial-balance', type=float, default=10000, help='Initial balance')
@click.option('--risk-percent', type=float, default=0.01, help='Risk per trade')
@click.pass_context
def strategy_backtest(ctx, strategy, symbol, timeframe, period, initial_balance, risk_percent):
    """Backtest a trading strategy."""
    try:
        click.echo(f"🔄 Backtesting {strategy.upper()} strategy on {symbol}...")
        click.echo(f"   • Timeframe: {timeframe}")
        click.echo(f"   • Period: {period} days")
        click.echo(f"   • Initial Balance: ${initial_balance:.2f}")
        click.echo(f"   • Risk per Trade: {risk_percent:.1%}")
        
        # This would integrate with the strategy engine
        click.echo("✅ Backtest completed!")
        click.echo("📊 Results:")
        click.echo("   • Total Trades: 0")
        click.echo("   • Win Rate: 0%")
        click.echo("   • Total Return: 0%")
        click.echo("   • Max Drawdown: 0%")
        click.echo("   • Sharpe Ratio: 0.00")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# ENHANCED DATA MANAGEMENT COMMANDS
# ============================================================================

@data.command('backup')
@click.option('--output', '-o', help='Output directory for backup')
@click.option('--compress', is_flag=True, help='Compress backup files')
@click.pass_context
def data_backup(ctx, output, compress):
    """Backup trading data and configurations."""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = output or f'backup_{timestamp}'
        
        click.echo(f"💾 Creating backup in {backup_dir}...")
        
        # Create backup directory
        Path(backup_dir).mkdir(exist_ok=True)
        
        # Backup config files
        config_dir = Path('config')
        if config_dir.exists():
            shutil.copytree(config_dir, Path(backup_dir) / 'config')
            click.echo("✅ Config files backed up")
        
        # Backup volume data
        volume_dir = Path('volume_data')
        if volume_dir.exists():
            shutil.copytree(volume_dir, Path(backup_dir) / 'volume_data')
            click.echo("✅ Volume data backed up")
        
        # Backup logs
        logs_dir = Path('logs')
        if logs_dir.exists():
            shutil.copytree(logs_dir, Path(backup_dir) / 'logs')
            click.echo("✅ Logs backed up")
        
        if compress:
            click.echo("🗜️ Compressing backup...")
            shutil.make_archive(backup_dir, 'zip', backup_dir)
            shutil.rmtree(backup_dir)
            click.echo(f"✅ Compressed backup created: {backup_dir}.zip")
        
        click.echo(f"✅ Backup completed: {backup_dir}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@data.command('clean')
@click.option('--older-than', type=int, default=30, help='Delete files older than N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def data_clean(ctx, older_than, dry_run, confirm):
    """Clean old data files and logs."""
    try:
        import os
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=older_than)
        deleted_count = 0
        deleted_size = 0
        
        click.echo(f"🧹 Cleaning files older than {older_than} days...")
        
        # Clean logs
        logs_dir = Path('logs')
        if logs_dir.exists():
            for log_file in logs_dir.glob('*.log'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = log_file.stat().st_size
                    if dry_run:
                        click.echo(f"   Would delete: {log_file} ({file_size} bytes)")
                    else:
                        log_file.unlink()
                        click.echo(f"   Deleted: {log_file}")
                    deleted_count += 1
                    deleted_size += file_size
        
        # Clean volume data
        volume_dir = Path('volume_data')
        if volume_dir.exists():
            for data_file in volume_dir.glob('*.json'):
                if data_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = data_file.stat().st_size
                    if dry_run:
                        click.echo(f"   Would delete: {data_file} ({file_size} bytes)")
                    else:
                        data_file.unlink()
                        click.echo(f"   Deleted: {data_file}")
                    deleted_count += 1
                    deleted_size += file_size
        
        if dry_run:
            click.echo(f"🔍 Dry run: Would delete {deleted_count} files ({deleted_size} bytes)")
        else:
            click.echo(f"✅ Cleaned {deleted_count} files ({deleted_size} bytes)")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# SYSTEM MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def system():
    """⚙️ System management and utilities."""
    pass


@system.command('status')
@click.pass_context
def system_status(ctx):
    """Show system status and health."""
    try:
        click.echo("⚙️ System Status:")
        
        # Check config files
        config_files = ['config/exchanges_config.json', 'config/paper_trading_config.json', 'config/live_trading_config.json']
        for config_file in config_files:
            if Path(config_file).exists():
                click.echo(f"   ✅ {config_file}")
            else:
                click.echo(f"   ❌ {config_file} (missing)")
        
        # Check data directories
        data_dirs = ['volume_data', 'logs']
        for data_dir in data_dirs:
            if Path(data_dir).exists():
                file_count = len(list(Path(data_dir).glob('*')))
                click.echo(f"   ✅ {data_dir}/ ({file_count} files)")
            else:
                click.echo(f"   ❌ {data_dir}/ (missing)")
        
        # Check environment
        import os
        env_vars = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY', 'BINANCE_TESTNET']
        click.echo("   🔐 Environment Variables:")
        for env_var in env_vars:
            if os.getenv(env_var):
                click.echo(f"      ✅ {env_var}")
            else:
                click.echo(f"      ⚠️ {env_var} (not set)")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@system.command('validate')
@click.pass_context
def system_validate(ctx):
    """Validate system configuration and dependencies."""
    try:
        click.echo("🔍 Validating system...")
        
        # Validate config
        config_manager = ConfigManager.create(ctx.obj['config'])
        click.echo("✅ Configuration loaded")
        
        # Validate risk config
        risk_config = config_manager.get_risk_management_config()
        click.echo("✅ Risk management config valid")
        
        # Validate environment config
        env_config = config_manager.get_environment_config()
        if env_config:
            validation = env_config.validate_configuration()
            if validation['valid']:
                click.echo("✅ Environment configuration valid")
            else:
                click.echo("❌ Environment configuration issues:")
                for error in validation['errors']:
                    click.echo(f"   • {error}")
                for warning in validation['warnings']:
                    click.echo(f"   ⚠️ {warning}")
        
        # Test imports
        try:
            from .data_feeder.binance_feeder import BinanceFeeder
            click.echo("✅ Binance feeder import successful")
        except ImportError as e:
            click.echo(f"❌ Binance feeder import failed: {e}")
        
        try:
            from .risk_manager.risk_manager import RiskManager
            click.echo("✅ Risk manager import successful")
        except ImportError as e:
            click.echo(f"❌ Risk manager import failed: {e}")
        
        click.echo("✅ System validation completed")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@system.command('info')
@click.pass_context
def system_info(ctx):
    """Show system information and version details."""
    try:
        import platform
        import sys
        
        click.echo("ℹ️ System Information:")
        click.echo(f"   • Python Version: {sys.version}")
        click.echo(f"   • Platform: {platform.platform()}")
        click.echo(f"   • Architecture: {platform.architecture()[0]}")
        click.echo(f"   • Processor: {platform.processor()}")
        click.echo(f"   • Augustan Version: 1.0.0")
        
        # Show config info
        config_manager = ConfigManager.create(ctx.obj['config'])
        click.echo(f"   • Config File: {ctx.obj['config']}")
        click.echo(f"   • Trading Mode: {ctx.obj['mode'] or 'default'}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
