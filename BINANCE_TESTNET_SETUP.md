# 🔧 Binance Testnet API Setup Guide

## ✅ **Yes, you can connect with your own API tokens!**

The Augustan system is fully designed to work with your own Binance testnet API tokens. Here's how to set it up:

## 🚀 **Quick Setup**

### **Option 1: Using CLI (Recommended)**
```bash
aug live testnet --setup
```

### **Option 2: Direct Script**
```bash
python3 setup_testnet.py
```

## 📋 **Step-by-Step Process**

### **Step 1: Get Binance Testnet API Keys**

1. **Visit Binance Testnet**: https://testnet.binancefuture.com/
2. **Create Account**: Sign up for a testnet account
3. **Generate API Keys**: 
   - Go to API Management
   - Create new API key
   - **Enable trading permissions**
   - Save your API key and secret
4. **Add Testnet USDT**: Get some testnet USDT (recommended: 1000+ USDT)

### **Step 2: Configure Augustan**

Run the setup script:
```bash
python3 setup_testnet.py
```

The script will:
- ✅ Prompt for your API key and secret
- ✅ Update the configuration file securely
- ✅ Test the connection to Binance testnet
- ✅ Verify your account balance
- ✅ Confirm everything is working

### **Step 3: Test Your Setup**

```bash
# Test the connection
aug live testnet --dry-run

# Test volume analysis
aug volume analyze --enhanced

# Test position sizing
aug position analyze --symbol BTC/USDT --budget 1000
```

## 🔧 **Manual Configuration**

If you prefer to configure manually, edit `config/exchanges_config.json`:

```json
{
  "binance": {
    "api_key": "YOUR_API_KEY_HERE",
    "secret": "YOUR_SECRET_KEY_HERE",
    "enabled": true,
    "testnet": true
  }
}
```

## 🧪 **Testing Your Connection**

### **Test 1: Basic Connection**
```bash
aug live testnet --dry-run
```

**Expected Output:**
```
✅ API connection successful!
💰 USDT Balance: 1000.00
✅ Sufficient balance for testing
```

### **Test 2: Volume Analysis**
```bash
aug volume analyze --enhanced
```

**Expected Output:**
```
📊 Enhanced volume analysis completed
📈 Top markets by volume:
1. BTC/USDT: $1,234,567,890
2. ETH/USDT: $987,654,321
...
```

### **Test 3: Position Sizing**
```bash
aug position analyze --symbol BTC/USDT --budget 1000
```

**Expected Output:**
```
📊 Position analysis for BTC/USDT
💰 Budget: $1000.00
📈 Position size: 0.001 BTC
⚠️ Risk: $20.00 (2.0%)
```

## 🔒 **Security Best Practices**

### **API Key Security**
- ✅ **Never share your API keys publicly**
- ✅ **Use testnet only for testing**
- ✅ **Enable IP restrictions if available**
- ✅ **Monitor API usage regularly**
- ✅ **Rotate keys periodically**

### **Configuration Security**
- ✅ **Keep config files secure**
- ✅ **Don't commit API keys to git**
- ✅ **Use environment variables for production**
- ✅ **Backup your configuration**

## 🚨 **Common Issues & Solutions**

### **Issue 1: "Invalid Api-Key ID"**
```
❌ Error fetching prices from binance: binance {"code":-2008,"msg":"Invalid Api-Key ID."}
```

**Solutions:**
1. Check your API key is correct
2. Ensure you're using testnet keys (not mainnet)
3. Verify the key has trading permissions
4. Check if the key is active

### **Issue 2: "Low Balance Warning"**
```
⚠️ Low testnet balance: 50 USDT
```

**Solutions:**
1. Add more testnet USDT from Binance testnet
2. Minimum recommended: 100 USDT
3. Visit: https://testnet.binancefuture.com/

### **Issue 3: "Connection Timeout"**
```
❌ Connection timeout
```

**Solutions:**
1. Check your internet connection
2. Verify Binance testnet is accessible
3. Try again in a few minutes
4. Check firewall settings

### **Issue 4: "Rate Limit Exceeded"**
```
❌ Rate limit exceeded
```

**Solutions:**
1. Wait a few minutes
2. Reduce test frequency
3. Check API usage limits
4. Implement rate limiting

## 📊 **Testnet vs Mainnet**

| Feature | Testnet | Mainnet |
|---------|---------|---------|
| **Money** | Fake USDT | Real money |
| **Risk** | None | High |
| **API Limits** | Higher | Lower |
| **Testing** | Perfect for testing | Production only |
| **Cost** | Free | Real trading fees |

## 🎯 **What You Can Test**

### **Volume Analysis**
- ✅ Fetch real market data
- ✅ Analyze volume patterns
- ✅ Rank markets by volume
- ✅ Enhanced analysis with position sizing

### **Position Sizing**
- ✅ Calculate position sizes with real prices
- ✅ Apply risk management rules
- ✅ Test with different budgets
- ✅ Validate exchange limits

### **Live Trading (Paper Mode)**
- ✅ Connect to real exchange APIs
- ✅ Process real-time data
- ✅ Generate trading signals
- ✅ Simulate order execution

### **Risk Management**
- ✅ Test risk calculations
- ✅ Validate position limits
- ✅ Test portfolio management
- ✅ Verify safety checks

## 🚀 **Next Steps After Setup**

1. **Run Comprehensive Tests**:
   ```bash
   aug live testnet --dry-run
   ```

2. **Test Volume Analysis**:
   ```bash
   aug volume analyze --enhanced
   ```

3. **Test Position Sizing**:
   ```bash
   aug position analyze --symbol BTC/USDT --budget 1000
   ```

4. **Start Paper Trading**:
   ```bash
   aug live start --paper
   ```

5. **Monitor Performance**:
   ```bash
   aug dashboard
   ```

## 🎉 **Success Indicators**

You'll know your setup is working when:

- ✅ `aug live testnet --dry-run` passes all tests
- ✅ `aug volume analyze --enhanced` returns real data
- ✅ `aug position analyze` calculates positions correctly
- ✅ No "Invalid Api-Key ID" errors
- ✅ Account balance shows correctly

## 📞 **Support**

If you encounter issues:

1. **Check the error messages** - they often contain specific solutions
2. **Verify your API keys** - ensure they're correct and have proper permissions
3. **Test with Binance directly** - verify your keys work on Binance testnet
4. **Check the logs** - look for detailed error information
5. **Review this guide** - ensure you followed all steps correctly

---

**🎯 Ready to get started? Run: `aug live testnet --setup`**
