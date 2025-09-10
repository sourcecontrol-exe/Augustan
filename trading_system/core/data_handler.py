"""
DataHandler - Processes and manages market data from multiple sources.

This module provides centralized data processing, validation, normalization,
and distribution of market data throughout the trading system.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import pandas as pd
from loguru import logger

from .models import MarketData, TradingSignal, MarketFeatures
from .orderbook import OrderBook
from .exchange_manager import ExchangeManager, ExchangeConfig


@dataclass
class DataConfig:
    """Configuration for data handling."""
    max_history_size: int = 10000
    data_validation: bool = True
    normalize_prices: bool = True
    cache_duration: int = 60  # seconds
    batch_size: int = 100
    enable_compression: bool = False


@dataclass
class DataQualityMetrics:
    """Data quality metrics."""
    symbol: str
    total_updates: int = 0
    valid_updates: int = 0
    invalid_updates: int = 0
    missing_data_count: int = 0
    duplicate_count: int = 0
    out_of_sequence_count: int = 0
    last_update: Optional[datetime] = None
    data_freshness: Optional[float] = None  # seconds since last update


class DataHandler:
    """
    Centralized data processing and management system.
    
    Features:
    - Data validation and normalization
    - Historical data storage and retrieval
    - Real-time data distribution
    - Data quality monitoring
    - Cross-exchange data aggregation
    - Performance metrics calculation
    """
    
    def __init__(self, exchange_manager: ExchangeManager, config: Optional[DataConfig] = None):
        """
        Initialize data handler.
        
        Args:
            exchange_manager: Exchange manager instance
            config: Data handling configuration
        """
        self.exchange_manager = exchange_manager
        self.config = config or DataConfig()
        
        # Data storage
        self.market_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.max_history_size))
        self.orderbooks: Dict[str, Dict[str, OrderBook]] = defaultdict(dict)
        self.tickers: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Data quality tracking
        self.quality_metrics: Dict[str, DataQualityMetrics] = defaultdict(
            lambda: DataQualityMetrics("")
        )
        
        # Data processing pipelines
        self.data_processors: List[Callable[[str, Dict], Dict]] = []
        self.data_validators: List[Callable[[str, Dict], bool]] = []
        
        # Callbacks for data distribution
        self.market_data_callbacks: List[Callable[[str, MarketData], None]] = []
        self.orderbook_callbacks: List[Callable[[str, str, OrderBook], None]] = []
        self.ticker_callbacks: List[Callable[[str, str, Dict], None]] = []
        
        # Performance tracking
        self.processing_times: Dict[str, List[float]] = defaultdict(list)
        self.data_rates: Dict[str, List[float]] = defaultdict(list)
        
        # Cache for processed data
        self.data_cache: Dict[str, Tuple[Any, datetime]] = {}
        
        logger.info("DataHandler initialized")
    
    def add_data_processor(self, processor: Callable[[str, Dict], Dict]):
        """Add data processing function."""
        self.data_processors.append(processor)
    
    def add_data_validator(self, validator: Callable[[str, Dict], bool]):
        """Add data validation function."""
        self.data_validators.append(validator)
    
    def add_market_data_callback(self, callback: Callable[[str, MarketData], None]):
        """Add market data callback."""
        self.market_data_callbacks.append(callback)
    
    def add_orderbook_callback(self, callback: Callable[[str, str, OrderBook], None]):
        """Add orderbook callback."""
        self.orderbook_callbacks.append(callback)
    
    def add_ticker_callback(self, callback: Callable[[str, str, Dict], None]):
        """Add ticker callback."""
        self.ticker_callbacks.append(callback)
    
    async def process_market_data(self, exchange_name: str, symbol: str, 
                                data: Dict) -> Optional[MarketData]:
        """
        Process raw market data into standardized format.
        
        Args:
            exchange_name: Source exchange
            symbol: Trading symbol
            data: Raw market data
            
        Returns:
            Processed MarketData or None if invalid
        """
        start_time = datetime.now()
        
        try:
            # Validate data
            if not self._validate_data(symbol, data):
                self._update_quality_metrics(symbol, False)
                return None
            
            # Process data through pipeline
            processed_data = self._process_data_pipeline(symbol, data)
            
            # Create MarketData object
            market_data = self._create_market_data(exchange_name, symbol, processed_data)
            if not market_data:
                self._update_quality_metrics(symbol, False)
                return None
            
            # Store historical data
            self.market_data[symbol].append(market_data)
            
            # Update quality metrics
            self._update_quality_metrics(symbol, True)
            
            # Notify callbacks
            self._notify_market_data_callbacks(symbol, market_data)
            
            # Update performance metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_metrics(symbol, processing_time)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
            self._update_quality_metrics(symbol, False)
            return None
    
    async def process_orderbook_data(self, exchange_name: str, symbol: str, 
                                   data: Dict) -> Optional[OrderBook]:
        """
        Process orderbook data.
        
        Args:
            exchange_name: Source exchange
            symbol: Trading symbol
            data: Raw orderbook data
            
        Returns:
            Updated OrderBook or None if invalid
        """
        try:
            # Validate orderbook data
            if not self._validate_orderbook_data(data):
                return None
            
            # Get or create orderbook
            if symbol not in self.orderbooks[exchange_name]:
                self.orderbooks[exchange_name][symbol] = OrderBook(symbol)
            
            orderbook = self.orderbooks[exchange_name][symbol]
            
            # Update orderbook
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            sequence = data.get('sequence', None)
            
            success = orderbook.update(bids, asks, sequence)
            if not success:
                logger.warning(f"Failed to update orderbook for {exchange_name}:{symbol}")
                return None
            
            # Notify callbacks
            self._notify_orderbook_callbacks(exchange_name, symbol, orderbook)
            
            return orderbook
            
        except Exception as e:
            logger.error(f"Error processing orderbook data for {symbol}: {e}")
            return None
    
    async def process_ticker_data(self, exchange_name: str, symbol: str, 
                                data: Dict) -> Optional[Dict]:
        """
        Process ticker data.
        
        Args:
            exchange_name: Source exchange
            symbol: Trading symbol
            data: Raw ticker data
            
        Returns:
            Processed ticker data or None if invalid
        """
        try:
            # Validate ticker data
            if not self._validate_ticker_data(data):
                return None
            
            # Process and normalize data
            processed_data = self._normalize_ticker_data(data)
            
            # Store ticker data
            self.tickers[exchange_name][symbol] = processed_data
            
            # Notify callbacks
            self._notify_ticker_callbacks(exchange_name, symbol, processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing ticker data for {symbol}: {e}")
            return None
    
    def _validate_data(self, symbol: str, data: Dict) -> bool:
        """Validate market data."""
        try:
            # Check required fields
            required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing required field '{field}' in data for {symbol}")
                    return False
            
            # Validate data types and ranges
            if not isinstance(data['timestamp'], (int, float, datetime)):
                logger.warning(f"Invalid timestamp type for {symbol}")
                return False
            
            for field in ['open', 'high', 'low', 'close', 'volume']:
                if not isinstance(data[field], (int, float)) or data[field] < 0:
                    logger.warning(f"Invalid {field} value for {symbol}: {data[field]}")
                    return False
            
            # Validate OHLC relationships
            if not (data['low'] <= data['open'] <= data['high'] and 
                   data['low'] <= data['close'] <= data['high']):
                logger.warning(f"Invalid OHLC relationships for {symbol}")
                return False
            
            # Run custom validators
            for validator in self.data_validators:
                if not validator(symbol, data):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data validation error for {symbol}: {e}")
            return False
    
    def _validate_orderbook_data(self, data: Dict) -> bool:
        """Validate orderbook data."""
        try:
            if 'bids' not in data or 'asks' not in data:
                return False
            
            # Validate bids
            for bid in data['bids']:
                if len(bid) != 2 or not isinstance(bid[0], (int, float)) or not isinstance(bid[1], (int, float)):
                    return False
                if bid[0] <= 0 or bid[1] < 0:
                    return False
            
            # Validate asks
            for ask in data['asks']:
                if len(ask) != 2 or not isinstance(ask[0], (int, float)) or not isinstance(ask[1], (int, float)):
                    return False
                if ask[0] <= 0 or ask[1] < 0:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Orderbook validation error: {e}")
            return False
    
    def _validate_ticker_data(self, data: Dict) -> bool:
        """Validate ticker data."""
        try:
            required_fields = ['last', 'bid', 'ask', 'volume']
            for field in required_fields:
                if field not in data:
                    return False
                if not isinstance(data[field], (int, float)) or data[field] < 0:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ticker validation error: {e}")
            return False
    
    def _process_data_pipeline(self, symbol: str, data: Dict) -> Dict:
        """Process data through the processing pipeline."""
        processed_data = data.copy()
        
        for processor in self.data_processors:
            try:
                processed_data = processor(symbol, processed_data)
            except Exception as e:
                logger.error(f"Data processor error for {symbol}: {e}")
                break
        
        return processed_data
    
    def _create_market_data(self, exchange_name: str, symbol: str, data: Dict) -> Optional[MarketData]:
        """Create MarketData object from processed data."""
        try:
            # Handle timestamp conversion
            timestamp = data['timestamp']
            if isinstance(timestamp, (int, float)):
                if timestamp > 1e10:  # Milliseconds
                    timestamp = datetime.fromtimestamp(timestamp / 1000)
                else:  # Seconds
                    timestamp = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            return MarketData(
                symbol=symbol,
                timestamp=timestamp,
                open=float(data['open']),
                high=float(data['high']),
                low=float(data['low']),
                close=float(data['close']),
                volume=float(data['volume'])
            )
            
        except Exception as e:
            logger.error(f"Error creating MarketData for {symbol}: {e}")
            return None
    
    def _normalize_ticker_data(self, data: Dict) -> Dict:
        """Normalize ticker data to standard format."""
        normalized = {}
        
        # Map common field names
        field_mapping = {
            'last': 'last',
            'close': 'last',
            'price': 'last',
            'bid': 'bid',
            'ask': 'ask',
            'volume': 'volume',
            'baseVolume': 'volume',
            'quoteVolume': 'quote_volume'
        }
        
        for source_field, target_field in field_mapping.items():
            if source_field in data:
                normalized[target_field] = float(data[source_field])
        
        # Add metadata
        normalized['timestamp'] = datetime.now()
        normalized['exchange'] = data.get('exchange', 'unknown')
        
        return normalized
    
    def _update_quality_metrics(self, symbol: str, is_valid: bool):
        """Update data quality metrics."""
        metrics = self.quality_metrics[symbol]
        metrics.symbol = symbol
        metrics.total_updates += 1
        
        if is_valid:
            metrics.valid_updates += 1
        else:
            metrics.invalid_updates += 1
        
        metrics.last_update = datetime.now()
        
        # Calculate data freshness
        if metrics.last_update:
            metrics.data_freshness = (datetime.now() - metrics.last_update).total_seconds()
    
    def _update_performance_metrics(self, symbol: str, processing_time: float):
        """Update performance metrics."""
        self.processing_times[symbol].append(processing_time)
        
        # Keep only recent measurements
        if len(self.processing_times[symbol]) > 100:
            self.processing_times[symbol] = self.processing_times[symbol][-100:]
    
    def _notify_market_data_callbacks(self, symbol: str, market_data: MarketData):
        """Notify market data callbacks."""
        for callback in self.market_data_callbacks:
            try:
                callback(symbol, market_data)
            except Exception as e:
                logger.error(f"Market data callback error: {e}")
    
    def _notify_orderbook_callbacks(self, exchange_name: str, symbol: str, orderbook: OrderBook):
        """Notify orderbook callbacks."""
        for callback in self.orderbook_callbacks:
            try:
                callback(exchange_name, symbol, orderbook)
            except Exception as e:
                logger.error(f"Orderbook callback error: {e}")
    
    def _notify_ticker_callbacks(self, exchange_name: str, symbol: str, ticker_data: Dict):
        """Notify ticker callbacks."""
        for callback in self.ticker_callbacks:
            try:
                callback(exchange_name, symbol, ticker_data)
            except Exception as e:
                logger.error(f"Ticker callback error: {e}")
    
    def get_market_data(self, symbol: str, limit: Optional[int] = None) -> List[MarketData]:
        """Get historical market data for a symbol."""
        data = list(self.market_data[symbol])
        if limit:
            return data[-limit:]
        return data
    
    def get_latest_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get the latest market data for a symbol."""
        data = self.market_data[symbol]
        return data[-1] if data else None
    
    def get_orderbook(self, exchange_name: str, symbol: str) -> Optional[OrderBook]:
        """Get orderbook for exchange and symbol."""
        return self.orderbooks[exchange_name].get(symbol)
    
    def get_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Get ticker data for exchange and symbol."""
        return self.tickers[exchange_name].get(symbol)
    
    def get_data_quality_metrics(self, symbol: str) -> Optional[DataQualityMetrics]:
        """Get data quality metrics for a symbol."""
        return self.quality_metrics.get(symbol)
    
    def get_all_data_quality_metrics(self) -> Dict[str, DataQualityMetrics]:
        """Get data quality metrics for all symbols."""
        return dict(self.quality_metrics)
    
    def calculate_performance_metrics(self, symbol: str) -> Dict[str, float]:
        """Calculate performance metrics for a symbol."""
        processing_times = self.processing_times[symbol]
        
        if not processing_times:
            return {}
        
        return {
            'avg_processing_time': sum(processing_times) / len(processing_times),
            'max_processing_time': max(processing_times),
            'min_processing_time': min(processing_times),
            'total_updates': len(processing_times)
        }
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of all data."""
        summary = {
            'symbols_with_data': len(self.market_data),
            'total_data_points': sum(len(data) for data in self.market_data.values()),
            'orderbooks': {
                exchange: len(orderbooks) 
                for exchange, orderbooks in self.orderbooks.items()
            },
            'tickers': {
                exchange: len(tickers) 
                for exchange, tickers in self.tickers.items()
            },
            'quality_metrics': {
                symbol: {
                    'total_updates': metrics.total_updates,
                    'valid_updates': metrics.valid_updates,
                    'invalid_updates': metrics.invalid_updates,
                    'data_freshness': metrics.data_freshness
                }
                for symbol, metrics in self.quality_metrics.items()
            }
        }
        
        return summary
    
    def clear_cache(self):
        """Clear data cache."""
        self.data_cache.clear()
        logger.info("Data cache cleared")
    
    def clear_historical_data(self, symbol: Optional[str] = None):
        """Clear historical data."""
        if symbol:
            if symbol in self.market_data:
                self.market_data[symbol].clear()
                logger.info(f"Cleared historical data for {symbol}")
        else:
            for symbol_data in self.market_data.values():
                symbol_data.clear()
            logger.info("Cleared all historical data")
    
    def export_data(self, symbol: str, format: str = 'json') -> Optional[str]:
        """Export data for a symbol."""
        try:
            data = self.get_market_data(symbol)
            
            if format.lower() == 'json':
                return json.dumps([md.to_dict() for md in data], indent=2)
            elif format.lower() == 'csv':
                df = pd.DataFrame([md.to_dict() for md in data])
                return df.to_csv(index=False)
            else:
                logger.error(f"Unsupported export format: {format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting data for {symbol}: {e}")
            return None
