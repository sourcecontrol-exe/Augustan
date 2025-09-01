# Augustan: Futures Trading System

A comprehensive cryptocurrency futures trading system optimized for high-volume markets with automated volume analysis, multi-exchange support, and intelligent market selection.

## 🚀 System Overview

Augustan is designed as a futures-optimized trading system with three main components:

**Layer 1 (Volume Analysis)**: Daily analysis of futures markets across 5 major exchanges to identify high-liquidity trading opportunities.

**Layer 2 (Strategy Engine)**: Executes RSI and MACD strategies on volume-selected markets with confidence scoring.

**Layer 3 (CLI Interface)**: Professional command-line interface for easy system operation and monitoring.

This architecture ensures you only trade the most liquid futures markets while maintaining professional-grade tooling for analysis and execution.

## ✨ Core Features

| Module | Description |
|--------|-------------|
| 📊 **Multi-Exchange Volume Analysis** | Analyzes futures markets across Binance, Bybit, OKX, Bitget, and Gate.io |
| 🤖 **Futures-Optimized Strategies** | RSI and MACD strategies adapted for futures volatility patterns |
| ⚙️ **Intelligent Market Selection** | Automatically selects top liquid markets (>$1M daily volume) |
| 🎯 **Signal Management** | Generates BUY/SELL signals with confidence scoring (60-90%) |
| 🛡️ **Volume-Based Risk Control** | Only trades high-liquidity markets to minimize slippage risk |
| 📤 **CLI Interface** | Professional command-line tools for all operations |
| 📈 **Daily Volume Jobs** | Automated daily analysis with 30-day data retention |
| 📊 **Live Dashboard** | Real-time market overview with auto-refresh capabilities |
| ⏰ **Automated Scheduler** | Runs daily volume analysis jobs at configurable times |
| 🔧 **Production Ready** | Systemd service support for server deployment |
## 🏗️ Project Architecture

```
augustan/
├── 📂 src/
│   ├── 📂 core/                 # Data models (MarketData, TradingSignal, FuturesModels)
│   ├── 📂 data_feeder/          # Multi-exchange data fetching (Binance, Bybit, etc.)
│   ├── 📂 strategy_engine/      # RSI and MACD strategies with base framework
│   ├── 📂 jobs/                 # Daily volume analysis and scheduling jobs
│   └── 📂 (future modules)/     # Market features, ML models, signal management
├── 📂 config/                   # Exchange configurations and API keys
├── 📂 volume_data/              # Daily volume analysis results (JSON)
├── 📂 logs/                     # Structured application logs
├── 📂 deployment/               # Production deployment files (systemd)
├── 🐍 futures_main.py           # Futures trading system entry point
├── 🐍 cli.py                    # Comprehensive CLI interface
├── 🐍 main.py                   # Original spot trading system
└── 📋 requirements.txt          # Python dependencies (ccxt, pandas, ta, click)
```
## 🔧 Installation & Setup

### 1. Prerequisites
- **Python 3.9+** (tested with Python 3.9.6)
- **pip** and **virtualenv** (recommended)

### 2. Quick Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd augustan

# One-command setup (recommended)
./setup_cli.sh
```

### 3. Manual Installation
```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip3 install -r requirements.txt

# Initialize configuration
python3 cli.py config init
```

### 4. Configuration
Edit `config/exchanges_config.json` with your exchange API keys:

```json
{
  "binance": {
    "api_key": "YOUR_BINANCE_API_KEY",
    "secret": "YOUR_BINANCE_SECRET",
    "enabled": true,
    "testnet": false
  },
  "bybit": {
    "api_key": "YOUR_BYBIT_API_KEY", 
    "secret": "YOUR_BYBIT_SECRET",
    "enabled": true,
    "testnet": false
  },
  "volume_settings": {
    "min_volume_usd_24h": 1000000,
    "min_volume_rank": 200
  }
}
```

⚠️ **Security**: Never commit real API keys to version control! The system works without API keys for volume analysis.

## 🚀 Usage

### CLI Interface (Recommended)
The system provides a comprehensive CLI for all operations:

```bash
# Run volume analysis across all exchanges
python3 cli.py volume analyze

# Generate trading signals for top markets
python3 cli.py trading analyze --timeframe 4h

# Show latest signals
python3 cli.py trading signals --type buy --min-confidence 0.7

# Start daily scheduled job
python3 cli.py job start --schedule

# Live dashboard
python3 cli.py dashboard --refresh 30
```

### Direct Python Usage

**Volume Analysis:**
```bash
python3 futures_main.py --volume-analysis
```

**Trading Analysis:**
```bash
python3 futures_main.py --trading-analysis --timeframe 4h
```

**Complete Analysis:**
```bash
python3 futures_main.py  # Runs both volume and trading analysis
```

**Daily Job Scheduler:**
```bash
python3 futures_main.py --daily-job
```

## 🔌 Exchange Support

The system supports **5 major futures exchanges**:
- **Binance** (Primary, most tested)
- **Bybit** (Excellent volume data)
- **OKX** (Good liquidity)
- **Bitget** (Growing market)
- **Gate.io** (Wide selection)

### API Configuration
1. **Create API Keys**: Generate read-only API keys on your exchange
2. **Add to Config**: Edit `config/exchanges_config.json` 
3. **Test First**: System works without API keys for volume analysis

### Volume Analysis (No API Required)
The system can analyze market volumes without API keys using public endpoints.

## 📈 Strategy Development

### Using Built-in Strategies
```python
from src.strategy_engine import RSIStrategy, MACDStrategy

