# API Key Security Guide

## 🔐 Why Secure Your API Keys?

Your API keys are like passwords to your trading account. If they get exposed, attackers can:
- Access your account and view balances
- Place unauthorized trades
- Withdraw funds
- Manipulate your trading strategy

**Never commit API keys to version control!**

## 🛡️ Security Setup

### Option 1: Automatic Migration (Recommended)

Run the security migration tool:

```bash
# Using the CLI command
aug live secure

# Or run the script directly
python3 secure_api_keys.py
```

This will:
1. Extract your API keys from config files
2. Create a `.env` file with your keys
3. Clean up config files (replace keys with `***REDACTED***`)
4. Update `.gitignore` to exclude `.env` files

### Option 2: Manual Setup

1. **Create `.env` file** in your project root:
```bash
touch .env
```

2. **Add your API keys** to `.env`:
```env
# Binance API Configuration
BINANCE_SPOT_API_KEY=your_actual_api_key_here
BINANCE_SPOT_SECRET_KEY=your_actual_secret_key_here
BINANCE_FUTURES_API_KEY=your_futures_api_key_here
BINANCE_FUTURES_SECRET_KEY=your_futures_secret_key_here

# Testnet Configuration
BINANCE_TESTNET=true

# Risk Management (optional)
DEFAULT_BUDGET=1000.0
MAX_RISK_PER_TRADE=0.01
MIN_SAFETY_RATIO=2.0
DEFAULT_LEVERAGE=3
```

3. **Verify `.env` is in `.gitignore`**:
```bash
echo ".env" >> .gitignore
```

## 🔍 How It Works

The system now uses a **SecureConfigLoader** that:

1. **Loads base configuration** from JSON files
2. **Overrides sensitive data** with environment variables
3. **Prioritizes environment variables** over config files
4. **Logs when using environment variables** for transparency

### Configuration Priority Order:
1. Environment variables (highest priority)
2. Config files (fallback)
3. Default values (lowest priority)

## 🧪 Testing Your Setup

After securing your API keys, test the system:

```bash
# Test with environment variables
aug position analyze --symbol BTC/USDT

# Test configuration loading
aug config show

# Test API connection
python3 test_binance_connection.py
```

## 🔒 Additional Security Measures

### 1. Binance API Key Restrictions

In your Binance account:
- **Enable IP restrictions** (only allow your IP addresses)
- **Set read-only permissions** for testing
- **Use separate keys** for spot and futures
- **Enable 2FA** on your Binance account

### 2. Environment Variable Best Practices

```bash
# Never do this:
export BINANCE_API_KEY=your_key  # Visible in shell history

# Do this instead:
echo "BINANCE_API_KEY=your_key" >> .env  # Hidden from history
```

### 3. Production Deployment

For production servers:
```bash
# Use system environment variables
sudo nano /etc/environment
# Add: BINANCE_API_KEY=your_key

# Or use Docker secrets
docker secret create binance_api_key - < .env
```

### 4. Backup Security

When backing up your project:
```bash
# Exclude sensitive files
tar --exclude='.env' --exclude='config/*.json' -czf backup.tar.gz .
```

## 🚨 Emergency Procedures

### If API Keys Are Compromised:

1. **Immediately revoke keys** in Binance account
2. **Generate new API keys**
3. **Update `.env` file** with new keys
4. **Check for unauthorized activity**
5. **Review access logs**

### Recovery Commands:
```bash
# Update environment variables
nano .env

# Test new keys
aug position analyze --symbol BTC/USDT

# Verify no sensitive data in config files
grep -r "api_key\|secret_key" config/
```

## 📋 Security Checklist

- [ ] API keys moved to `.env` file
- [ ] `.env` file added to `.gitignore`
- [ ] Config files cleaned of sensitive data
- [ ] IP restrictions enabled on Binance
- [ ] 2FA enabled on Binance account
- [ ] Separate keys for spot/futures (if needed)
- [ ] Read-only keys for testing
- [ ] Regular key rotation scheduled
- [ ] Backup procedures exclude sensitive data

## 🔧 Troubleshooting

### "API key not found" error:
```bash
# Check if .env file exists
ls -la .env

# Check if environment variables are loaded
python3 -c "import os; print(os.getenv('BINANCE_SPOT_API_KEY'))"
```

### "Invalid API key" error:
1. Verify keys in `.env` file
2. Check IP restrictions in Binance
3. Ensure testnet setting matches your keys

### Configuration not loading:
```bash
# Check config file structure
cat config/exchanges_config.json

# Test secure loader
python3 -c "from trading_system.config_loader import SecureConfigLoader; print(SecureConfigLoader().load_config())"
```

## 📚 Related Documentation

- [CLI Guide](CLI_GUIDE.md) - Command-line interface usage
- [Trading Modes Guide](TRADING_MODES_GUIDE.md) - Paper vs live trading
- [SAPI Testnet Guide](SAPI_TESTNET_GUIDE.md) - Testnet limitations

---

**Remember: Security is an ongoing process. Regularly review and update your security measures!**
