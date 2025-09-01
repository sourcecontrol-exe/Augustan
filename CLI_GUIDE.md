# Futures Trading CLI Guide

A comprehensive command-line interface for the futures trading system that makes it easy to analyze markets, generate signals, and manage trading operations.

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
pip3 install -r requirements.txt

# Make CLI executable
chmod +x futures-cli

# Initialize configuration
python3 cli.py config init

# Run your first analysis
python3 cli.py volume analyze
```

### Basic Usage
```bash
# Show help
python3 cli.py --help

# Analyze volume across all exchanges
python3 cli.py volume analyze

# Generate trading signals
python3 cli.py trading analyze --timeframe 4h

# Show top markets
python3 cli.py volume top --limit 10

# View latest signals
python3 cli.py trading signals --type buy
```

## 📋 Command Reference

### Global Options
```bash
-c, --config TEXT    Path to configuration file (default: config/exchanges_config.json)
-v, --verbose        Enable verbose output for debugging
--version           Show version and exit
```

### Volume Commands (`volume`)

#### `volume analyze`
Analyze futures market volumes across all configured exchanges.

**Usage:**
```bash
python3 cli.py volume analyze [OPTIONS]
```

**Options:**
- `--exchanges, -e`: Specific exchanges to analyze (binance, bybit, okx, bitget, gate)
- `--min-volume, -m`: Minimum 24h volume in USD (default: 1M)
- `--max-rank, -r`: Maximum volume rank to consider (default: 200)
- `--output, -o`: Output file path (auto-generated if not specified)
- `--format, -f`: Output format (json, csv, table)
- `--save/--no-save`: Save results to file (default: true)

**Examples:**
```bash
# Analyze all exchanges with default settings
python3 cli.py volume analyze

# Analyze only Bybit with higher volume threshold
python3 cli.py volume analyze --exchanges bybit --min-volume 5000000

# Save as JSON file
python3 cli.py volume analyze --format json --output my_analysis.json

# Analyze without saving
python3 cli.py volume analyze --no-save
```

#### `volume top`
Show top markets by volume from the latest analysis.

**Usage:**
```bash
python3 cli.py volume top [OPTIONS]
```

**Options:**
- `--limit, -l`: Number of top markets to show (default: 10)
- `--exchange, -e`: Filter by specific exchange

**Examples:**
```bash
# Show top 20 markets
python3 cli.py volume top --limit 20

# Show top 5 markets from Bybit only
python3 cli.py volume top --exchange bybit --limit 5
```

### Trading Commands (`trading`)

#### `trading analyze`
Generate trading signals for futures markets using RSI and MACD strategies.

**Usage:**
```bash
python3 cli.py trading analyze [OPTIONS]
```

**Options:**
- `--symbols, -s`: Specific symbols to analyze (can be multiple)
- `--timeframe, -t`: Timeframe for analysis (1m, 5m, 1h, 4h, 1d)
- `--limit, -l`: Number of candles to fetch (default: 100)
- `--top`: Number of top volume symbols to analyze (default: 20)
- `--strategies`: Strategies to run (rsi, macd, all)
- `--min-confidence`: Minimum confidence threshold for signals (0.0-1.0)
- `--output, -o`: Output file path
- `--format, -f`: Output format (json, table)

**Examples:**
```bash
# Analyze top 20 markets with 4h timeframe
python3 cli.py trading analyze --timeframe 4h

# Analyze specific symbols
python3 cli.py trading analyze --symbols BTCUSDT ETHUSDT --timeframe 1h

# Run only RSI strategy with high confidence threshold
python3 cli.py trading analyze --strategies rsi --min-confidence 0.7

# Save results as JSON
python3 cli.py trading analyze --format json --output signals.json
```

#### `trading signals`
Show latest trading signals with filtering options.

**Usage:**
```bash
python3 cli.py trading signals [OPTIONS]
```

**Options:**
- `--type, -t`: Filter signals by type (buy, sell, all)
- `--strategy, -s`: Filter signals by strategy (rsi, macd, all)
- `--min-confidence`: Minimum confidence threshold
- `--limit, -l`: Number of signals to show (default: 10)

**Examples:**
```bash
# Show all signals
python3 cli.py trading signals

