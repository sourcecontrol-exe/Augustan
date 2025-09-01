# Futures Trading System

A comprehensive cryptocurrency futures trading system optimized for high-volume markets with automated volume analysis, multi-exchange support, and intelligent market selection.

## 🚀 Key Features

### 📊 **Multi-Exchange Volume Analysis**
- **5 Major Exchanges**: Binance, Bybit, OKX, Bitget, Gate.io
- **Real-time Volume Metrics**: 24h volume, price changes, market rankings
- **Intelligent Filtering**: Minimum $1M daily volume threshold
- **Market Ranking**: Volume-based scoring and recommendations

### 🤖 **Automated Daily Jobs**
- **Scheduled Volume Analysis**: Daily at 9:00 AM (configurable)
- **Market Discovery**: Automatically finds top futures markets
- **Data Retention**: 30-day historical data storage
- **JSON Export**: Structured data for further analysis

### 📈 **Futures-Optimized Trading**
- **Volume-Based Selection**: Trades only high-liquidity markets
- **RSI & MACD Strategies**: Adapted for futures volatility
- **Multi-Symbol Analysis**: Processes top 20 markets simultaneously
- **4-Hour Timeframe**: Optimized for futures trading patterns

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Daily Volume   │    │  Futures Data    │    │  Strategy       │
│  Analysis Job   │───▶│  Feeder          │───▶│  Engine         │
│  (Scheduled)    │    │  (5 Exchanges)   │    │  (RSI + MACD)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Volume Data    │    │  Market Rankings │    │  Trading        │
│  Storage        │    │  & Filtering     │    │  Signals        │
│  (JSON Files)   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📦 Installation

1. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure Exchanges** (Optional):
   ```bash
   # Edit config/exchanges_config.json with your API keys
   nano config/exchanges_config.json
   ```

## 🎯 Usage

### **1. Volume Analysis Only**
```bash
python3 futures_main.py --volume-analysis
```
- Analyzes all futures markets across 5 exchanges
- Generates volume rankings and recommendations
- Saves results to `volume_data/` directory

### **2. Trading Analysis Only**
```bash
python3 futures_main.py --trading-analysis --timeframe 4h
```
- Uses previously analyzed volume data
- Runs RSI/MACD strategies on top markets
- Generates BUY/SELL signals with confidence scores

### **3. Complete Analysis** (Default)
```bash
python3 futures_main.py
```
- Runs both volume and trading analysis
- Provides comprehensive market overview
- Saves all results with timestamps

### **4. Daily Scheduled Job**
```bash
python3 futures_main.py --daily-job
```
- Runs continuous scheduler
- Executes volume analysis daily at 9:00 AM
- Maintains rolling 30-day data history

### **5. Custom Symbol Analysis**
```bash
python3 futures_main.py --trading-analysis --symbols BTCUSDT ETHUSDT SOLUSDT
```

## 📊 Sample Output

### Volume Analysis Results
```
================================================================================
FUTURES VOLUME ANALYSIS - 2025-09-01
================================================================================
📊 Total Markets Analyzed: 351
🏆 Recommended Markets: 49
💰 Total 24h Volume: $26,450,556,666
📈 Markets >$10M Volume: 112
🚀 Markets >$100M Volume: 19
👑 Top Volume Market: ETH/USDT:USDT ($7,507,053,058)

📋 Exchanges Analyzed:
  • BYBIT: 351 markets, $26,450,556,666 volume
  • BINANCE: 0 markets, $0 volume (API config needed)

🎯 Top 10 Recommended Symbols:
   1. ETH/USDT:USDT
   2. BTC/USDT:USDT
   3. SOL/USDT:USDT
   4. XRP/USDT:USDT
   5. WLFI/USDT:USDT
   6. DOGE/USDT:USDT
   7. TRUMP/USDT:USDT
   8. ADA/USDT:USDT
   9. FARTCOIN/USDT:USDT
  10. SUI/USDT:USDT
```

### Trading Signals
```
📊 BTC/USDT:USDT (FUTURES)
----------------------------------------
🟢 RSI - BUY
   Price: $112152.8000
   Confidence: 63.24%
   Time: 2025-08-21T21:30:00
   RSI: 29.03

🟢 MACD - BUY
   Price: $108656.9000
   Confidence: 70.00%
   Time: 2025-08-31T09:30:00
   MACD: -868.8039
```

## 🔧 Configuration

### Exchange Configuration (`config/exchanges_config.json`)
```json
{
  "binance": {
    "api_key": "your_api_key",
    "secret": "your_secret",
    "enabled": true,
    "testnet": false
  },
  "volume_settings": {
    "min_volume_usd_24h": 1000000,
    "min_volume_rank": 200,
    "max_markets_per_exchange": 100
  },
  "job_settings": {
    "schedule_time": "09:00",
    "retention_days": 30,
    "output_directory": "volume_data"
  }
}
```

