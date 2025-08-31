# Augustan CLI Guide

## Installation

Install Augustan in development mode to enable all CLI commands:

```bash
pip install -e .
```

## Available CLI Commands

### Main CLI Interface
```bash
augustan --help                    # Show all available commands
augustan --version                 # Show version information
augustan config                    # Show current configuration
```

### Trading Operations
```bash
# Paper Trading
augustan paper-trading --quick     # Quick paper trading demo
augustan paper-trading --full      # Full paper trading session
augustan-paper --quick             # Direct paper trading command

# Backtesting
augustan backtest                  # Run backtesting session
augustan backtest --strategy RSI_MACD  # Backtest specific strategy
augustan-backtest                  # Direct backtesting command

# Live Trading
augustan live                      # Run live trading bot
augustan live --cycles 5          # Run for 5 cycles
augustan-live                      # Direct live trading command

# Market Analysis
augustan scan                      # Scan for trading opportunities
```

### Development & Testing
```bash
augustan test                      # Run test suite
augustan test --coverage           # Run tests with coverage
augustan-test                      # Direct test command
```

### Demo Commands
```bash
# Interactive Demos
augustan-demo quick-backtest       # Quick backtesting demo
augustan-demo strategy-compare     # Compare multiple strategies
augustan-demo paper-trading        # Paper trading demo
augustan-demo market-scan          # Market scanner demo
augustan-demo risk-analysis        # Risk management demo

# Quick Access Commands
augustan-quick --backtest-quick    # Quick backtest
augustan-quick --paper-quick       # Quick paper trading
augustan-quick --scan-markets      # Market scan
augustan-quick --show-config       # Show configuration
augustan-quick --run-tests         # Run tests
augustan-quick --live-demo         # Live trading demo (1 cycle)
```

## Examples

### Quick Start
```bash
# Install and run quick demo
pip install -e .
augustan-quick --paper-quick

# Run comprehensive backtest
augustan backtest

# Scan markets for opportunities
augustan scan
```

### Development Workflow
```bash
# Run tests
augustan test

# Check configuration
augustan config

# Run paper trading
augustan paper-trading --quick

# Run live demo (safe)
augustan live --cycles 1
```

### Strategy Development
```bash
# Compare strategies
augustan-demo strategy-compare

# Analyze risk management
augustan-demo risk-analysis

# Quick backtest iteration
augustan-demo quick-backtest
```

## Configuration

Augustan uses environment-based configuration:
- `configs/testing/config.json` - Testing environment
- `configs/live/config.json` - Live trading environment

Set environment with:
```bash
export AUGUSTAN_ENV=testing  # or 'live'
```

## Logging

All commands generate logs:
- Console output for immediate feedback
- Log files for detailed analysis
- Configurable log levels

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you've installed in development mode:
   ```bash
   pip install -e .
   ```

2. **Configuration Errors**: Check your config files:
   ```bash
   augustan config
   ```

3. **API Key Issues**: Verify your `.env` file contains valid API keys

4. **Permission Errors**: Ensure proper file permissions for log directories

### Getting Help

```bash
augustan --help                    # Main help
augustan paper-trading --help      # Command-specific help
augustan-demo --help               # Demo help
```
