# Augustan Trading Bot

A Python-based algorithmic trading bot with a modular adapter system for multiple exchanges, featuring environment-based configuration management and comprehensive risk management.

## 🚀 Features

- **Multi-Exchange Support**: CCXT adapter for 100+ exchanges, custom Pi42 adapter
- **Environment-Based Configuration**: Separate configs for testing, live trading, and development
- **Advanced Risk Management**: ATR-based stop-loss, position sizing, portfolio risk monitoring
- **Modular Architecture**: Plugin-based adapter system for easy extension
- **Comprehensive Testing**: Unit tests with 99%+ coverage for core components
- **Professional Logging**: Structured logging with different levels and rotation
- **Configuration Validation**: Automatic validation of all configuration parameters

## 📋 Prerequisites

- Python 3.9+
- API keys for your chosen exchanges
- Basic understanding of cryptocurrency trading

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Augustan
   ```

2. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Copy the template and fill in your API keys
   cp .env.example .env
   
   # Edit .env with your actual API keys
   nano .env
   ```

## ⚙️ Configuration Management

The bot uses a sophisticated environment-based configuration system with three main environments:

### **🧪 Testing Environment** (`configs/testing/config.json`)
- **Purpose**: Development, testing, and backtesting
- **Settings**: Conservative parameters, testnet enabled
- **Risk**: Low risk per trade (0.5%), smaller capital ($1,000)
- **Features**: Debug logging, shorter timeframes

### **🚀 Live Trading Environment** (`configs/live/config.json`)
- **Purpose**: Production trading with real money
- **Settings**: Production parameters, testnet disabled
- **Risk**: Standard risk per trade (1%), larger capital ($10,000)
- **Features**: Production logging, longer timeframes, notifications

### **📋 Default Configuration** (`configs/default.json`)
- **Purpose**: Fallback configuration if others are not found
- **Settings**: Balanced parameters, testnet enabled by default

## 🔧 Environment Management

### **Quick Environment Commands**

```bash
# Show current environment
python3 configs/switch_env.py --current

# List available environments
python3 configs/switch_env.py --list

# Switch to testing environment
python3 configs/switch_env.py --switch testing

# Switch to live environment
python3 configs/switch_env.py --switch live

# Create testing environment (if it doesn't exist)
python3 configs/switch_env.py --create testing
```

### **Environment Variables**

```bash
# Force specific environment
export AUGUSTAN_ENV=testing
export AUGUSTAN_ENV=live

# Production indicators (auto-detects live environment)
export PRODUCTION=true
export LIVE_TRADING=true
export DEPLOYMENT_ENV=production
```

### **Programmatic Environment Control**

```python
from configs import config_manager

# Get current configuration
config = config_manager.get_all_config()

# Switch environments
config_manager.switch_environment('live')

# Access configuration values
timeframe = config_manager.get('trading.timeframe', '5m')
risk_per_trade = config_manager.get('risk_management.risk_per_trade', 0.01)
```

## 🎯 Basic Usage

### **1. Initialize the Bot**

```python
from config import config
from data_service import DataService
from strategy import Strategy
from risk_manager import RiskManager

# Initialize components
ds = DataService('ccxt', config={'exchange_id': 'binance'})
strategy = Strategy()
risk_mgr = RiskManager()
```

### **2. Fetch Market Data**

```python
# Get available markets
markets = ds.get_markets()
print(f"Available markets: {markets}")

# Get OHLCV data
ohlcv = ds.get_ohlcv('BTC/USDT', '1h', 100)
print(f"OHLCV data shape: {ohlcv.shape}")

# Get current ticker
ticker = ds.get_ticker('BTC/USDT')
print(f"Current price: {ticker.get('last')}")
```

### **3. Generate Trading Signals**

```python
# Generate trading signal
signal = strategy.generate_signal(ohlcv_dataframe)
print(f"Signal: {signal}")  # BUY, SELL, or HOLD

if signal == 'BUY':
    # Calculate position size and risk
    trade_details = risk_mgr.calculate_trade_details(ohlcv, signal)
    if trade_details:
        print(f"Position size: {trade_details['position_size']}")
        print(f"Stop-loss: {trade_details['stop_loss']}")
        print(f"Take-profit: {trade_details['take_profit']}")
```

