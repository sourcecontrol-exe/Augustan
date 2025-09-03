"""
Exchange Limits Fetcher - Gets trading limits and market info from exchanges.
"""
import ccxt
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime

from ..core.position_sizing import ExchangeLimits
from ..core.futures_models import ExchangeType


class ExchangeLimitsFetcher:
    """Fetches trading limits and market information from exchanges."""
    
    def __init__(self, exchanges_config: Optional[Dict] = None):
        """Initialize exchange limits fetcher."""
        self.exchanges = {}
        self.exchanges_config = exchanges_config or {}
        self._init_exchanges()
        
        logger.info(f"ExchangeLimitsFetcher initialized with {len(self.exchanges)} exchanges")
    
    def _init_exchanges(self):
        """Initialize exchange connections."""
        exchange_configs = {
            ExchangeType.BINANCE: {
                'class': ccxt.binance,
                'options': {
                    'defaultType': 'future',
                    'sandbox': False,
                    'rateLimit': 1200,
                    'enableRateLimit': True,
                }
            }
        }
        
        for exchange_type in [ExchangeType.BINANCE]:
            try:
                exchange_config = exchange_configs[exchange_type]
                options = exchange_config['options'].copy()
                
                # Add API keys if provided
                if exchange_type.value in self.exchanges_config:
                    user_config = self.exchanges_config[exchange_type.value]
                    if 'api_key' in user_config:
                        options['apiKey'] = user_config['api_key']
                    if 'secret' in user_config:
                        options['secret'] = user_config['secret']
                    # Handle testnet configuration
                    if user_config.get('testnet', False):
                        options['sandbox'] = True
                        options['sandboxMode'] = True
                        if exchange_type == ExchangeType.BINANCE:
                            # Use the test URLs that ccxt provides
                            options['urls'] = {
                                'api': {
                                    'public': 'https://testnet.binance.vision/api/v3',
                                    'private': 'https://testnet.binance.vision/api/v3',
                                    'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                                    'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                                    'fapiPublicV2': 'https://testnet.binancefuture.com/fapi/v2',
                                    'fapiPrivateV2': 'https://testnet.binancefuture.com/fapi/v2',
                                }
                            }
                
                exchange = exchange_config['class'](options)
                self.exchanges[exchange_type] = exchange
                logger.info(f"Initialized {exchange_type.value} exchange")
                
            except Exception as e:
                logger.warning(f"Failed to initialize {exchange_type.value}: {e}")
    
    def fetch_symbol_limits(self, exchange_type: ExchangeType, symbol: str) -> Optional[ExchangeLimits]:
        """Fetch trading limits for a specific symbol."""
        if exchange_type not in self.exchanges:
            logger.error(f"Exchange {exchange_type.value} not available")
            return None
        
        try:
            exchange = self.exchanges[exchange_type]
            markets = exchange.load_markets()
            
            if symbol not in markets:
                logger.warning(f"Symbol {symbol} not found on {exchange_type.value}")
                return None
            
            market = markets[symbol]
            
            # Extract limits from market info
            limits = market.get('limits', {})
            amount_limits = limits.get('amount', {})
            cost_limits = limits.get('cost', {})
            
            # Get precision info
            precision = market.get('precision', {})
            
            # Extract contract info for futures
            contract_size = market.get('contractSize', 1.0)
            
            # Get leverage info (if available)
            max_leverage = market.get('info', {}).get('maxLeverage', 100)
            if isinstance(max_leverage, str):
                try:
                    max_leverage = int(max_leverage)
                except ValueError:
                    max_leverage = 100
            
            # Estimate maintenance margin rate (exchange-specific)
            maintenance_margin_rate = self._get_maintenance_margin_rate(exchange_type, symbol)
            
            exchange_limits = ExchangeLimits(
                symbol=symbol,
                exchange=exchange_type.value,
                min_notional=cost_limits.get('min', 5.0),  # Default 5 USDT minimum
                min_qty=amount_limits.get('min', 0.001),
                max_qty=amount_limits.get('max', 1000000),
                qty_step=precision.get('amount', 0.001),
                price_step=precision.get('price', 0.01),
                max_leverage=max_leverage,
                maintenance_margin_rate=maintenance_margin_rate
            )
            
            logger.debug(f"Fetched limits for {symbol} on {exchange_type.value}")
            return exchange_limits
            
        except Exception as e:
            logger.error(f"Error fetching limits for {symbol} on {exchange_type.value}: {e}")
            return None
    
    def _get_maintenance_margin_rate(self, exchange_type: ExchangeType, symbol: str) -> float:
        """Get maintenance margin rate for a symbol (exchange-specific)."""
        # Default maintenance margin rates by exchange
        default_rates = {
            ExchangeType.BINANCE: 0.004,  # 0.4%
            ExchangeType.BYBIT: 0.005,    # 0.5%
        }
        
        # Try to fetch actual rate from exchange API
        try:
            exchange = self.exchanges[exchange_type]
            
            if exchange_type == ExchangeType.BINANCE:
                # Binance has leverage brackets API
                return self._fetch_binance_maintenance_rate(symbol)
            elif exchange_type == ExchangeType.BYBIT:
                # Bybit has risk limit API
                return self._fetch_bybit_maintenance_rate(symbol)
            
        except Exception as e:
            logger.debug(f"Could not fetch maintenance rate for {symbol}: {e}")
        
        return default_rates.get(exchange_type, 0.005)
    
    def _fetch_binance_maintenance_rate(self, symbol: str) -> float:
        """Fetch maintenance margin rate from Binance API."""
        try:
            exchange = self.exchanges[ExchangeType.BINANCE]
            
            # Use Binance's leverage bracket endpoint
            response = exchange.fapiPublicGetLeverageBracket({'symbol': symbol.replace('/', '')})
            
            if response and len(response) > 0:
                # Get the first bracket (lowest leverage, lowest maintenance rate)
                first_bracket = response[0]['brackets'][0]
                maintenance_rate = float(first_bracket['maintMarginRatio'])
                return maintenance_rate
                
        except Exception as e:
            logger.debug(f"Could not fetch Binance maintenance rate for {symbol}: {e}")
        
        return 0.004  # Default 0.4%
    
    def _fetch_bybit_maintenance_rate(self, symbol: str) -> float:
        """Fetch maintenance margin rate from Bybit API."""
        try:
            exchange = self.exchanges[ExchangeType.BYBIT]
            
            # Bybit risk limit endpoint
            response = exchange.publicGetV5MarketRiskLimit({'category': 'linear', 'symbol': symbol.replace('/', '')})
            
            if response and response.get('result', {}).get('list'):
                # Get the first risk limit level
                first_limit = response['result']['list'][0]
                maintenance_rate = float(first_limit['maintenanceMargin'])
                return maintenance_rate
                
        except Exception as e:
            logger.debug(f"Could not fetch Bybit maintenance rate for {symbol}: {e}")
        
        return 0.005  # Default 0.5%
    
    def fetch_all_symbol_limits(self, symbols: List[str], 
                               preferred_exchange: ExchangeType = ExchangeType.BINANCE) -> Dict[str, ExchangeLimits]:
        """Fetch limits for multiple symbols from the preferred exchange."""
        limits_dict = {}
        
        for symbol in symbols:
            limits = self.fetch_symbol_limits(preferred_exchange, symbol)
            if limits:
                limits_dict[symbol] = limits
            else:
                logger.warning(f"Could not fetch limits for {symbol}")
        
        logger.info(f"Fetched limits for {len(limits_dict)} symbols from {preferred_exchange.value}")
        return limits_dict
    
    def get_current_prices(self, symbols: List[str], 
                          exchange_type: ExchangeType = ExchangeType.BINANCE) -> Dict[str, float]:
        """Get current prices for multiple symbols."""
        if exchange_type not in self.exchanges:
            logger.error(f"Exchange {exchange_type.value} not available")
            return {}
        
        try:
            exchange = self.exchanges[exchange_type]
            tickers = exchange.fetch_tickers(symbols)
            
            prices = {}
            for symbol, ticker in tickers.items():
                if ticker.get('last'):
                    prices[symbol] = float(ticker['last'])
            
            logger.info(f"Fetched prices for {len(prices)} symbols from {exchange_type.value}")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching prices from {exchange_type.value}: {e}")
            return {}
    
    def create_symbol_data_for_position_sizing(self, symbols: List[str], 
                                             exchange_type: ExchangeType = ExchangeType.BINANCE) -> List[Dict]:
        """
        Create symbol data list for position sizing analysis.
        
        Returns list of dicts with keys: symbol, current_price, exchange_limits
        """
        # Fetch current prices
        prices = self.get_current_prices(symbols, exchange_type)
        
        # Fetch exchange limits
        limits_dict = self.fetch_all_symbol_limits(symbols, exchange_type)
        
        symbol_data = []
        for symbol in symbols:
            if symbol in prices and symbol in limits_dict:
                symbol_data.append({
                    'symbol': symbol,
                    'current_price': prices[symbol],
                    'exchange_limits': limits_dict[symbol]
                })
            else:
                logger.warning(f"Missing data for {symbol} - price: {symbol in prices}, limits: {symbol in limits_dict}")
        
        logger.info(f"Created symbol data for {len(symbol_data)} symbols")
        return symbol_data