# Show only BUY signals with high confidence
python3 cli.py trading signals --type buy --min-confidence 0.7

# Show top 5 RSI signals
python3 cli.py trading signals --strategy rsi --limit 5
```

### Job Commands (`job`)

#### `job start`
Start the daily volume analysis job.

**Usage:**
```bash
python3 cli.py job start [OPTIONS]
```

**Options:**
- `--schedule/--no-schedule`: Run as scheduled job vs. run once (default: false)
- `--time, -t`: Schedule time in HH:MM format (default: 09:00)
- `--daemon/--no-daemon`: Run in background (default: false)

**Examples:**
```bash
# Run volume analysis once
python3 cli.py job start

# Schedule daily job at 9:00 AM
python3 cli.py job start --schedule

# Schedule daily job at 3:30 PM
python3 cli.py job start --schedule --time 15:30
```

#### `job status`
Show job status and latest results.

**Usage:**
```bash
python3 cli.py job status
```

**Output includes:**
- Last run date
- Markets analyzed
- Recommended markets count
- Total volume
- Top 5 recommended symbols

### Configuration Commands (`config`)

#### `config show`
Show current configuration.

**Usage:**
```bash
python3 cli.py config show [OPTIONS]
```

**Options:**
- `--section, -s`: Show specific section only

**Examples:**
```bash
# Show all configuration
python3 cli.py config show

# Show only volume settings
python3 cli.py config show --section volume_settings
```

#### `config init`
Initialize configuration file with defaults.

**Usage:**
```bash
python3 cli.py config init [OPTIONS]
```

**Options:**
- `--force, -f`: Overwrite existing configuration

**Examples:**
```bash
# Create default configuration
python3 cli.py config init

# Overwrite existing configuration
python3 cli.py config init --force
```

### Dashboard Command

#### `dashboard`
Show a live dashboard with market overview.

**Usage:**
```bash
python3 cli.py dashboard [OPTIONS]
```

**Options:**
- `--refresh, -r`: Auto-refresh interval in seconds (0 = no refresh)

**Examples:**
```bash
# Static dashboard
python3 cli.py dashboard

# Auto-refresh every 30 seconds
python3 cli.py dashboard --refresh 30
```

## 🎯 Common Workflows

### Daily Market Analysis
```bash
# 1. Run volume analysis
python3 cli.py volume analyze

# 2. Check top markets
python3 cli.py volume top --limit 10

# 3. Generate trading signals for top markets
python3 cli.py trading analyze --timeframe 4h

# 4. View high-confidence BUY signals
python3 cli.py trading signals --type buy --min-confidence 0.7
```

### Quick Signal Check
```bash
# Show latest signals
python3 cli.py trading signals --limit 5

# Show only BUY signals
python3 cli.py trading signals --type buy

# Show high-confidence signals
python3 cli.py trading signals --min-confidence 0.75
```

### Automated Daily Job
```bash
# Start daily scheduled job
python3 cli.py job start --schedule

# Check job status
python3 cli.py job status

# View latest volume analysis results
python3 cli.py volume top --limit 20
```

### Custom Analysis
```bash
# Analyze specific symbols with 1h timeframe
python3 cli.py trading analyze --symbols BTCUSDT ETHUSDT SOLUSDT --timeframe 1h

# Run only MACD strategy
python3 cli.py trading analyze --strategies macd --timeframe 4h

