"""
Order Manager - Handles Order Execution and State Management

This module manages order placement, tracking, and execution on exchanges.
It integrates with the LiveTradingEngine to execute trades and update
the PortfolioManager with order status changes.
"""
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import ccxt

from ..core.config_manager import get_config_manager
from ..core.position_state import SignalType


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT_MARKET = "take_profit_market"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


@dataclass
class OrderRequest:
    """Order request structure."""
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: OrderType
    quantity: float
    price: Optional[float] = None  # Required for limit orders
    stop_price: Optional[float] = None  # For stop orders
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    leverage: int = 1
    reduce_only: bool = False
    close_on_trigger: bool = False
    time_in_force: str = "GTC"  # Good Till Cancelled
    client_order_id: Optional[str] = None
    test: bool = True  # Default to test orders


@dataclass
class OrderResult:
    """Order execution result."""
    success: bool
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'order_id': self.order_id,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'commission': self.commission,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }


class OrderManager:
    """
    Order Manager - Handles Order Execution and State Management
    
    Responsibilities:
    1. Place orders on exchanges (testnet and live)
    2. Track order status and execution
    3. Handle order cancellations and modifications
    4. Provide order callbacks for portfolio updates
    5. Manage order retries and error handling
    6. Support multiple order types (market, limit, stop)
    """
    
    def __init__(self, config_path: Optional[str] = None, testnet: bool = True):
        """
        Initialize Order Manager.
        
        Args:
            config_path: Path to configuration file
            testnet: If True, use testnet for all orders
        """
        self.config_path = config_path
        self.testnet = testnet
        
        # Initialize configuration
        self.config_manager = get_config_manager(config_path)
        self.exchanges_config = self.config_manager.get_all_exchange_configs()
        
        # Initialize exchange connections
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._init_exchanges()
        
        # Order tracking
        self.active_orders: Dict[str, Dict[str, Any]] = {}  # order_id -> order_info
        self.order_history: List[Dict[str, Any]] = []
        
        # Callbacks
        self.order_callbacks: List[Callable[[str, OrderResult], None]] = []
        self.fill_callbacks: List[Callable[[str, OrderResult], None]] = []
        
        # Order monitoring
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        logger.info(f"OrderManager initialized - Testnet: {testnet}")
    
    def _init_exchanges(self):
        """Initialize exchange connections."""
        for exchange_name, config in self.exchanges_config.items():
            if exchange_name == "volume_settings" or exchange_name == "job_settings" or exchange_name == "risk_management" or exchange_name == "data_fetching" or exchange_name == "signal_generation":
                continue
                
            if not config.get('enabled', False):
                continue
            
            try:
                # Initialize exchange
                if exchange_name == 'binance':
                    exchange_class = ccxt.binance
                    options = {
                        'defaultType': 'future',
                        'sandbox': self.testnet,
                        'rateLimit': 1200,
                        'enableRateLimit': True,
                    }
                    
                    # Add API credentials
                    if 'api_key' in config:
                        options['apiKey'] = config['api_key']
                    if 'secret' in config:
                        options['secret'] = config['secret']
                    
                    # Configure testnet URLs if needed
                    if self.testnet:
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
                        options['fetchCurrencies'] = False
                
                exchange = exchange_class(options)
                self.exchanges[exchange_name] = exchange
                logger.info(f"Initialized {exchange_name} exchange (testnet: {self.testnet})")
                
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_name}: {e}")
    
    def add_order_callback(self, callback: Callable[[str, OrderResult], None]):
        """Add callback for order status changes."""
        self.order_callbacks.append(callback)
    
    def add_fill_callback(self, callback: Callable[[str, OrderResult], None]):
        """Add callback for order fills."""
        self.fill_callbacks.append(callback)
    
    def place_order(self, order_request: OrderRequest) -> OrderResult:
        """
        Place an order on the exchange.
        
        Args:
            order_request: Order request details
            
        Returns:
            OrderResult with execution status
        """
        try:
            # Validate order request
            if not self._validate_order_request(order_request):
                return OrderResult(
                    success=False,
                    error_message="Invalid order request"
                )
            
            # Get exchange for symbol
            exchange = self._get_exchange_for_symbol(order_request.symbol)
            if not exchange:
                return OrderResult(
                    success=False,
                    error_message=f"No exchange available for {order_request.symbol}"
                )
            
            # Prepare order parameters
            order_params = self._prepare_order_params(order_request)
            
            # Place order
            if self.testnet or order_request.test:
                # Simulate order placement for testnet
                result = self._simulate_order_placement(order_request, order_params)
            else:
                # Real order placement
                result = self._execute_real_order(exchange, order_request, order_params)
            
            # Track order if successful
            if result.success and result.order_id:
                self._track_order(result.order_id, order_request, result)
            
            # Notify callbacks
            self._notify_order_callbacks(result.order_id or "unknown", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return OrderResult(
                success=False,
                error_message=str(e)
            )
    
    def _validate_order_request(self, order_request: OrderRequest) -> bool:
        """Validate order request parameters."""
        if not order_request.symbol:
            return False
        
        if order_request.side not in ['buy', 'sell']:
            return False
        
        if order_request.quantity <= 0:
            return False
        
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
            if not order_request.price or order_request.price <= 0:
                return False
        
        if order_request.order_type in [OrderType.STOP_MARKET, OrderType.STOP_LIMIT]:
            if not order_request.stop_price or order_request.stop_price <= 0:
                return False
        
        return True
    
    def _get_exchange_for_symbol(self, symbol: str) -> Optional[ccxt.Exchange]:
        """Get the appropriate exchange for a symbol."""
        # For now, use the first available exchange
        # In the future, this could be more sophisticated
        for exchange in self.exchanges.values():
            return exchange
        return None
    
    def _prepare_order_params(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Prepare order parameters for exchange API."""
        params = {
            'symbol': order_request.symbol,
            'side': order_request.side,
            'type': order_request.order_type.value,
            'quantity': order_request.quantity,
            'timeInForce': order_request.time_in_force,
        }
        
        if order_request.price:
            params['price'] = order_request.price
        
        if order_request.stop_price:
            params['stopPrice'] = order_request.stop_price
        
        if order_request.client_order_id:
            params['newClientOrderId'] = order_request.client_order_id
        
        # Futures-specific parameters
        if order_request.leverage > 1:
            params['leverage'] = order_request.leverage
        
        if order_request.reduce_only:
            params['reduceOnly'] = order_request.reduce_only
        
        if order_request.close_on_trigger:
            params['closeOnTrigger'] = order_request.close_on_trigger
        
        return params
    
    def _simulate_order_placement(self, order_request: OrderRequest, order_params: Dict[str, Any]) -> OrderResult:
        """Simulate order placement for testnet."""
        import uuid
        
        order_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Simulate immediate fill for market orders
        if order_request.order_type == OrderType.MARKET:
            status = OrderStatus.FILLED
            filled_quantity = order_request.quantity
            average_price = order_request.price or 100.0  # Default price for simulation
        else:
            status = OrderStatus.OPEN
            filled_quantity = 0.0
            average_price = None
        
        result = OrderResult(
            success=True,
            order_id=order_id,
            status=status,
            filled_quantity=filled_quantity,
            average_price=average_price,
            commission=0.0
        )
        
        logger.info(f"📄 SIMULATED ORDER: {order_request.symbol} {order_request.side} "
                   f"{order_request.quantity} @ {order_request.price or 'MARKET'} "
                   f"(ID: {order_id})")
        
        return result
    
    def _execute_real_order(self, exchange: ccxt.Exchange, order_request: OrderRequest, 
                          order_params: Dict[str, Any]) -> OrderResult:
        """Execute real order on exchange."""
        try:
            # Place order
            response = exchange.create_order(**order_params)
            
            order_id = response.get('id')
            status = OrderStatus(response.get('status', 'pending'))
            filled_quantity = float(response.get('filled', 0))
            average_price = float(response.get('average', 0)) if response.get('average') else None
            commission = float(response.get('commission', 0))
            
            result = OrderResult(
                success=True,
                order_id=order_id,
                status=status,
                filled_quantity=filled_quantity,
                average_price=average_price,
                commission=commission
            )
            
            logger.info(f"✅ REAL ORDER: {order_request.symbol} {order_request.side} "
                       f"{order_request.quantity} @ {order_request.price or 'MARKET'} "
                       f"(ID: {order_id})")
            
            return result
            
        except Exception as e:
            logger.error(f"Real order execution failed: {e}")
            return OrderResult(
                success=False,
                error_message=str(e)
            )
    
    def _track_order(self, order_id: str, order_request: OrderRequest, result: OrderResult):
        """Track order for monitoring."""
        self.active_orders[order_id] = {
            'order_request': order_request,
            'result': result,
            'created_at': datetime.now(),
            'last_updated': datetime.now()
        }
    
    def _notify_order_callbacks(self, order_id: str, result: OrderResult):
        """Notify order callbacks."""
        for callback in self.order_callbacks:
            try:
                callback(order_id, result)
            except Exception as e:
                logger.error(f"Order callback error: {e}")
        
        # Notify fill callbacks if order is filled
        if result.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            for callback in self.fill_callbacks:
                try:
                    callback(order_id, result)
                except Exception as e:
                    logger.error(f"Fill callback error: {e}")
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an active order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Symbol for the order
            
        Returns:
            True if cancellation was successful
        """
        try:
            if order_id in self.active_orders:
                # Simulate cancellation for testnet
                if self.testnet:
                    self.active_orders[order_id]['result'].status = OrderStatus.CANCELLED
                    self.active_orders[order_id]['last_updated'] = datetime.now()
                    logger.info(f"📄 SIMULATED CANCELLATION: Order {order_id}")
                    return True
                else:
                    # Real cancellation
                    exchange = self._get_exchange_for_symbol(symbol)
                    if exchange:
                        response = exchange.cancel_order(order_id, symbol)
                        if response.get('status') == 'canceled':
                            self.active_orders[order_id]['result'].status = OrderStatus.CANCELLED
                            self.active_orders[order_id]['last_updated'] = datetime.now()
                            logger.info(f"✅ CANCELLED ORDER: {order_id}")
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderResult]:
        """Get current status of an order."""
        if order_id in self.active_orders:
            return self.active_orders[order_id]['result']
        return None
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get all active orders."""
        return self.active_orders.copy()
    
    def start_order_monitoring(self):
        """Start background order monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._order_monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Started order monitoring")
    
    def stop_order_monitoring(self):
        """Stop background order monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped order monitoring")
    
    def _order_monitoring_loop(self):
        """Background loop for monitoring order status."""
        import time
        
        while self.is_monitoring:
            try:
                # Update order statuses from exchange
                if not self.testnet:
                    self._update_order_statuses()
                
                # Clean up completed orders
                self._cleanup_completed_orders()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Order monitoring error: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _update_order_statuses(self):
        """Update order statuses from exchange."""
        for order_id, order_info in list(self.active_orders.items()):
            try:
                order_request = order_info['order_request']
                exchange = self._get_exchange_for_symbol(order_request.symbol)
                
                if exchange:
                    # Fetch order status from exchange
                    response = exchange.fetch_order(order_id, order_request.symbol)
                    
                    # Update local status
                    new_status = OrderStatus(response.get('status', 'pending'))
                    filled_quantity = float(response.get('filled', 0))
                    average_price = float(response.get('average', 0)) if response.get('average') else None
                    
                    order_info['result'].status = new_status
                    order_info['result'].filled_quantity = filled_quantity
                    order_info['result'].average_price = average_price
                    order_info['last_updated'] = datetime.now()
                    
                    # Notify callbacks if status changed
                    if new_status != order_info['result'].status:
                        self._notify_order_callbacks(order_id, order_info['result'])
                
            except Exception as e:
                logger.error(f"Error updating order {order_id}: {e}")
    
    def _cleanup_completed_orders(self):
        """Clean up completed orders from active tracking."""
        completed_statuses = [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        
        for order_id, order_info in list(self.active_orders.items()):
            if order_info['result'].status in completed_statuses:
                # Move to history
                self.order_history.append(order_info)
                del self.active_orders[order_id]
    
    def get_order_history(self) -> List[Dict[str, Any]]:
        """Get order history."""
        return self.order_history.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get order manager system status."""
        return {
            'is_monitoring': self.is_monitoring,
            'active_orders_count': len(self.active_orders),
            'order_history_count': len(self.order_history),
            'exchanges_connected': len(self.exchanges),
            'testnet_mode': self.testnet,
            'last_updated': datetime.now().isoformat()
        }
