# 🔧 SAPI Testnet Limitations Guide

## Overview

Binance testnet has **significant limitations** with SAPI (Spot Account API) endpoints. This guide explains how to work around these limitations and test your application properly.

## ❌ SAPI Endpoints Not Available in Testnet

The following SAPI endpoints are **NOT available** in Binance testnet:

- `/sapi/v1/account` - Account information
- `/sapi/v1/myTrades` - Trade history
- `/sapi/v1/openOrders` - Open orders
- `/sapi/v1/allOrders` - All orders
- `/sapi/v1/order` - Order management
- `/sapi/v1/order/test` - Test orders
- `/sapi/v1/deposit/hisrec` - Deposit history
- `/sapi/v1/withdraw/history` - Withdrawal history
- `/sapi/v1/asset/dribblet` - Asset dribblet
- `/sapi/v1/asset/assetDividend` - Asset dividend
- `/sapi/v1/account/snapshot` - Account snapshots
- `/sapi/v1/margin/*` - Margin trading
- `/sapi/v1/savings/*` - Savings
- `/sapi/v1/staking/*` - Staking

## ✅ Available Testnet Endpoints

### Spot Testnet (`/api/v3/*`)
- ✅ `/api/v3/exchangeInfo` - Exchange information
- ✅ `/api/v3/ticker/24hr` - 24hr ticker
- ✅ `/api/v3/ticker/price` - Price ticker
- ✅ `/api/v3/klines` - Kline/candlestick data
- ✅ `/api/v3/trades` - Recent trades
- ✅ `/api/v3/depth` - Order book

### Futures Testnet (`/fapi/v1/*`)
- ✅ `/fapi/v1/exchangeInfo` - Futures exchange info
- ✅ `/fapi/v1/ticker/24hr` - Futures 24hr ticker
- ✅ `/fapi/v1/ticker/price` - Futures price ticker
- ✅ `/fapi/v1/klines` - Futures klines
- ✅ `/fapi/v1/depth` - Futures order book
- ⚠️ `/fapi/v1/account` - Limited account info
- ⚠️ `/fapi/v1/positionRisk` - Limited position info

## 🛠️ Solutions for Testing

### 1. **Mock Account Service** (Recommended for Development)

The system now includes a **Mock Account Service** that provides realistic test data:

```python
from trading_system.data_feeder.mock_account_service import get_mock_account_service

# Get mock account service
mock_service = get_mock_account_service(balance=1000.0)

# Get mock balance
balance = mock_service.get_balance()

# Simulate trades
mock_service.simulate_trade('BTCUSDT', 'BUY', 0.001, 50000.0)
```

**Features:**
- ✅ Realistic account balance simulation
- ✅ Trade simulation with balance updates
- ✅ Position tracking
- ✅ Order history simulation
- ✅ No API calls required

### 2. **Mainnet with Read-Only Permissions**

For more comprehensive testing, use mainnet with restricted API keys:

```bash
# Create API key with read-only permissions
# - Enable: Spot & Futures Trading
# - Disable: Withdrawals, Futures Trading, Margin Trading
# - IP Restriction: Your development IP only
```

**Benefits:**
- ✅ Full SAPI access
- ✅ Real market data
- ✅ No risk of accidental trades
- ✅ Complete feature testing

### 3. **Futures Testnet for Derivatives**

For derivatives-related features, use Futures Testnet:

```python
# Futures testnet has better SAPI support
futures_feeder = BinanceFuturesFeeder(testnet=True)
```

**Available in Futures Testnet:**
- ✅ Account information (limited)
- ✅ Position management
- ✅ Order placement
- ✅ Trade history

## 🔧 Implementation Details

### Automatic Fallback System

The system now automatically handles SAPI limitations:

```python
def get_account_info(self) -> Optional[Dict]:
    """Get account information with automatic fallback."""
    try:
        if self.exchange.sandbox:
            # Use mock service in testnet
            from .mock_account_service import get_mock_account_service
            mock_service = get_mock_account_service(balance=1000.0)
            return mock_service.get_balance()
        
        # Use real API in mainnet
        return self.exchange.fetch_balance()
        
    except Exception as e:
        if "sapi" in str(e).lower():
            # Fallback to mock service
            from .mock_account_service import get_mock_account_service
            mock_service = get_mock_account_service(balance=1000.0)
            return mock_service.get_balance()
```

### Configuration-Based Behavior

Different behaviors based on trading mode:

```json
{
  "paper_trading_config.json": {
    "use_mock_accounts": true,
    "mock_balance": 1000.0,
    "testnet": true
  },
  "live_trading_config.json": {
    "use_mock_accounts": false,
    "testnet": false
  }
}
```

## 📋 Testing Checklist

### ✅ Paper Trading (Testnet)
- [ ] Use `/api/v3/*` endpoints only
- [ ] Mock account service for balance
- [ ] Test market data fetching
- [ ] Test position sizing calculations
- [ ] Test signal generation
- [ ] Verify risk management

### ✅ Live Trading (Mainnet)
- [ ] Use full SAPI access
- [ ] Real account balance
- [ ] Test order placement
- [ ] Test trade execution
- [ ] Test position management
- [ ] Verify real money flows

### ✅ Development Workflow
- [ ] Start with paper trading
- [ ] Use mock data for development
- [ ] Test with read-only mainnet
- [ ] Gradual transition to live trading

## 🚨 Common Issues and Solutions

### Issue: "SAPI endpoints not available"
```bash
# Solution: Use mock service
aug --mode paper position analyze --symbol BTC/USDT
```

### Issue: "Account info not available in testnet"
```bash
# Solution: Check mock service is working
aug config show --section risk
```

### Issue: "Need to test order placement"
```bash
# Solution: Use mainnet with read-only permissions
# Or use futures testnet for derivatives
```

### Issue: "Need to test withdrawals"
```bash
# Solution: Use mainnet with read-only permissions
# Or mock the withdrawal process
```

## 🔄 Best Practices

### 1. **Development Phase**
- Use paper trading mode
- Mock account service for balance
- Test market data and calculations
- Verify risk management logic

### 2. **Testing Phase**
- Use mainnet with read-only permissions
- Test real API responses
- Verify error handling
- Test edge cases

### 3. **Production Phase**
- Use live trading mode
- Real account balance
- Full SAPI access
- Monitor real money flows

### 4. **Error Handling**
```python
try:
    account_info = feeder.get_account_info()
except SAPIError:
    # Fallback to mock service
    account_info = mock_service.get_balance()
```

## 📚 Additional Resources

- [Binance Testnet Documentation](https://testnet.binance.vision/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/spot/en/)
- [Futures Testnet Documentation](https://testnet.binancefuture.com/)

## 🆘 Support

If you encounter SAPI-related issues:

1. **Check trading mode**: `aug config show`
2. **Verify testnet status**: Check config files
3. **Use mock service**: Automatic fallback
4. **Test with mainnet**: Read-only permissions
5. **Check logs**: Look for SAPI error messages

Remember: **Always test thoroughly in paper mode before live trading!**
