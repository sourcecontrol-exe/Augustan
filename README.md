# 🚀 Augustan Trading System

The ultimate futures trading and position sizing tool with intelligent risk management, multi-exchange support, and automated signal generation.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ✨ Key Features

### 💰 **Intelligent Position Sizing**
- **Budget-Based Filtering**: Only shows symbols you can actually afford to trade
- **Risk-Based Calculation**: Positions sized based on your risk tolerance (e.g., 0.2% per trade)
- **Exchange Limits Compliance**: Respects minimum notional values and position sizes
- **Liquidation Safety**: Ensures sufficient buffer against liquidation (1.5x+ safety ratio)

### 📊 **Multi-Exchange Volume Analysis**
- **5 Major Exchanges**: Binance, Bybit, OKX, Bitget, Gate.io
- **Real-Time Data**: Live volume metrics and market rankings
- **Smart Filtering**: Volume-based market selection with customizable thresholds
- **Enhanced Analysis**: Combines volume data with position sizing for optimal symbol selection

### 📈 **Advanced Trading Signals**
- **RSI Strategy**: Relative Strength Index with customizable parameters
- **MACD Strategy**: Moving Average Convergence Divergence signals
- **Multi-Timeframe**: 1m, 5m, 1h, 4h, 1d analysis
- **Confidence Scoring**: Signal strength assessment for better decision making

### 🤖 **Automated Job System**
- **Daily Volume Jobs**: Automated daily market analysis
- **Scheduled Execution**: Set and forget automation
- **Performance Tracking**: Historical analysis and performance metrics
- **Alert System**: Notifications for significant market changes

## 🛠️ Installation

### Quick Install (Recommended)
```bash
pip install -e .
```

After installation, the `aug` command will be available globally:
```bash
aug --help
```

### Development Install
```bash
git clone https://github.com/augustan-trading/augustan.git
cd augustan
pip install -e .
```

### Requirements
- Python 3.8+
- Internet connection for exchange APIs
- 50+ MB free disk space

## 🚀 Quick Start

### 1. **Find Tradeable Symbols for Your Budget**
```bash
aug position tradeable --budget 50
```
**Result**: List of symbols you can safely trade with $50.

### 2. **Analyze Specific Symbol Position Sizing**
```bash
aug position analyze --symbol DOGE/USDT  # Auto-fetches budget from wallet
```
**Result**: Detailed position sizing analysis with safety metrics.

### 3. **Enhanced Volume Analysis with Position Sizing**
```bash
aug volume analyze --enhanced --budget 50 --risk-percent 0.2
```
**Result**: Volume analysis + position sizing for top symbols.

### 4. **Generate Trading Signals for Affordable Symbols**
```bash
aug trading analyze --use-tradeable --budget 50
```
**Result**: RSI/MACD signals only for symbols within your budget.

## 📊 **Real Example Output**

```bash
$ aug position analyze --symbol DOGE/USDT  # Auto-fetches budget from wallet

📊 Position Sizing Analysis for DOGE/USDT
============================================================
Current Price: $0.2108
Stop Loss: $0.2066 (-2.0%)
Budget: $50.00 USDT
Risk per Trade: 0.5%
Leverage: 5x

✅ TRADEABLE
Position Size: 59.297913 DOGE
Position Value: $12.50
Required Margin: $2.50
Risk Amount: $0.25
Liquidation Price: $0.1695
Safety Ratio: 9.80x
============================================================
```

## 🎯 **Core Commands**

### **Position Sizing**
```bash
# Analyze specific symbol
aug position analyze --symbol BTC/USDT --budget 100

# Find tradeable symbols
aug position tradeable --budget 50 --limit 20

# Custom risk settings
aug position analyze --symbol ETH/USDT --budget 200 --risk-percent 1.0 --leverage 10
```

### **Volume Analysis**
```bash
# Basic volume analysis
aug volume analyze

# Enhanced with position sizing
aug volume analyze --enhanced --budget 50 --risk-percent 0.2

# Specific exchanges
aug volume analyze --exchanges bybit --min-volume 5000000
```