# RSI Strategy with custom parameters
rsi_strategy = RSIStrategy(
    period=14,
    overbought=70,
    oversold=30
)

# MACD Strategy
macd_strategy = MACDStrategy(
    fast_period=12,
    slow_period=26,
    signal_period=9
)
```

### Creating Custom Strategies
Extend the `BaseStrategy` class:

```python
from src.strategy_engine.base_strategy import BaseStrategy
from src.core.models import TradingSignal, SignalType, StrategyType

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(StrategyType.CUSTOM)
        
    def generate_signals(self, market_data):
        # Your custom logic here
        signals = []
        
        # Example: Simple price-based logic
        latest_price = market_data[-1].close
        if your_buy_condition(latest_price):
            signal = TradingSignal(
                symbol=market_data[0].symbol,
                strategy=self.strategy_type,
                signal_type=SignalType.BUY,
                confidence=0.75,
                price=latest_price,
                timestamp=market_data[-1].timestamp
            )
            signals.append(signal)
            
        return signals
```
## 📊 Output & Monitoring

The system provides comprehensive monitoring and output options:

### Real-time Feedback
- **Console Output**: Formatted tables with market data and signals
- **Progress Bars**: Visual feedback for long-running operations
- **Color-coded Signals**: 🟢 BUY, 🔴 SELL indicators

### File Outputs
- **JSON Reports**: Structured data in `volume_data/` and signal files
- **Log Files**: Detailed logs in `logs/futures_trading_system.log`
- **Configuration**: All settings saved in `config/exchanges_config.json`

### Live Dashboard
```bash
python3 cli.py dashboard --refresh 30
```
Shows:
- Current market volume statistics
- Latest trading signals with confidence scores
- Top recommended markets
- System status and last run times

### Sample Outputs

**Volume Analysis:**
```
🏆 Top 5 Markets by Volume
================================================================================
 1. ETH/USDT:USDT        | BYBIT    | $7,507,053,058 | Score:  80.5
 2. BTC/USDT:USDT        | BYBIT    | $7,497,283,725 | Score:  80.0
```

**Trading Signals:**
```
🎯 Latest Trading Signals (5 found)
==========================================================================================
🟢 BTC/USDT:USDT   | MACD | BUY  | $108656.9000 | 70.0% | 2025-08-31T09:30:00
🔴 ETH/USDT:USDT   | RSI  | SELL | $4830.3700   | 78.0% | 2025-08-23T01:30:00
```

## 🚀 Quick Demo

Try the interactive demo to see all features:
```bash
python3 demo_cli.py
```

Or run individual commands:
```bash
# Quick start
./setup_cli.sh
python3 cli.py volume analyze
python3 cli.py trading analyze --timeframe 4h
python3 cli.py dashboard
```

## 📚 Documentation

- **`CLI_GUIDE.md`**: Comprehensive CLI documentation with all commands
- **`README_FUTURES.md`**: Detailed system architecture and features  
- **`CLI_SUMMARY.md`**: Implementation summary and examples

## 🤝 Contributing

Contributions are welcome! Please:

1. **Fork the Project**
2. **Create Feature Branch**: `git checkout -b feature/AmazingFeature`
3. **Commit Changes**: `git commit -m 'Add AmazingFeature'`
4. **Push to Branch**: `git push origin feature/AmazingFeature`
5. **Open Pull Request**

### Development Areas
- Additional trading strategies (Bollinger Bands, Stochastic, etc.)
- More exchanges (Kraken, Huobi, etc.)
- ML model for strategy selection
- Backtesting framework
- Web dashboard interface

## ⚠️ Disclaimer

**This software is for educational and research purposes only.**

- Cryptocurrency futures trading carries **significant risk of loss**
- Past performance does not indicate future results
- Always test thoroughly before using real capital
- You are solely responsible for trading decisions
- Start with small amounts and paper trading

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

For help and support:

- **📖 Documentation**: Check `CLI_GUIDE.md` for detailed usage
- **🐛 Issues**: Create GitHub issues with detailed logs
- **💡 Features**: Submit feature requests with use cases
- **❓ Questions**: Use `--help` with any CLI command

## 🎯 Performance Metrics

**Live Test Results:**
- ✅ Analyzed **351 futures markets** across 5 exchanges
- ✅ Generated **49 recommended markets** for trading  
- ✅ **$26.4B** total daily volume processed
- ✅ Signal generation in **<30 seconds**
- ✅ **Professional CLI** with 15+ commands

---

**Happy Futures Trading!** 🚀📈