# High-confidence analysis with JSON output
python3 cli.py trading analyze --min-confidence 0.8 --format json --output high_conf_signals.json
```

## 🔧 Configuration

### Exchange Configuration
Edit `config/exchanges_config.json` to add your API keys:

```json
{
  "binance": {
    "api_key": "your_binance_api_key",
    "secret": "your_binance_secret",
    "enabled": true,
    "testnet": false
  },
  "bybit": {
    "api_key": "your_bybit_api_key",
    "secret": "your_bybit_secret",
    "enabled": true,
    "testnet": false
  }
}
```

### Volume Settings
```json
{
  "volume_settings": {
    "min_volume_usd_24h": 1000000,
    "min_volume_rank": 200,
    "max_markets_per_exchange": 100
  }
}
```

### Job Settings
```json
{
  "job_settings": {
    "schedule_time": "09:00",
    "retention_days": 30,
    "output_directory": "volume_data"
  }
}
```

## 📊 Output Formats

### Table Format (Default)
```
🏆 Top 5 Markets by Volume
================================================================================
 1. ETH/USDT:USDT        | BYBIT    | $7,507,053,058 | Score:  80.5
 2. BTC/USDT:USDT        | BYBIT    | $7,497,283,725 | Score:  80.0
 3. SOL/USDT:USDT        | BYBIT    | $2,372,808,996 | Score:  80.6
```

### JSON Format
```json
{
  "timestamp": "2025-09-01T22:11:36.364033",
  "timeframe": "4h",
  "symbols_analyzed": 19,
  "signals": {
    "BTC/USDT:USDT": [
      {
        "strategy": "RSI",
        "signal_type": "BUY",
        "confidence": 0.632,
        "price": 112152.8
      }
    ]
  }
}
```

## 🚨 Error Handling

### Common Errors and Solutions

**Configuration not found:**
```bash
❌ Configuration file not found: config/exchanges_config.json
```
**Solution:** Run `python3 cli.py config init`

**No volume analysis data:**
```bash
❌ No volume analysis data found. Run 'volume analyze' first.
```
**Solution:** Run `python3 cli.py volume analyze`

**API rate limits:**
```bash
❌ Error: Exchange rate limit exceeded
```
**Solution:** Wait a few minutes and try again, or reduce the number of symbols

**Network connectivity:**
```bash
❌ Error: Connection timeout
```
**Solution:** Check internet connection and try again

## 🔍 Debugging

### Verbose Mode
Use the `--verbose` flag for detailed debugging information:
```bash
python3 cli.py --verbose volume analyze
```

### Log Files
Check log files for detailed execution information:
```bash
tail -f logs/futures_trading_system.log
```

## 📈 Performance Tips

1. **Use specific exchanges** for faster analysis:
   ```bash
   python3 cli.py volume analyze --exchanges bybit
   ```

2. **Limit symbols** for quick testing:
   ```bash
   python3 cli.py trading analyze --symbols BTCUSDT ETHUSDT
   ```

3. **Use higher timeframes** for faster execution:
   ```bash
   python3 cli.py trading analyze --timeframe 4h
   ```

4. **Set confidence thresholds** to filter noise:
   ```bash
   python3 cli.py trading signals --min-confidence 0.7
   ```

## 🔒 Security Best Practices

1. **API Keys**: Store API keys in the configuration file, not in command line
2. **File Permissions**: Restrict access to configuration files:
   ```bash
   chmod 600 config/exchanges_config.json
   ```
3. **Testnet**: Use testnet APIs for testing:
   ```json
   {"testnet": true}
   ```

## 🤝 Integration Examples

### Shell Scripts
```bash
#!/bin/bash
# Daily analysis script
echo "Running daily futures analysis..."
python3 cli.py volume analyze --no-save
python3 cli.py trading analyze --timeframe 4h --output daily_signals.json
echo "Analysis complete!"
```

### Cron Jobs
```bash
# Run volume analysis daily at 9 AM
0 9 * * * cd /path/to/augustan && python3 cli.py volume analyze

# Generate trading signals every 4 hours
0 */4 * * * cd /path/to/augustan && python3 cli.py trading analyze --timeframe 4h
```

### Python Integration
```python
import subprocess
import json

# Run CLI command from Python
result = subprocess.run([
    'python3', 'cli.py', 'volume', 'analyze', '--format', 'json'
], capture_output=True, text=True)

data = json.loads(result.stdout)
print(f"Found {data['recommended_markets']} recommended markets")
```

---

## 📞 Support

For help with the CLI:
- Use `--help` with any command for detailed information
- Check the log files in `logs/` directory
- Use `--verbose` mode for debugging
- Refer to the main README for system architecture details

**Happy Trading!** 🚀
