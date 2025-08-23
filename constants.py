# Trading Timeframes
TIMEFRAMES = {
    '1m': '1m',
    '3m': '3m', 
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '2h': '2h',
    '4h': '4h',
    '6h': '6h',
    '8h': '8h',
    '12h': '12h',
    '1d': '1d',
    '3d': '3d',
    '1w': '1w',
    '1M': '1M'
}

# Default timeframe
DEFAULT_TIMEFRAME = '3m'

# Stake Currencies
STAKE_CURRENCIES = {
    'USD': 'USD',
    'USDT': 'USDT',
    'USDC': 'USDC',
    'INR': 'INR',
    'EUR': 'EUR',
    'GBP': 'GBP',
    'BTC': 'BTC',
    'ETH': 'ETH'
}

# Default stake currency
DEFAULT_STAKE_CURRENCY = 'USDT'

# Exchange Types
EXCHANGE_TYPES = {
    'SPOT': 'spot',
    'FUTURES': 'future',
    'MARGIN': 'margin'
}

# Default exchange type
DEFAULT_EXCHANGE_TYPE = 'future'

# Risk Management Constants
RISK_LEVELS = {
    'CONSERVATIVE': 0.005,  # 0.5%
    'MODERATE': 0.01,       # 1%
    'AGGRESSIVE': 0.02      # 2%
}

# Default risk per trade
DEFAULT_RISK_PER_TRADE = 0.01  # 1%

# Risk-Reward Ratios
RISK_REWARD_RATIOS = {
    'MINIMAL': 1.5,
    'STANDARD': 2.0,
    'AGGRESSIVE': 3.0,
    'VERY_AGGRESSIVE': 5.0
}

# Default risk-reward ratio
DEFAULT_RISK_REWARD_RATIO = 2.0

# Scanner Constants
SCANNER_BASE_CURRENCIES = {
    'USDT': 'USDT',
    'USD': 'USD',
    'BTC': 'BTC',
    'ETH': 'ETH',
    'INR': 'INR'
}

# Default scanner base currency
DEFAULT_SCANNER_BASE_CURRENCY = 'USDT'

# Scanner market limits
SCANNER_MARKET_LIMITS = {
    'SMALL': 50,
    'MEDIUM': 150,
    'LARGE': 300,
    'VERY_LARGE': 500
}

# Default scanner market limit
DEFAULT_SCANNER_MARKET_LIMIT = 150

# Scanner volatility thresholds
SCANNER_VOLATILITY_THRESHOLDS = {
    'LOW': 2.0,      # 2%
    'MEDIUM': 5.0,   # 5%
    'HIGH': 10.0,    # 10%
    'VERY_HIGH': 20.0 # 20%
}

# Default scanner volatility threshold
DEFAULT_SCANNER_MIN_24H_CHANGE = 5.0

# Capital Tiers
CAPITAL_TIERS = {
    'SMALL': 1000,      # $1,000
    'MEDIUM': 5000,     # $5,000
    'LARGE': 25000,     # $25,000
    'VERY_LARGE': 100000 # $100,000
}

# Default total capital
DEFAULT_TOTAL_CAPITAL = 1000

# Trading Session Times (in hours, UTC)
TRADING_SESSIONS = {
    'ASIA': {'start': 0, 'end': 8},      # 00:00 - 08:00 UTC
    'EUROPE': {'start': 6, 'end': 16},   # 06:00 - 16:00 UTC
    'AMERICA': {'start': 13, 'end': 23}, # 13:00 - 23:00 UTC
    'OVERLAP': {'start': 6, 'end': 16}   # 06:00 - 16:00 UTC (EU-AS overlap)
}

# Order Types
ORDER_TYPES = {
    'MARKET': 'market',
    'LIMIT': 'limit',
    'STOP_LOSS': 'stop_loss',
    'TAKE_PROFIT': 'take_profit',
    'STOP_LIMIT': 'stop_limit'
}

# Position Sides
POSITION_SIDES = {
    'LONG': 'long',
    'SHORT': 'short'
}

# Exchange Names
EXCHANGE_NAMES = {
    'BINANCE': 'binance',
    'BYBIT': 'bybit',
    'OKX': 'okx',
    'KUCOIN': 'kucoin',
    'GATE': 'gate'
}
