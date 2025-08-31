# Configuration Management

This directory contains configuration files for different environments of the Augustan Trading Bot.

## 📁 Directory Structure

```
configs/
├── README.md              # This file
├── __init__.py            # Package initialization
├── config_manager.py      # Configuration management system
├── switch_env.py          # Environment switching utility
├── default.json           # Default/fallback configuration
├── testing/               # Testing environment
│   └── config.json        # Testing configuration
└── live/                  # Live trading environment
    └── config.json        # Live trading configuration
```

## 🔧 Configuration Environments

### 🧪 Testing Environment (`configs/testing/config.json`)
- **Purpose**: Development, testing, and backtesting
- **Settings**: Conservative parameters, testnet enabled
- **Risk**: Low risk per trade (0.5%), smaller capital ($1,000)
- **Features**: Debug logging, shorter timeframes

### 🚀 Live Trading Environment (`configs/live/config.json`)
- **Purpose**: Production trading with real money
- **Settings**: Production parameters, testnet disabled
- **Risk**: Standard risk per trade (1%), larger capital ($10,000)
- **Features**: Production logging, longer timeframes, notifications

### 📋 Default Configuration (`configs/default.json`)
- **Purpose**: Fallback configuration if others are not found
- **Settings**: Balanced parameters, testnet enabled by default
- **Risk**: Standard risk per trade (1%), moderate capital ($1,000)

## 🚀 Usage

### Environment Switching

Use the `switch_env.py` utility to manage configurations:

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

### Environment Variables

Set environment variables to control configuration loading:

```bash
# Force testing environment
export AUGUSTAN_ENV=testing

# Force live environment
export AUGUSTAN_ENV=live

# Production indicators (auto-detects live environment)
export PRODUCTION=true
export LIVE_TRADING=true
export DEPLOYMENT_ENV=production
```

### Programmatic Usage

```python
from configs import config_manager

# Get current configuration
config = config_manager.get_all_config()

# Get specific configuration sections
trading_config = config_manager.get_trading_config()
risk_config = config_manager.get_risk_config()

# Switch environments
config_manager.switch_environment('live')

# Get configuration values
timeframe = config_manager.get('trading.timeframe', '5m')
risk_per_trade = config_manager.get('risk_management.risk_per_trade', 0.01)
```

## ⚙️ Configuration Sections

### Trading Configuration
- `timeframe`: Trading timeframe (1m, 3m, 5m, 15m, 1h, 4h, 1d)
- `stake_currency`: Base currency for trading (USDT, USD, INR)
- `total_capital`: Total capital available for trading
- `exchange_type`: Type of trading (spot, future, margin)
- `testnet`: Whether to use testnet/sandbox

### Scanner Configuration
- `base_currency`: Base currency for market scanning
- `market_limit`: Maximum number of markets to scan
- `min_24h_change`: Minimum 24h price change percentage
- `max_24h_change`: Maximum 24h price change percentage

### Risk Management
- `risk_per_trade`: Risk per trade as percentage of capital
- `risk_reward_ratio`: Target risk-reward ratio
- `stop_loss_multiplier`: ATR multiplier for stop-loss
- `max_open_trades`: Maximum number of open trades
- `max_daily_loss`: Maximum daily loss percentage
- `max_portfolio_risk`: Maximum portfolio risk percentage

### Strategy Parameters
- `rsi_length`: RSI calculation period
- `rsi_oversold`: RSI oversold threshold
- `rsi_overbought`: RSI overbought threshold
- `macd_fast`: MACD fast period
- `macd_slow`: MACD slow period
- `macd_signal`: MACD signal period
- `ema_short`: Short EMA period
- `ema_long`: Long EMA period

### Exchange Configuration
- `enabled`: Whether the exchange is enabled
- `default_type`: Default trading type
- `testnet`: Whether to use testnet

### Trading Sessions
- `start`: Session start hour (UTC)
- `end`: Session end hour (UTC)
- `enabled`: Whether the session is enabled

## 🔒 Security Considerations

### Live Trading Configuration
- **Never commit** live trading configurations to version control
- **Use environment variables** for sensitive information (API keys)
- **Enable 2FA** on all exchange accounts
- **Start with small amounts** and gradually increase

### Testing Configuration
- **Always use testnet** for testing
- **Use small capital amounts** for realistic testing
- **Test all features** before going live

## 📝 Adding New Configuration Options

1. **Add to all environment configs** (testing, live, default)
2. **Update config_manager.py** with getter methods if needed
3. **Update validation** in config_manager.py
4. **Update documentation** in this README

## 🐛 Troubleshooting

### Configuration Not Found
```bash
# Check if config files exist
ls -la configs/

# Check current working directory
pwd

# Verify environment variable
echo $AUGUSTAN_ENV
```

### Invalid Configuration
```bash
# Validate configuration
python3 configs/switch_env.py --current

# Check for JSON syntax errors
python3 -m json.tool configs/testing/config.json
```

### Environment Switching Issues
```bash
# Force specific environment
export AUGUSTAN_ENV=testing

# Restart Python process
python3 your_script.py
```

## 📚 Examples

### Custom Configuration
```python
from configs import ConfigManager

# Create custom configuration
custom_config = ConfigManager('testing')
custom_config.switch_environment('live')

# Access configuration
timeframe = custom_config.get('trading.timeframe')
risk_per_trade = custom_config.get('risk_management.risk_per_trade')
```

### Configuration Validation
```python
from configs import config_manager

# Validate configuration
if config_manager.validate():
    print("Configuration is valid")
else:
    print("Configuration validation failed")
```

### Environment Information
```python
from configs import config_manager

# Get environment info
info = config_manager.get_environment_info()
print(f"Current environment: {info['environment']}")
print(f"Testnet enabled: {info['testnet']}")
print(f"Total capital: ${info['total_capital']:,}")
```
