# Augustan Trading Bot

A sophisticated Python-based algorithmic trading bot with comprehensive backtesting, multi-exchange support, and professional-grade risk management.

## 🚀 Key Features

- **🔬 Advanced Backtesting Engine**: 25+ technical indicators, strategy optimization, walk-forward analysis
- **📊 Professional Analytics**: Sharpe ratio, drawdown analysis, risk-adjusted returns, trade statistics
- **🔄 Multi-Exchange Support**: CCXT adapter for 100+ exchanges, custom Pi42 adapter
- **⚙️ Environment Management**: Separate configs for testing, live trading, and development
- **🛡️ Risk Management**: ATR-based stop-loss, position sizing, portfolio monitoring
- **🧪 Comprehensive Testing**: 99%+ test coverage with automated validation

## 📋 Prerequisites

- Python 3.9+
- API keys for your chosen exchanges
- Basic understanding of cryptocurrency trading

## 🛠️ Quick Start

```bash
# 1. Clone and install
git clone <your-repo-url> && cd Augustan
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env  # Add your API keys

# 3. Run backtesting demo
python backtesting/demo_backtest.py

# 4. Switch environments
python configs/switch_env.py --switch testing  # or live
```

## 🔬 Backtesting Engine

### **Run Comprehensive Backtesting**
```bash
# Full backtesting suite with optimization
python backtesting/run_backtest.py

# Quick demo with realistic results
python backtesting/demo_backtest.py
```

### **Key Backtesting Features**
- **25+ Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX, SuperTrend, Ichimoku
- **Strategy Optimization**: Grid search parameter optimization with walk-forward analysis
- **Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, VaR/CVaR, drawdown analysis
- **Realistic Execution**: Slippage modeling, commission costs, stop-loss/take-profit
- **Strategy Comparison**: Side-by-side performance ranking and analysis

### **Custom Strategy Example**
```python
from backtesting.strategy_framework import RuleBasedStrategy, StrategyConfig, StrategyRule, StrategyCondition, SignalType
from backtesting.backtester import BacktestEngine, BacktestConfig

# Create custom strategy
strategy_config = StrategyConfig(
    name="My_Strategy",
    indicators=[{"name": "rsi", "params": {"length": 14}}],
    entry_rules=[
        StrategyRule(
            conditions=[StrategyCondition("rsi", "RSI_14", "<", 30)],
            signal=SignalType.BUY
        )
    ]
)

# Run backtest
engine = BacktestEngine(BacktestConfig(initial_capital=100000))
result = engine.run_backtest(RuleBasedStrategy(strategy_config), your_data)
```

## 🎯 Live Trading Usage

### **Basic Trading Setup**
```python
from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager

# Initialize components
ds = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
strategy = Strategy()
risk_mgr = RiskManager()

# Get market data and generate signals
data = ds.get_ohlcv('BTC/USDT', '1h', 100)
signal = strategy.generate_signal(data)

if signal == 'BUY':
    trade_details = risk_mgr.calculate_trade_details(data, signal)
    print(f"Position size: {trade_details['position_size']}")
```

### **Environment Management**
```bash
# Switch between environments
python configs/switch_env.py --switch testing  # Safe testing
python configs/switch_env.py --switch live     # Real trading

# Check current environment
python configs/switch_env.py --current
```

## 🧪 Testing & Validation

```bash
# Run comprehensive tests
python run_tests.py

# Test specific components
python -m pytest tests/test_risk_manager.py -v
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

## 📊 Available Exchanges

- **CCXT**: 100+ exchanges (Binance, Bybit, OKX, etc.)
- **Pi42**: Custom adapter for Pi42 exchange
- **Extensible**: Easy to add new exchange adapters

## 🚨 Risk Disclaimer

⚠️ **Educational purposes only**. Cryptocurrency trading involves significant risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose.

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch  
3. Add tests
4. Submit pull request

**Happy Trading! 🚀** *Start small, test thoroughly, prioritize risk management.*
