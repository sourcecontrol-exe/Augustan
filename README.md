# Augustan Trading Bot

A sophisticated Python-based algorithmic trading bot with comprehensive backtesting, multi-exchange support, and professional-grade risk management.

## 🚀 Key Features

- **🔬 Advanced Backtesting Engine**: 25+ technical indicators, strategy optimization, walk-forward analysis
- **📈 Real-Time Paper Trading**: Virtual trading with live WebSocket feeds and realistic execution
- **⚡ Live Data Feeds**: WebSocket streams + REST API fallback with automatic failover
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

# 3. Try paper trading (safe virtual trading)
python paper_trading/demo_paper_trading.py --quick

# 4. Run backtesting demo
python backtesting/demo_backtest.py

# 5. Switch environments
python configs/switch_env.py --switch testing  # or live
```

## 🔬 Backtesting & Paper Trading

### **Backtesting (Historical Data)**
```bash
# Full backtesting suite with optimization
python backtesting/run_backtest.py

# Quick demo with realistic results
python backtesting/demo_backtest.py
```

### **Paper Trading (Real-Time Virtual Trading)**
```bash
# Quick paper trading demo
python paper_trading/demo_paper_trading.py --quick

# Full automated paper trading session
python paper_trading/demo_paper_trading.py --full

# Live data feed demos
python paper_trading/live_feed_demo.py --websocket    # Real-time WebSocket
python paper_trading/live_feed_demo.py --combined     # WebSocket + REST fallback
```

### **Key Features**
- **25+ Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX, SuperTrend, Ichimoku
- **Strategy Optimization**: Grid search parameter optimization with walk-forward analysis
- **Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, VaR/CVaR, drawdown analysis
- **Realistic Execution**: Slippage modeling, commission costs, stop-loss/take-profit
- **Paper Trading**: Real-time virtual trading with live WebSocket feeds
- **Live Data Feeds**: WebSocket streams + REST API fallback with automatic failover
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

## 📈 Paper Trading with Live Feeds

### **Real-Time Paper Trading**
```python
from paper_trading import PaperTradingEngine, PaperTradingConfig
from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager

# Initialize components
data_service = DataService('ccxt', {'exchange_id': 'binance', 'testnet': True})
strategy = Strategy()
risk_manager = RiskManager()

# Configure paper trading
config = PaperTradingConfig(
    initial_capital=50000.0,
    commission_rate=0.001,
    slippage_rate=0.0005,
    max_position_size_pct=0.15
)

# Create paper trader
paper_trader = PaperTradingEngine(config, data_service, strategy, risk_manager)

# Run with live WebSocket feeds
await paper_trader.run_paper_trading(
    symbols=['BTC/USDT', 'ETH/USDT'], 
    duration_minutes=60, 
    use_live_feed=True  # Real-time data
)
```

### **Live Data Feed Options**
```python
from paper_trading.live_data_feed import create_simple_feed

# Create live feed
feed = create_simple_feed(['BTC/USDT', 'ETH/USDT'], data_service)

# Add price callback
def price_callback(market_data):
    print(f"{market_data.symbol}: ${market_data.price:.2f}")

feed.add_price_callback(price_callback)
await feed.start_feed()
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

# Test live data feeds
python paper_trading/live_feed_demo.py --info
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

**1. Backtesting (Historical)**
```bash
python backtesting/demo_backtest.py
```

**2. Paper Trading (Real-time Virtual)**
```bash
python paper_trading/demo_paper_trading.py --full
```

**3. Live Trading (Real Money)**
```bash
python configs/switch_env.py --switch live
python main.py  # Your live trading implementation
```

## 📊 Available Exchanges & Data Sources

### **Exchanges**
- **CCXT**: 100+ exchanges (Binance, Bybit, OKX, etc.)
- **Pi42**: Custom adapter for Pi42 exchange
- **Extensible**: Easy to add new exchange adapters

### **Live Data Sources**
- **WebSocket Streams**: Real-time price feeds (sub-second updates)
- **REST API**: Reliable polling fallback (1-60 second intervals)
- **Combined Mode**: WebSocket + REST with automatic failover

## 🚨 Risk Disclaimer

⚠️ **Educational purposes only**. Cryptocurrency trading involves significant risk. Past performance doesn't guarantee future results. Only trade with money you can afford to lose.

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch  
3. Add tests
4. Submit pull request

**Happy Trading! 🚀** *Start small, test thoroughly, prioritize risk management.*