### **4. Portfolio Risk Management**

```python
# Calculate portfolio risk
positions = [
    {'size': 10, 'current_price': 100},
    {'size': 5, 'current_price': 200}
]

risk_metrics = risk_mgr.calculate_portfolio_risk(positions)
print(f"Total exposure: ${risk_metrics['total_exposure']:,}")
print(f"Portfolio risk: {risk_metrics['portfolio_risk']:.2%}")
```

## 🔌 Exchange Adapters

### **Available Adapters**

- **CCXT Adapter**: Supports all CCXT-compatible exchanges (Binance, Bybit, OKX, etc.)
- **Pi42 Adapter**: Custom adapter for Pi42 exchange

### **Using Different Exchanges**

```python
from data_service import DataService

# Use CCXT adapter for Binance
binance_ds = DataService('ccxt', {
    'exchange_id': 'binance',
    'api_key': 'your_key',
    'api_secret': 'your_secret',
    'testnet': True
})

# Use Pi42 adapter
pi42_ds = DataService('pi42', {
    'api_key': 'your_pi42_key',
    'api_secret': 'your_pi42_secret'
})

# Switch between exchanges
ds = DataService('ccxt')
ds.switch_exchange('pi42', {
    'api_key': 'your_key',
    'api_secret': 'your_secret'
})
```

### **Context Manager Usage**

```python
# Automatic cleanup with context manager
with DataService('ccxt') as ds:
    data = ds.get_ohlcv('ETH/USDT', '15m', 50)
    # DataService automatically disconnects when exiting context
```

## 📊 Advanced Usage

### **Custom Strategy Implementation**

```python
from strategy import Strategy

class CustomStrategy(Strategy):
    def generate_signal(self, df):
        # Your custom logic here
        if self._rsi_oversold(df):
            return 'BUY'
        elif self._rsi_overbought(df):
            return 'SELL'
        return 'HOLD'
    
    def _rsi_oversold(self, df):
        # Custom RSI logic
        return df['rsi'].iloc[-1] < 30
    
    def _rsi_overbought(self, df):
        # Custom RSI logic
        return df['rsi'].iloc[-1] > 70
```

### **Risk Management Customization**

```python
from risk_manager import RiskManager

# Custom risk parameters
custom_risk = RiskManager()
custom_risk.risk_per_trade = 0.02  # 2% risk per trade
custom_risk.risk_reward_ratio = 3.0  # 3:1 risk-reward ratio

# Adjust position size based on volatility
volatility = 0.8  # High volatility
adjusted_size = custom_risk.adjust_position_size(100, volatility)
print(f"Adjusted position size: {adjusted_size}")
```

### **Batch Operations**

```python
# Fetch data for multiple symbols
symbols = ['BTC/USDT', 'ETH/USDT', 'ADA/USDT']
all_data = {}

for symbol in symbols:
    all_data[symbol] = ds.get_ohlcv(symbol, '1h', 100)
    print(f"Fetched {symbol}: {all_data[symbol].shape}")
```

## 🧪 Testing

### **Run All Tests**

```bash
# Run all tests with coverage
python3 run_tests.py

# Run specific test file
python3 run_tests.py tests/test_risk_manager.py

# Run tests with pytest directly
python3 -m pytest tests/ -v --cov=.
```

### **Test Coverage**

The bot includes comprehensive unit tests with:
- **Risk Manager**: 99% coverage
- **Configuration System**: 75% coverage
- **Overall Project**: 42% coverage (increasing)

## 📈 Backtesting

### **Run Backtests**

```bash
cd backtesting
python3 run_backtest.py
```

### **Custom Backtest Parameters**

```python
from backtesting.backtester import Backtester

backtester = Backtester(
    strategy=Strategy(),
    data=historical_data,
    initial_capital=1000
)

results = backtester.run()
print(f"Total return: {results['total_return']}%")
```

