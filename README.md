# Augustan - Advanced Algorithmic Trading Bot

A comprehensive, service-based trading system with backtesting, paper trading, and live trading capabilities using real cryptocurrency market data.

## 🏗️ Service-Based Architecture

```
Augustan/
├── services/                       # Core trading services
│   ├── data/                      # Data fetching & management
│   │   ├── data_loader.py         # Multi-source data loading (CCXT, yfinance)
│   │   └── data_service.py        # Unified data interface
│   ├── trading/                   # Strategy & execution
│   │   └── strategy.py            # RSI+MACD, Bollinger+RSI, Mean Reversion
│   ├── backtesting/               # Backtesting engine
│   │   ├── backtester.py          # Main backtesting engine
│   │   ├── indicators.py          # 25+ technical indicators
│   │   ├── performance_metrics.py # Performance analytics
│   │   └── strategy_framework.py  # Strategy framework
│   ├── paper_trading/             # Paper trading simulation
│   │   ├── paper_trader.py        # Virtual trading engine
│   │   └── paper_backtest_bridge.py # Integration bridge
│   ├── risk/                      # Risk management
│   │   └── risk_manager.py        # ATR-based position sizing
│   └── adapters/                  # Exchange adapters
│       ├── base_adapter.py        # Abstract adapter interface
│       ├── ccxt_adapter.py        # CCXT integration (100+ exchanges)
│       └── pi42_adapter.py        # Custom Pi42 adapter
├── core/                          # Shared components
│   ├── config/                    # Configuration management
│   ├── exceptions/                # Custom exceptions
│   └── utils/                     # Shared utilities
├── cli/                           # Command line interface
├── scripts/                       # Entry point scripts
├── tests/                         # Test suite
├── data/                          # Data storage
├── results/                       # Backtest results
└── docs/                          # Documentation
```

## 🚀 Key Features

- **🔬 Advanced Backtesting Engine**: Real crypto data via CCXT, 25+ technical indicators, strategy optimization
- **📈 Real-Time Paper Trading**: Virtual trading with live market data and realistic execution
- **💰 Real Crypto Data**: Direct integration with Binance, OKX, Bybit, KuCoin via CCXT
- **📊 Professional Analytics**: Sharpe ratio, drawdown analysis, risk-adjusted returns, trade statistics
- **🔄 Multi-Exchange Support**: CCXT adapter for 100+ exchanges, custom Pi42 adapter
- **⚙️ Service-Based Architecture**: Clean separation of concerns, easy to maintain and extend
- **🛡️ Risk Management**: ATR-based stop-loss, position sizing, portfolio monitoring
- **🧪 Comprehensive Testing**: 99%+ test coverage with automated validation

## 📋 Prerequisites

- Python 3.8+
- API keys for your chosen exchanges
- Basic understanding of cryptocurrency trading

## 🛠️ Quick Start

### Installation
```bash
# Install in development mode
pip install -e .

# Or install from source
python setup.py install
```

### Usage

#### Command Line Interface
```bash
# Show available commands
augustan

# Run backtesting with real crypto data
augustan-backtest --symbol BTC/USDT --exchange binance --timeframe 1h

# Run paper trading (quick demo)
augustan-paper --quick

# Run paper trading (full session)
augustan-paper --full

# Run tests
augustan-test
```

#### Direct Script Execution
```bash
# Backtesting with real crypto data
python scripts/run_backtest.py --symbol ETH/USDT --exchange binance --timeframe 4h

# Paper trading demo
python scripts/demo_paper_trading.py --quick

# Main trading bot
python scripts/main.py
```

## 🔬 Backtesting & Paper Trading

### **Backtesting (Real Crypto Data)**
```bash
# Backtest BTC with real Binance data
augustan-backtest --symbol BTC/USDT --exchange binance --timeframe 1h

# Compare all strategies on Ethereum
augustan-backtest --compare-all --symbol ETH/USDT --exchange okx --timeframe 4h

# Optimize strategy parameters
augustan-backtest --optimize --strategy rsi_macd --symbol SOL/USDT --limit 500

# Test different crypto pairs
augustan-backtest --symbol ADA/USDT --exchange bybit --timeframe 1d
```

### **Paper Trading (Real-Time Virtual Trading)**
```bash
# Quick paper trading demo (1 minute)
augustan-paper --quick

# Full automated paper trading session (30 minutes)
augustan-paper --full

# Custom duration and symbol
python scripts/demo_paper_trading.py --symbol ETH/USDT --duration 10
```