### **Trading Signals**
```bash
# Generate signals for top volume symbols
aug trading analyze

# Use only tradeable symbols
aug trading analyze --use-tradeable --budget 50

# Custom timeframe and strategies
aug trading analyze --timeframe 1h --strategies rsi macd
```

### **Job Management**
```bash
# Start daily volume job
aug job start --schedule

# Run job once
aug job run

# Check job status
aug job status
```

### **Configuration**
```bash
# Show current config
aug config show

# Validate config
aug config validate
```

## ⚙️ **Configuration**

Create `config/exchanges_config.json`:
```json
{
    "exchanges": {
        "binance": {"enabled": true},
        "bybit": {"enabled": true},
        "okx": {"enabled": true},
        "bitget": {"enabled": true},
        "gate": {"enabled": true}
    },
    "volume_analysis": {
        "min_volume_usd_24h": 1000000,
        "min_volume_rank": 200,
        "min_price_change_24h": -50,
        "max_price_change_24h": 500
    },
    "risk_management": {
        "max_budget": 50.0,
        "max_risk_per_trade": 0.002,
        "min_safety_ratio": 1.5,
        "default_leverage": 5
    }
}
```

## 🔧 **Advanced Usage**

### **Position Sizing System**

The position sizing system implements sophisticated risk management:

1. **Budget Filtering**: `min_feasible_notional = max(exchange_min_notional, min_qty * current_price)`
2. **Risk Calculation**: `position_size = risk_amount / (entry_price - stop_loss_price)`  
3. **Liquidation Safety**: `safety_ratio = liquidation_buffer / risk_buffer` (minimum 1.5x)
4. **Exchange Compliance**: All positions respect exchange minimum requirements

### **Safety Guidelines**

- **Never risk more than 2% per trade**
- **Maintain 1.5x+ safety ratio** (liquidation protection)
- **Start with small budgets** ($25-50) and conservative risk (0.2-0.5%)
- **Use stop-losses religiously**
- **Test with paper trading first**

## 📈 **Performance Examples**

**Expected Results for Different Budgets:**
- **$50 Budget**: ~5-10 tradeable symbols from top 50 volume markets
- **$200 Budget**: ~15-25 tradeable symbols from top 50 volume markets  
- **$500 Budget**: ~30-40 tradeable symbols from top 50 volume markets

**Live Performance Metrics:**
- ✅ **Real-time Analysis**: Position sizing calculated in seconds
- ✅ **Exchange Integration**: Fetches live limits from major exchanges
- ✅ **Safety Validation**: Proper liquidation risk assessment
- ✅ **Budget Compliance**: Accurate affordability filtering

## 🐍 **Python API Usage**

```python
from trading_system import PositionSizingCalculator, RiskManagementConfig, ExchangeLimitsFetcher

# Initialize components
risk_config = RiskManagementConfig(max_budget=50.0, max_risk_per_trade=0.002)
calculator = PositionSizingCalculator(risk_config)
limits_fetcher = ExchangeLimitsFetcher()

# Analyze position sizing
limits = limits_fetcher.fetch_symbol_limits("binance", "DOGE/USDT")
result = calculator.analyze_position_sizing(inputs)

print(f"Tradeable: {result.is_tradeable}")
print(f"Safety Ratio: {result.safety_ratio:.2f}x")
```

## 🔬 **Development**

### **Setup Development Environment**
```bash
git clone https://github.com/augustan-trading/augustan.git
cd augustan
pip install -e ".[dev]"
```

### **Run Tests**
```bash
python -m pytest tests/
```

### **Code Formatting**
```bash
black augustan/
flake8 augustan/
mypy augustan/
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Documentation**: This README and built-in help (`aug --help`)
- **Issues**: [GitHub Issues](https://github.com/augustan-trading/augustan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/augustan-trading/augustan/discussions)

## ⚠️ **Disclaimer**

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk and may not be suitable for all investors. Past performance is not indicative of future results. Always do your own research and consider your risk tolerance before trading.

---

**Built with ❤️ for the crypto trading community**

*Start trading smarter, not harder with Augustan!* 🚀📈💰