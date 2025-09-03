# 🚀 Augustan Trading System CLI Guide

The Augustan Trading System provides a powerful command-line interface (`aug`) for futures trading analysis, position sizing, and risk management.

## 📦 Installation

```bash
# Install the package
pip install -e .

# The 'aug' command will be available globally
```

## 🎯 Quick Start

```bash
# Show all available commands
aug --help

# Analyze volume across exchanges
aug volume analyze --enhanced

# Check position sizing for a symbol
aug position analyze --symbol BTC/USDT --budget 100

# Monitor real-time prices
aug live monitor --symbols BTC/USDT ETH/USDT --duration 30

# Show configuration
aug config show --section risk
```

## 🔧 Auto-Completion Setup

Enable tab completion for faster command entry:

```bash
# Enable completion for current session
source completion.sh

# Enable permanently (add to ~/.bashrc or ~/.zshrc)
echo "source $(pwd)/completion.sh" >> ~/.bashrc
```

### Auto-Completion Features

- **Commands**: `aug <TAB>` shows main commands
- **Subcommands**: `aug volume <TAB>` shows volume subcommands
- **Symbols**: `aug position analyze --symbol <TAB>` shows trading symbols
- **Timeframes**: `aug trading analyze --timeframe <TAB>` shows timeframes
- **Exchanges**: `aug volume analyze --exchanges <TAB>` shows exchanges
- **Formats**: `aug volume analyze --format <TAB>` shows output formats

## 📊 Volume Analysis Commands

### `aug volume analyze`
Analyze futures market volumes across exchanges.

```bash
# Basic volume analysis
aug volume analyze

# Enhanced analysis with position sizing
aug volume analyze --enhanced --budget 100 --risk-percent 0.5

# Specific exchanges only
aug volume analyze --exchanges bybit binance

# Custom volume threshold
aug volume analyze --min-volume 5000000

# Output to JSON
aug volume analyze --format json --output analysis.json
```

**Options:**
- `--enhanced`: Run enhanced analysis with position sizing
- `--budget FLOAT`: Trading budget in USDT (default: 50)
- `--risk-percent FLOAT`: Risk per trade in % (default: 0.2)
- `--exchanges`: Specific exchanges to analyze
- `--min-volume FLOAT`: Minimum 24h volume in USD
- `--format`: Output format (json, csv, table)

### `aug volume top`
Show top markets by volume from latest analysis.

```bash
# Show top 10 markets
aug volume top --limit 10

# Show top markets with custom minimum volume
aug volume top --min-volume 10000000
```

## 💰 Position Sizing Commands

### `aug position analyze`
Analyze position sizing for a specific symbol. Budget is automatically fetched from wallet if not specified.

```bash
# Auto-fetch budget from wallet
aug position analyze --symbol BTC/USDT

# Use specified budget
aug position analyze --symbol BTC/USDT --budget 100

# Custom risk parameters
aug position analyze --symbol ETH/USDT --budget 500 --risk-percent 0.5 --leverage 10

# Custom stop loss
aug position analyze --symbol DOGE/USDT --budget 50 --stop-loss-percent 3.0
```

**Options:**
- `--symbol TEXT`: Symbol to analyze (required)
- `--budget FLOAT`: Trading budget in USDT (auto-fetched from wallet if not provided)
- `--risk-percent FLOAT`: Risk per trade in % (default: 0.2)
- `--leverage INTEGER`: Leverage to use (default: 5)
- `--stop-loss-percent FLOAT`: Stop loss in % (default: 2.0)

### `aug position tradeable`
Find tradeable symbols based on position sizing analysis.

```bash
# Find tradeable symbols for $100 budget
aug position tradeable --budget 100 --limit 20

# Custom risk parameters
aug position tradeable --budget 500 --risk-percent 0.5
```

## 📈 Trading Analysis Commands

### `aug trading analyze`
Generate trading signals for futures markets.

```bash
# Analyze top volume symbols
aug trading analyze --timeframe 4h --top 20

# Specific symbols
aug trading analyze --symbols BTC/USDT ETH/USDT --strategies rsi

# High confidence signals only
aug trading analyze --min-confidence 0.7 --format json

# Use only tradeable symbols
aug trading analyze --use-tradeable --budget 100
```

**Options:**
- `--symbols`: Specific symbols to analyze
- `--timeframe`: Timeframe for analysis (1m, 5m, 1h, 4h, 1d)
- `--strategies`: Strategies to run (rsi, macd, all)
- `--min-confidence FLOAT`: Minimum confidence threshold
- `--top INTEGER`: Number of top volume symbols to analyze
- `--use-tradeable`: Use only tradeable symbols from enhanced analysis

### `aug trading signals`
Show latest trading signals with filtering options.

```bash
# Show all signals
aug trading signals --type all --strategy all

# Buy signals only
aug trading signals --type buy --min-confidence 0.6

# RSI strategy signals
aug trading signals --strategy rsi --limit 5
```

## 🎯 Trading Modes

The system supports two trading modes with separate configurations:

### **📝 Paper Trading (Default)**
- **Safe**: Uses testnet APIs, no real money
- **Config**: `config/paper_trading_config.json`
- **Risk**: Conservative settings (1% risk, 3x leverage)
- **Use**: Testing strategies, learning, development