## 🔒 Security Best Practices

### **API Key Management**
- **Never commit API keys** to version control
- Use `.env` file for sensitive information
- Enable 2FA on all exchange accounts
- Start with testnet/sandbox mode

### **Configuration Security**
- **Live trading configs** are excluded from version control
- **Environment separation** prevents accidental live trading
- **Configuration validation** ensures integrity
- **Testnet defaults** for safety

### **Risk Management**
- **Always test** on testnet first
- **Start small** and gradually increase
- **Monitor performance** closely
- **Use stop-losses** religiously

## 🐛 Troubleshooting

### **Common Issues**

1. **Configuration Not Found**
   ```bash
   # Check if config files exist
   ls -la configs/
   
   # Verify environment variable
   echo $AUGUSTAN_ENV
   ```

2. **Import Errors**
   ```bash
   # Ensure you're using Python 3
   python3 --version
   
   # Install dependencies
   pip3 install -r requirements.txt
   ```

3. **API Connection Issues**
   - Verify API keys are correct
   - Check if exchange is accessible
   - Ensure proper permissions on API keys

4. **Configuration Validation Errors**
   ```bash
   # Validate configuration
   python3 configs/switch_env.py --current
   
   # Check for JSON syntax errors
   python3 -m json.tool configs/testing/config.json
   ```

### **Getting Help**

- Check the logs for error messages
- Verify configuration files
- Test individual components separately
- Consult exchange API documentation

## 📚 Configuration Reference

### **Trading Configuration**
```json
{
  "timeframe": "3m",
  "stake_currency": "USDT",
  "total_capital": 1000,
  "exchange_type": "future",
  "testnet": true
}
```

### **Risk Management**
```json
{
  "risk_per_trade": 0.01,
  "risk_reward_ratio": 2.0,
  "stop_loss_multiplier": 2.0,
  "max_open_trades": 3
}
```

### **Scanner Configuration**
```json
{
  "base_currency": "USDT",
  "market_limit": 150,
  "min_24h_change": 5.0,
  "max_24h_change": 20.0
}
```

## 🔄 Advanced Configuration

### **Adding New Configuration Options**

1. **Add to all environment configs** (testing, live, default)
2. **Update config_manager.py** with getter methods if needed
3. **Update validation** in config_manager.py
4. **Update documentation** in README files

### **Custom Adapters**

```python
from adapters.base_adapter import BaseAdapter

class CustomExchangeAdapter(BaseAdapter):
    def __init__(self, config):
        super().__init__(config)
        # Your custom initialization
    
    def connect(self):
        # Your connection logic
        pass
    
    # Implement all required methods...

# Register custom adapter
from adapters import register_adapter
register_adapter('custom_exchange', CustomExchangeAdapter)
```

## 📊 Performance Monitoring

### **Health Checks**

```python
# Check adapter health
if ds.is_healthy():
    print("Data service is healthy")
else:
    print("Data service has issues")

# Get available exchanges
available = ds.get_available_exchanges()
print(f"Available adapters: {available}")
```

### **Logging Configuration**

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# File logging with rotation
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler('trading_bot.log', maxBytes=10*1024*1024, backupCount=5)
logging.getLogger().addHandler(handler)
```

## 🚨 Important Notes

### **Risk Disclaimer**
- This bot is for educational purposes
- Cryptocurrency trading involves significant risk
- Past performance doesn't guarantee future results
- Only trade with money you can afford to lose

### **Testing Requirements**
- Always test on testnet first
- Start with small amounts
- Monitor the bot's performance closely
- Have stop-loss mechanisms in place

### **Maintenance**
- Regularly update exchange API keys
- Monitor configuration changes
- Keep dependencies updated
- Review logs for issues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the configuration documentation
- Test with the provided examples
- Consult the exchange-specific documentation

---

**Happy Trading! 🚀📈**

*Remember: Start small, test thoroughly, and always prioritize risk management.*
