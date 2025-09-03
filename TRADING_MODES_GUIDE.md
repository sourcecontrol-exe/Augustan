# 🎯 Trading Modes Guide

## Overview

The Augustan Trading System now supports **separate configurations** for paper trading and live trading, ensuring you can safely test strategies before using real money.

## 📁 Configuration Files

### `config/paper_trading_config.json`
- **Purpose**: Safe testing environment
- **API**: Binance testnet (no real money)
- **Risk**: Conservative settings
- **Default**: Used when no mode is specified

### `config/live_trading_config.json`
- **Purpose**: Real money trading
- **API**: Binance mainnet (real money)
- **Risk**: More aggressive settings
- **Warning**: Requires explicit confirmation

### `config/exchanges_config.json`
- **Purpose**: Active configuration (copied from paper/live)
- **Usage**: System reads from this file
- **Management**: Automatically managed by `config switch` command

## 🔧 Risk Management Settings

### Paper Trading (Conservative)
```json
{
  "risk_management": {
    "default_budget": 1000.0,
    "max_risk_per_trade": 0.01,        // 1% risk per trade
    "min_safety_ratio": 2.0,           // 2x safety buffer
    "default_leverage": 3,             // 3x leverage
    "max_position_percent": 0.05,      // 5% of budget per position
    "max_positions": 3,                 // Max 3 concurrent positions
    "emergency_stop_loss": 5.0        // 5% emergency stop loss
  }
}
```

### Live Trading (Aggressive)
```json
{
  "risk_management": {
    "default_budget": 5000.0,
    "max_risk_per_trade": 0.02,        // 2% risk per trade
    "min_safety_ratio": 1.5,           // 1.5x safety buffer
    "default_leverage": 5,             // 5x leverage
    "max_position_percent": 0.1,        // 10% of budget per position
    "max_positions": 5,                 // Max 5 concurrent positions
    "emergency_stop_loss": 10.0        // 10% emergency stop loss
  }
}
```

## 🚀 Usage Examples

### 1. Paper Trading (Safe Testing)
```bash
# Use paper trading mode
aug --mode paper position analyze --symbol BTC/USDT

# Switch to paper trading permanently
aug config switch --mode paper

# Then use normally
aug position analyze --symbol BTC/USDT
```

### 2. Live Trading (Real Money)
```bash
# Use live trading mode (with warnings)
aug --mode live position analyze --symbol BTC/USDT

# Switch to live trading permanently
aug config switch --mode live

# Then use normally (with real money)
aug position analyze --symbol BTC/USDT
```

### 3. Configuration Management
```bash
# View current risk settings
aug config show --section risk

# Update risk settings
aug config update --section risk_management --default-budget 2000 --max-risk-per-trade 0.015

# Switch between modes
aug config switch --mode paper
aug config switch --mode live
```

## ⚠️ Safety Features

### Live Trading Warnings
When using live trading mode, the system will:
1. **Display warnings** about real money usage
2. **Require confirmation** before proceeding
3. **Show current risk settings** for review
4. **Remind you** to test in paper mode first

### Configuration Validation
- **API Keys**: Validates API keys are configured
- **Risk Limits**: Ensures risk settings are reasonable
- **Testnet Check**: Confirms testnet is disabled for live trading
- **Budget Check**: Validates budget is appropriate for live trading

## 🔄 Workflow Recommendations

### 1. Development Phase
```bash
# Start with paper trading
aug config switch --mode paper

# Test your strategies
aug position analyze --symbol BTC/USDT
aug volume analyze --enhanced
aug trading analyze --use-tradeable
```

### 2. Testing Phase
```bash
# Test with paper trading
aug --mode paper live test

# Verify everything works
aug --mode paper live monitor --symbols BTC/USDT ETH/USDT
```

### 3. Live Trading Phase
```bash
# Setup live trading
python3 setup_live_trading.py

# Switch to live mode
aug config switch --mode live

# Start live trading
aug --mode live position analyze --symbol BTC/USDT
```

## 📊 Configuration Comparison

| Setting | Paper Trading | Live Trading |
|---------|---------------|--------------|
| **Budget** | $1,000 | $5,000 |
| **Risk per Trade** | 1% | 2% |
| **Leverage** | 3x | 5x |
| **Max Positions** | 3 | 5 |
| **Safety Ratio** | 2.0x | 1.5x |
| **API** | Testnet | Mainnet |
| **Money** | Virtual | Real |

## 🛡️ Best Practices

### Before Live Trading
1. **Test thoroughly** in paper mode
2. **Verify strategies** work as expected
3. **Configure API keys** in live config
4. **Review risk settings** carefully
5. **Start small** with conservative positions

### Risk Management
1. **Never exceed** your risk limits
2. **Monitor positions** regularly
3. **Use stop losses** consistently
4. **Diversify** across multiple symbols
5. **Keep emergency funds** available

### Configuration Management
1. **Backup configurations** regularly
2. **Version control** your config files
3. **Document changes** to risk settings
4. **Test changes** in paper mode first
5. **Review settings** before live trading

## 🆘 Troubleshooting

### Common Issues

**"Configuration file not found"**
```bash
# Initialize configuration
aug config init --force
```

**"API keys not configured"**
```bash
# Setup live trading
python3 setup_live_trading.py
```

**"Testnet still enabled"**
```bash
# Check configuration
aug config show --section binance

# Update to disable testnet
aug config update --section binance --testnet false
```

**"Risk settings too aggressive"**
```bash
# Switch to paper trading
aug config switch --mode paper

# Or update risk settings
aug config update --section risk_management --max-risk-per-trade 0.01
```

## 📞 Support

If you need help with configuration:
1. Check the current settings: `aug config show`
2. Review the CLI guide: `CLI_GUIDE.md`
3. Test in paper mode first
4. Start with conservative settings

Remember: **Always test in paper mode before live trading!**