### **💰 Live Trading**
- **Real Money**: Uses mainnet APIs, real trading
- **Config**: `config/live_trading_config.json`
- **Risk**: More aggressive settings (2% risk, 5x leverage)
- **Use**: Actual trading with real capital

### **🔄 Switching Modes**

```bash
# Use paper trading mode
aug --mode paper position analyze --symbol BTC/USDT

# Use live trading mode (with warnings)
aug --mode live position analyze --symbol BTC/USDT

# Switch default configuration
aug config switch --mode paper
aug config switch --mode live
```

## 🚀 Live Trading Commands

### `aug live monitor`
Monitor real-time prices for symbols.

```bash
# Monitor multiple symbols
aug live monitor --symbols BTC/USDT ETH/USDT --duration 60

# Quick price check
aug live monitor --symbols DOGE/USDT --duration 10
```

### `aug live secure`
Secure API keys by moving them to environment variables.

```bash
# Secure API keys
aug live secure
```

This command will:
1. Extract API keys from config files
2. Create a `.env` file with the keys
3. Clean up config files to remove sensitive data
4. Update `.gitignore` if needed

### `aug live test`
Test live trading components.

```bash
# Test all components
aug live test
```

### `aug live start`
Start live trading engine (paper trading).

```bash
# Start with specific symbols
aug live start --symbols BTC/USDT ETH/USDT --balance 1000 --duration 60

# Paper trading mode
aug live start --symbols DOGE/USDT --paper
```

## 🤖 Job Management Commands

### `aug job status`
Show job status and latest results.

```bash
# Check job status
aug job status
```

### `aug job start`
Start the daily volume analysis job.

```bash
# Start scheduled job
aug job start --schedule
```

## ⚙️ Configuration Commands

### `aug config show`
Show current configuration.

```bash
# Show complete configuration
aug config show

# Show specific section
aug config show --section risk
aug config show --section data
aug config show --section signals
```

### `aug config switch`
Switch between paper and live trading configurations.

```bash
# Switch to paper trading (safe, testnet)
aug config switch --mode paper

# Switch to live trading (real money)
aug config switch --mode live
```

### `aug config update`
Update configuration settings.

```bash
# Update risk management settings
aug config update --section risk_management --default-budget 1000 --max-risk-per-trade 0.01

# Update multiple settings
aug config update --section risk_management --default-leverage 5 --max-positions 3
```

### `aug config init`
Initialize configuration file with defaults.

```bash
# Initialize with defaults
aug config init

# Force overwrite existing config
aug config init --force
```

## 📊 Dashboard

### `aug dashboard`
Show a live dashboard with market overview.

```bash
# Show dashboard with auto-refresh
aug dashboard --refresh 5

# One-time dashboard
aug dashboard --refresh 0
```

## 🔍 Common Use Cases

### 1. Market Analysis Workflow
```bash
# 1. Analyze market volumes
aug volume analyze --enhanced --budget 100

# 2. Find tradeable symbols
aug position tradeable --budget 100 --limit 10

# 3. Generate trading signals
aug trading analyze --use-tradeable --timeframe 4h

# 4. Monitor live prices
aug live monitor --symbols BTC/USDT ETH/USDT --duration 30
```

### 2. Position Sizing Analysis
```bash
# Analyze multiple symbols
for symbol in BTC/USDT ETH/USDT SOL/USDT; do
    aug position analyze --symbol $symbol --budget 100 --risk-percent 0.5
done
```

### 3. Risk Management Check
```bash
# Check current risk settings
aug config show --section risk

# Analyze position with conservative parameters
aug position analyze --symbol BTC/USDT --budget 50 --risk-percent 0.2 --leverage 3
```

## 🎯 Tips and Tricks

1. **Use Auto-Completion**: Press TAB to get suggestions for commands and options
2. **Check Help**: Use `--help` on any command to see available options
3. **Verbose Mode**: Use `-v` flag for detailed logging
4. **Custom Config**: Use `-c` to specify a custom configuration file
5. **Output Formats**: Use `--format json` for machine-readable output

## 🔧 Troubleshooting

### Common Issues

1. **Command not found**: Ensure the package is installed with `pip install -e .`
2. **Auto-completion not working**: Source the completion script with `source completion.sh`
3. **Configuration errors**: Use `aug config init` to create a default configuration
4. **Network issues**: Check your internet connection for data fetching commands

### Getting Help

```bash
# General help
aug --help

# Command-specific help
aug volume --help
aug position analyze --help

# Verbose output for debugging
aug -v volume analyze
```

## 📝 Examples

### Complete Trading Session
```bash
# 1. Market analysis
aug volume analyze --enhanced --budget 1000 --risk-percent 0.5

# 2. Find opportunities
aug position tradeable --budget 1000 --limit 20

# 3. Generate signals
aug trading analyze --use-tradeable --timeframe 1h --min-confidence 0.7

# 4. Monitor live
aug live monitor --symbols BTC/USDT ETH/USDT SOL/USDT --duration 300

# 5. Check portfolio
aug dashboard --refresh 10
```

This CLI provides a comprehensive toolkit for futures trading analysis, from market research to live monitoring, all accessible through the simple `aug` command with powerful auto-completion support.