### Volume Filtering Criteria
- **Minimum Volume**: $1M USD daily volume
- **Maximum Rank**: Top 200 markets by volume
- **Recommended Markets**: Top 50 highest-scoring markets
- **Scoring Formula**: `Volume (50%) + Volatility (20%) + Liquidity (30%)`

## 📁 File Structure

```
Augustan/
├── futures_main.py              # Main futures application
├── test_futures.py              # Test suite
├── config/
│   └── exchanges_config.json    # Exchange configuration
├── volume_data/                 # Volume analysis results
│   ├── latest_volume_analysis.json
│   └── futures_volume_analysis_*.json
├── src/
│   ├── core/
│   │   ├── models.py           # Core data models
│   │   └── futures_models.py   # Futures-specific models
│   ├── data_feeder/
│   │   ├── binance_feeder.py   # Original data feeder
│   │   └── futures_data_feeder.py # Multi-exchange futures feeder
│   ├── jobs/
│   │   └── daily_volume_job.py # Scheduled volume analysis
│   └── strategy_engine/        # Trading strategies
└── logs/                       # Application logs
```

## 🔄 Daily Workflow

1. **9:00 AM**: Automated volume analysis runs
2. **Data Collection**: Fetches metrics from all configured exchanges
3. **Market Ranking**: Calculates volume-based scores
4. **Filtering**: Identifies top 50 recommended markets
5. **Storage**: Saves results to JSON files
6. **Cleanup**: Removes files older than 30 days

## 📈 Trading Strategy Details

### RSI Strategy (Futures-Optimized)
- **Oversold**: RSI ≤ 30 → BUY signal
- **Overbought**: RSI ≥ 70 → SELL signal
- **Confidence**: Higher for extreme RSI values
- **Period**: 14 candles (default)

### MACD Strategy (Futures-Optimized)
- **Bullish Crossover**: MACD crosses above signal line → BUY
- **Bearish Crossover**: MACD crosses below signal line → SELL
- **Enhanced Confidence**: Higher when MACD is in oversold/overbought territory
- **Parameters**: Fast EMA (12), Slow EMA (26), Signal (9)

## 🚨 Risk Management Features

- **Volume-Based Filtering**: Only trades liquid markets
- **Confidence Scoring**: Weighted signal reliability
- **Multi-Timeframe Support**: 1m, 5m, 1h, 4h, 1d
- **Exchange Diversification**: Reduces single-point-of-failure risk

## 🛠️ Advanced Usage

### Custom Volume Thresholds
```python
# Modify in futures_data_feeder.py
self.min_volume_usd_24h = 5_000_000  # $5M minimum
self.min_volume_rank = 100           # Top 100 only
```

### Adding New Exchanges
```python
# Add to ExchangeType enum in futures_models.py
class ExchangeType(Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    YOUR_EXCHANGE = "your_exchange"
```

### Custom Scheduling
```python
# Modify in daily_volume_job.py
self.job_time = "15:30"  # Run at 3:30 PM
```

## 📊 Performance Metrics

- **Analysis Speed**: ~30 seconds for 351 markets
- **Data Processing**: 19 symbols with 100 candles each
- **Memory Efficiency**: Streaming processing for large datasets
- **API Rate Limiting**: Built-in rate limiting for all exchanges

## 🔍 Monitoring & Debugging

### Log Files
```bash
# View application logs
tail -f logs/futures_trading_system.log

# View volume analysis logs
grep "Volume analysis" logs/futures_trading_system.log
```

### Test System Health
```bash
python3 test_futures.py
```

## 🚀 Production Deployment

### 1. **Server Setup**
```bash
# Install as systemd service
sudo cp futures-trading.service /etc/systemd/system/
sudo systemctl enable futures-trading
sudo systemctl start futures-trading
```

### 2. **Monitoring**
```bash
# Check service status
sudo systemctl status futures-trading

# View logs
journalctl -u futures-trading -f
```

### 3. **Backup Strategy**
```bash
# Daily backup of volume data
0 2 * * * tar -czf /backup/volume_data_$(date +%Y%m%d).tar.gz volume_data/
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-exchange`
3. Commit changes: `git commit -am 'Add new exchange support'`
4. Push branch: `git push origin feature/new-exchange`
5. Submit pull request

## ⚠️ Disclaimer

This software is for educational and research purposes only. Cryptocurrency futures trading involves significant risk of loss. Always:

- Test thoroughly before live trading
- Use proper risk management
- Start with small position sizes
- Monitor market conditions closely

## 📞 Support

- **Issues**: Create GitHub issue with detailed description
- **Features**: Submit feature request with use case
- **Documentation**: Contribute to README improvements

---

**Built with ❤️ for the crypto futures trading community**