### **Key Features**
- **Real Crypto Data**: Direct CCXT integration with Binance, OKX, Bybit, KuCoin
- **25+ Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX, SuperTrend, Ichimoku
- **Strategy Optimization**: Grid search parameter optimization with walk-forward analysis
- **Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, VaR/CVaR, drawdown analysis
- **Realistic Execution**: Slippage modeling, commission costs, stop-loss/take-profit
- **Paper Trading**: Real-time virtual trading with live market data
- **Strategy Comparison**: Side-by-side performance ranking and analysis

### **Custom Strategy Example**
```python
from services.trading import RSIMACDStrategy, BollingerRSIStrategy, MeanReversionStrategy
from services.backtesting import AugustanBacktester, BacktestConfig
from services.data import DataLoader

# Load real crypto data
loader = DataLoader()
data = loader.load_data('BTC/USDT', source='binance', timeframe='1h', limit=1000)

# Configure backtesting
config = BacktestConfig(
    initial_capital=10000,
    commission=0.001,
    margin=1.0
)

# Run backtest with real data
backtester = AugustanBacktester(config)
results = backtester.run_backtest(data, RSIMACDStrategy)
```

## 📈 Real Crypto Data Integration

### **Supported Exchanges & Timeframes**
```python
from services.data import DataLoader, get_crypto_pairs

# Initialize data loader
loader = DataLoader()

# Supported exchanges
exchanges = ['binance', 'okx', 'bybit', 'kucoin']

# Supported timeframes
timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']

# Popular crypto pairs
pairs = get_crypto_pairs()
# ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', ...]

# Load real market data
btc_data = loader.load_data('BTC/USDT', source='binance', timeframe='1h', limit=1000)
eth_data = loader.load_data('ETH/USDT', source='okx', timeframe='4h', limit=500)
```

### **Paper Trading with Real Data**
```python
from services.paper_trading import PaperTradingEngine
from services.trading import RSIMACDStrategy
from services.data import DataLoader
from core.config import ConfigManager

# Initialize components
config_manager = ConfigManager()
config = config_manager.get_active_config()
paper_trader = PaperTradingEngine(config)
strategy = RSIMACDStrategy()

# Run paper trading with real market data
await paper_trader.start_session(
    strategy=strategy,
    symbol='BTC/USDT',
    duration_minutes=30
)
```

### **Environment Management**
```bash
# Switch between environments
python core/config/switch_env.py --switch testing  # Safe testing
python core/config/switch_env.py --switch live     # Real trading

# Check current environment
python core/config/switch_env.py --current
```

## 🧪 Testing & Validation

```bash
# Run comprehensive tests
augustan-test

# Test specific components
python -m pytest tests/test_risk_manager.py -v

# Test backtesting with real data
augustan-backtest --symbol BTC/USDT --exchange binance --limit 100
```

**Test Coverage**: 99% risk management, 75% configuration system

## 🔒 Security & Risk Management

### **Safety First**
- **Always start with testnet** - Never risk real money initially
- **Environment separation** - Testing vs live trading configs
- **API key security** - Use `.env` file, never commit keys
- **Position sizing** - Risk only 0.5-1% per trade

### **Configuration**
```json
{
  "risk_per_trade": 0.01,
  "risk_reward_ratio": 2.5,
  "stop_loss_multiplier": 2.0,
  "testnet": true
}
```

## 🐛 Troubleshooting

**Common Issues:**
- **Import errors**: `pip install -r requirements.txt`
- **Config not found**: `python configs/switch_env.py --current`
- **API issues**: Verify keys and exchange connectivity

## 🔄 Trading Progression Path

**1. Backtesting (Real Crypto Data)**
```bash
augustan-backtest --symbol BTC/USDT --exchange binance --timeframe 1h
```

**2. Paper Trading (Real-time Virtual)**
```bash
augustan-paper --full
```

**3. Live Trading (Real Money)**
```bash
python core/config/switch_env.py --switch live
python scripts/main.py  # Your live trading implementation
```

## 📊 Available Exchanges & Data Sources

### **Exchanges**
- **CCXT**: 100+ exchanges (Binance, Bybit, OKX, etc.)
- **Pi42**: Custom adapter for Pi42 exchange
- **Extensible**: Easy to add new exchange adapters

### **Crypto Data Sources**
- **CCXT Integration**: Real-time data from Binance, OKX, Bybit, KuCoin
- **Multiple Timeframes**: 1m, 5m, 15m, 1h, 4h, 1d intervals
- **Automatic Fallback**: CCXT → yfinance → synthetic data (if needed)

## 🚨 Risk Disclaimer

⚠️ **Educational purposes only**. Cryptocurrency trading involves significant risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose.

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch  
3. Add tests
4. Submit pull request

**Happy Trading! 🚀** *Start small, test thoroughly, prioritize risk management.*
