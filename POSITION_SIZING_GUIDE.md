# Position Sizing & Risk Management System

A comprehensive position sizing and risk management system that filters futures markets based on your budget constraints and liquidation safety requirements.

## 🎯 **Key Features**

### **✅ Intelligent Position Sizing**
- **Budget-Based Filtering**: Only shows symbols you can actually afford to trade
- **Risk-Based Calculation**: Positions sized based on your risk tolerance (e.g., 0.2% per trade)
- **Exchange Limits Compliance**: Respects minimum notional values and position sizes
- **Liquidation Safety**: Ensures sufficient buffer against liquidation

### **✅ Advanced Risk Management**
- **Safety Ratio Calculation**: Liquidation buffer vs stop-loss buffer (minimum 1.5x)
- **Leverage Optimization**: Calculates optimal leverage for your risk profile
- **Maintenance Margin Integration**: Uses real exchange maintenance margin rates
- **Position Size Limits**: Maximum 10% of budget per position

## 🔧 **How It Works**

### **Step 1: Budget Filtering**
```
For each symbol, calculate:
min_feasible_notional = max(exchange_min_notional, min_qty * current_price)

If user_budget < min_feasible_notional → REJECT (can't afford minimum order)
```

### **Step 2: Risk-Based Position Sizing**
```
risk_amount = budget * risk_per_trade_percent
position_size = risk_amount / (entry_price - stop_loss_price)
required_margin = (position_size * entry_price) / leverage
```

### **Step 3: Liquidation Safety Check**
```
liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)
liquidation_buffer = entry_price - liquidation_price
risk_buffer = entry_price - stop_loss_price
safety_ratio = liquidation_buffer / risk_buffer

If safety_ratio < 1.5 → REJECT (liquidation risk too high)
```

## 🚀 **CLI Commands**

### **Analyze Single Symbol**
```bash
# Basic analysis
python3 cli.py position analyze --symbol DOGE/USDT --budget 50

# Custom parameters
python3 cli.py position analyze --symbol BTC/USDT --budget 500 --risk-percent 0.5 --leverage 10

# Higher risk tolerance
python3 cli.py position analyze --symbol ETH/USDT --budget 100 --risk-percent 1.0 --stop-loss-percent 3.0
```

### **Find Tradeable Symbols**
```bash
# Show tradeable symbols for $50 budget
python3 cli.py position tradeable --budget 50

# Higher budget with more symbols
python3 cli.py position tradeable --budget 200 --limit 30

# Conservative risk settings
python3 cli.py position tradeable --budget 100 --risk-percent 0.1
```

### **Enhanced Volume Analysis**
```bash
# Run volume analysis with position sizing
python3 cli.py volume analyze --enhanced --budget 50 --risk-percent 0.2

# Higher budget analysis
python3 cli.py volume analyze --enhanced --budget 500 --risk-percent 0.5
```

## 📊 **Real Examples**

### **Example 1: DOGE/USDT - Tradeable ✅**
```
📊 Position Sizing Analysis for DOGE/USDT
============================================================
Current Price: $0.2112
Stop Loss: $0.2070 (-2.0%)
Budget: $50.00 USDT
Risk per Trade: 0.5%
Leverage: 10x

✅ TRADEABLE
Position Size: 59.185606 DOGE
Position Value: $12.50
Required Margin: $1.25
Risk Amount: $0.25
Liquidation Price: $0.1909
Safety Ratio: 4.80x
```

**Why it's tradeable:**
- Required margin ($1.25) fits within budget ($50)
- Safety ratio (4.80x) exceeds minimum (1.5x)
- Position size meets exchange minimums
- Risk amount ($0.25) is only 0.5% of budget

### **Example 2: BTC/USDT - Not Tradeable ❌**
```
📊 Position Sizing Analysis for BTC/USDT
============================================================
Current Price: $108534.00
Stop Loss: $106363.32 (-2.0%)
Budget: $50.00 USDT
Risk per Trade: 0.2%
Leverage: 5x

❌ NOT TRADEABLE
Reason: Position size (0.000000) < Min Qty (0.000010)
```

