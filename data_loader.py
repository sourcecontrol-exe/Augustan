#!/usr/bin/env python3
"""
Historical Data Loader for Augustan Backtesting
Provides unified interface for loading data from multiple sources
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from data_service import DataService
    DATA_SERVICE_AVAILABLE = True
except ImportError:
    DATA_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

class DataLoader:
    """Unified data loader for backtesting"""
    
    def __init__(self):
        self.data_service = None
        
    def load_data(self, symbol: str, source: str = 'yfinance', **kwargs) -> pd.DataFrame:
        """
        Load historical data from specified source
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USD' for yfinance, 'BTC/USDT' for exchanges)
            source: Data source ('yfinance', 'binance', 'pi42', 'csv')
            **kwargs: Additional parameters for data loading
            
        Returns:
            DataFrame with OHLCV data
        """
        if source == 'yfinance':
            return self._load_yfinance(symbol, **kwargs)
        elif source in ['binance', 'ccxt']:
            return self._load_exchange_data(symbol, 'ccxt', **kwargs)
        elif source == 'pi42':
            return self._load_exchange_data(symbol, 'pi42', **kwargs)
        elif source == 'csv':
            return self._load_csv(symbol, **kwargs)
        else:
            raise ValueError(f"Unsupported data source: {source}")
    
    def _load_yfinance(self, symbol: str, period: str = '2y', 
                      interval: str = '1d', **kwargs) -> pd.DataFrame:
        """Load data from Yahoo Finance"""
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance not available. Install with: pip install yfinance")
        
        logger.info(f"Loading {symbol} from Yahoo Finance ({period}, {interval})")
        
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # Standardize column names
        data = self._standardize_columns(data)
        logger.info(f"Loaded {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        
        return data
    
    def _load_exchange_data(self, symbol: str, exchange: str, 
                           timeframe: str = '1h', limit: int = 1000, **kwargs) -> pd.DataFrame:
        """Load data from exchange via DataService"""
        if not DATA_SERVICE_AVAILABLE:
            raise ImportError("DataService not available")
        
        logger.info(f"Loading {symbol} from {exchange} ({timeframe}, {limit} bars)")
        
        # Initialize data service if not already done
        if not self.data_service or self.data_service.exchange_name != exchange:
            config = kwargs.get('config', {
                'exchange_id': 'binance' if exchange == 'ccxt' else exchange,
                'testnet': True
            })
            self.data_service = DataService(exchange, config)
        
        # Get OHLCV data
        data = self.data_service.get_ohlcv(symbol, timeframe, limit)
        
        if data.empty:
            raise ValueError(f"No data found for {symbol} on {exchange}")
        
        # Standardize columns and ensure proper datetime index
        data = self._standardize_columns(data)
        
        # Convert timestamp to datetime index if needed
        if 'timestamp' in data.columns:
            data.index = pd.to_datetime(data['timestamp'])
            data = data.drop('timestamp', axis=1)
        
        logger.info(f"Loaded {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        
        return data
    
    def _load_csv(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load data from CSV file"""
        logger.info(f"Loading data from CSV: {filepath}")
        
        # Load CSV with flexible parsing
        data = pd.read_csv(filepath, index_col=0, parse_dates=True)
        
        if data.empty:
            raise ValueError(f"No data found in {filepath}")
        
        # Standardize columns
        data = self._standardize_columns(data)
        
        logger.info(f"Loaded {len(data)} bars from CSV")
        return data
    
    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names for backtesting.py compatibility"""
        # Column mapping (case insensitive)
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low', 
            'close': 'Close',
            'volume': 'Volume',
            'adj close': 'Close',  # Use adjusted close if available
            'dividends': None,     # Remove dividends column
            'stock splits': None   # Remove stock splits column
        }
        
        # Create new dataframe with standardized columns
        standardized_data = pd.DataFrame(index=data.index)
        
        for old_col in data.columns:
            new_col = column_mapping.get(old_col.lower())
            if new_col:
                standardized_data[new_col] = data[old_col]
        
        # Ensure we have required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in standardized_data.columns]
        
        if missing_cols:
            # Try to fill missing Volume with zeros if it's the only missing column
            if missing_cols == ['Volume']:
                standardized_data['Volume'] = 0
                logger.warning("Volume data not available, using zeros")
            else:
                raise ValueError(f"Missing required columns: {missing_cols}")
        
        return standardized_data[required_cols]
    
    def get_sample_data(self, symbol: str = 'BTC-USD', bars: int = 1000) -> pd.DataFrame:
        """Get sample data for testing (defaults to BTC from Yahoo Finance)"""
        try:
            # Try yfinance first
            return self._load_yfinance(symbol, period='2y', interval='1d')
        except:
            try:
                # Fallback to exchange data
                exchange_symbol = symbol.replace('-', '/').replace('USD', 'USDT')
                return self._load_exchange_data(exchange_symbol, 'ccxt', limit=bars)
            except:
                # Generate synthetic data as last resort
                logger.warning("Using synthetic data - install yfinance or configure exchange access")
                return self._generate_synthetic_data(bars)
    
    def _generate_synthetic_data(self, bars: int = 1000) -> pd.DataFrame:
        """Generate synthetic OHLCV data for testing"""
        dates = pd.date_range(end=datetime.now(), periods=bars, freq='1H')
        
        # Generate realistic price movement
        np.random.seed(42)
        price_changes = np.random.normal(0, 0.02, bars)  # 2% volatility
        prices = 50000 * np.exp(np.cumsum(price_changes))  # Start at $50k
        
        # Create OHLCV data
        data = pd.DataFrame(index=dates)
        data['Open'] = prices
        data['Close'] = prices * (1 + np.random.normal(0, 0.005, bars))
        data['High'] = np.maximum(data['Open'], data['Close']) * (1 + np.abs(np.random.normal(0, 0.01, bars)))
        data['Low'] = np.minimum(data['Open'], data['Close']) * (1 - np.abs(np.random.normal(0, 0.01, bars)))
        data['Volume'] = np.random.randint(1000, 10000, bars)
        
        return data

# Convenience functions
def load_crypto_data(symbol: str, period: str = '1y', interval: str = '1d') -> pd.DataFrame:
    """Quick function to load crypto data"""
    loader = DataLoader()
    return loader.load_data(symbol, source='yfinance', period=period, interval=interval)

def load_exchange_data(symbol: str, exchange: str = 'binance', 
                      timeframe: str = '1h', limit: int = 1000) -> pd.DataFrame:
    """Quick function to load exchange data"""
    loader = DataLoader()
    return loader.load_data(symbol, source=exchange, timeframe=timeframe, limit=limit)

def get_sample_btc_data(bars: int = 1000) -> pd.DataFrame:
    """Get sample BTC data for testing"""
    loader = DataLoader()
    return loader.get_sample_data('BTC-USD', bars)

if __name__ == '__main__':
    # Example usage
    loader = DataLoader()
    
    # Load BTC data from Yahoo Finance
    btc_data = loader.load_data('BTC-USD', source='yfinance', period='1y', interval='1d')
    print(f"BTC data shape: {btc_data.shape}")
    print(btc_data.head())
    
    # Load from exchange (if configured)
    try:
        eth_data = loader.load_data('ETH/USDT', source='binance', timeframe='4h', limit=500)
        print(f"ETH data shape: {eth_data.shape}")
    except Exception as e:
        print(f"Exchange data not available: {e}")
