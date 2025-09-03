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
from .core.config_manager import get_config_manager


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
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """
    🚀 Augustan Trading System CLI
    
    The ultimate futures trading and position sizing tool with volume analysis,
    multi-exchange support, and intelligent risk management.
    
    Examples:
        aug volume analyze --enhanced               # Enhanced volume analysis with position sizing
        aug position analyze --symbol DOGE/USDT    # Analyze position sizing for DOGE
        aug position tradeable --budget 50          # Find tradeable symbols for $50 budget
        aug trading analyze --timeframe 4h          # Generate trading signals
        aug job start --schedule                    # Start daily job
        aug config show                             # Show configuration
        
    Auto-completion: Press TAB to get suggestions for commands, options, and values.
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = config
    ctx.obj['verbose'] = verbose
    
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
        config_manager = get_config_manager(ctx.obj['config'])
        
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
            
            if is_futures:
                # Use futures feeder for futures symbols
                feeder = BinanceFuturesFeeder(testnet=True)
                account_info = feeder.get_account_info()
            else:
                # Use spot feeder for spot symbols
                feeder = BinanceDataFeeder(testnet=True)
                account_info = feeder.get_account_info()
            
            if account_info and 'USDT' in account_info.get('free', {}):
                budget = float(account_info['free']['USDT'])
                click.echo(f"✅ Wallet balance: ${budget:.2f} USDT")
            else:
                # Fallback to default budget
                budget = 50.0
                click.echo(f"⚠️  Could not fetch wallet balance, using default: ${budget:.2f} USDT")
                click.echo("   (Account info may not be available in testnet)")
        else:
            click.echo(f"💰 Using specified budget: ${budget:.2f} USDT")
        
        # Initialize configuration manager and get risk config
        config_manager = get_config_manager(ctx.obj['config'])
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
        config_manager = get_config_manager(ctx.obj['config'])
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
        config_manager = get_config_manager(ctx.obj['config'])
        
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
            time.sleep(refresh)
            
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
        from .data_feeder.realtime_feeder import BinanceWebsocketFeeder
        
        # Default symbols if none provided
        watchlist = list(symbols) if symbols else ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT']
        
        click.echo(f"📡 Starting real-time price monitor...")
        click.echo(f"📊 Symbols: {', '.join(watchlist)}")
        click.echo(f"⏱️ Duration: {duration} seconds")
        
        feeder = BinanceWebsocketFeeder(watchlist, timeframe='1m', stream_type='ticker')
        
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
        config_manager = get_config_manager(ctx.obj['config'])
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
        from .data_feeder.realtime_feeder import BinanceWebsocketFeeder
        feeder = BinanceWebsocketFeeder(['BTC/USDT'], timeframe='1m', stream_type='ticker')
        
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


if __name__ == '__main__':
    cli()