**Why it's not tradeable:**
- With 0.2% risk ($0.10), position size is too small
- Doesn't meet exchange minimum quantity requirements
- Need higher budget or risk percentage

## 🎯 **Configuration Options**

### **Risk Management Config**
```python
RiskManagementConfig(
    max_budget=50.0,           # Maximum budget in USDT
    max_risk_per_trade=0.002,  # 0.2% maximum risk per trade
    min_safety_ratio=1.5,      # Minimum liquidation safety ratio
    default_leverage=5,        # Default leverage for calculations
    max_position_percent=0.1   # Maximum 10% of budget per position
)
```

### **Exchange Limits**
```python
ExchangeLimits(
    symbol="DOGE/USDT",
    min_notional=1.0,          # Minimum order value in USDT
    min_qty=1.0,               # Minimum quantity
    max_leverage=75,           # Maximum leverage allowed
    maintenance_margin_rate=0.004  # 0.4% maintenance margin
)
```

## 📈 **Best Practices**

### **For Small Budgets ($50-$200)**
- **Use lower-priced assets**: DOGE, ADA, XRP instead of BTC, ETH
- **Higher risk tolerance**: 0.5-1.0% per trade instead of 0.2%
- **Higher leverage**: 10-20x to reduce margin requirements
- **Focus on safety ratio**: Ensure 2x+ safety ratio

### **For Medium Budgets ($200-$1000)**
- **Mix of assets**: Can trade some higher-priced assets
- **Moderate risk**: 0.2-0.5% per trade
- **Balanced leverage**: 5-10x leverage
- **Diversification**: Multiple positions possible

### **For Large Budgets ($1000+)**
- **Any asset tradeable**: Including BTC, ETH at reasonable risk levels
- **Conservative risk**: 0.1-0.3% per trade
- **Lower leverage**: 3-5x for safety
- **Portfolio approach**: Multiple simultaneous positions

## ⚠️ **Safety Guidelines**

### **Liquidation Protection**
- **Always maintain 1.5x+ safety ratio**
- **Monitor maintenance margin rates**
- **Account for price volatility**
- **Use stop-losses religiously**

### **Risk Management**
- **Never risk more than 2% per trade**
- **Maximum 10% of budget per position**
- **Keep some budget as reserve**
- **Start with paper trading**

### **Position Sizing Rules**
- **Respect exchange minimums**
- **Account for slippage on small positions**
- **Consider funding rates for overnight positions**
- **Monitor margin requirements during high volatility**

## 🔧 **Technical Details**

### **Liquidation Price Formula**
```python
# For LONG positions
liquidation_price = entry_price * (1 - (1/leverage) + maintenance_margin_rate)

# For SHORT positions  
liquidation_price = entry_price * (1 + (1/leverage) - maintenance_margin_rate)
```

### **Position Size Formula**
```python
position_size = risk_amount / (entry_price - stop_loss_price)
required_margin = (position_size * entry_price) / leverage
```

### **Safety Ratio Formula**
```python
liquidation_buffer = abs(entry_price - liquidation_price)
risk_buffer = abs(entry_price - stop_loss_price)
safety_ratio = liquidation_buffer / risk_buffer
```

## 📊 **Performance Metrics**

**Live Test Results:**
- ✅ **Real-time Analysis**: Position sizing calculated in seconds
- ✅ **Exchange Integration**: Fetches live limits from Binance
- ✅ **Safety Validation**: Proper liquidation risk assessment
- ✅ **Budget Compliance**: Accurate affordability filtering

**Example Success Rate:**
- **$50 Budget**: ~5-10 tradeable symbols from top 50
- **$200 Budget**: ~15-25 tradeable symbols from top 50  
- **$500 Budget**: ~30-40 tradeable symbols from top 50

---

## 🚀 **Quick Start**

1. **Analyze Your Budget**:
   ```bash
   python3 cli.py position tradeable --budget 50
   ```

2. **Check Specific Symbol**:
   ```bash
   python3 cli.py position analyze --symbol DOGE/USDT --budget 50
   ```

3. **Run Enhanced Analysis**:
   ```bash
   python3 cli.py volume analyze --enhanced --budget 50
   ```

**Start with small amounts and conservative risk settings until you're comfortable with the system!** 🛡️📈
