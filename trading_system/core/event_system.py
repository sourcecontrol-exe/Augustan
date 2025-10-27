
"""
Event-Driven Architecture for Scalping Trading System
Provides event emission and handling for real-time trading decisions.

⚠️ DEPRECATED: This module uses a global singleton and has issues with error handling.
Use trading_system.core.event_system_refactored.EventBus instead.

This module will be removed in a future version.
"""
import warnings
import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import threading
from collections import defaultdict

from .models import MarketData

# Show deprecation warning
warnings.warn(
    "event_system.EventBus and event_bus are deprecated. "
    "Use trading_system.core.event_system_refactored.EventBus instead.",
    DeprecationWarning,
    stacklevel=2
)


class EventType(Enum):
    """Event types for the trading system."""
    CANDLE_TICK = "CANDLE_TICK"           # New tick data
    CANDLE_CLOSED = "CANDLE_CLOSED"       # Candle completed
    SIGNAL_GENERATED = "SIGNAL_GENERATED" # New trading signal
    ORDER_PLACED = "ORDER_PLACED"         # Order executed
    ORDER_FILLED = "ORDER_FILLED"         # Order completed
    POSITION_OPENED = "POSITION_OPENED"   # New position
    POSITION_CLOSED = "POSITION_CLOSED"   # Position closed
    STOP_LOSS_HIT = "STOP_LOSS_HIT"       # Stop loss triggered
    TAKE_PROFIT_HIT = "TAKE_PROFIT_HIT"   # Take profit triggered
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"  # Risk threshold breached


@dataclass
class TradingEvent:
    """Base trading event."""
    event_type: EventType
    timestamp: datetime
    symbol: str
    data: Dict[str, Any]
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __post_init__(self):
        if not hasattr(self, 'timestamp') or self.timestamp is None:
            self.timestamp = datetime.now()


class CandleClosedEvent(TradingEvent):
    """Event emitted when a candle is completed."""
    
    def __init__(self, symbol: str, candle_data: MarketData, timeframe: str):
        super().__init__(
            event_type=EventType.CANDLE_CLOSED,
            timestamp=datetime.now(),
            symbol=symbol,
            data={'candle': candle_data.to_dict(), 'timeframe': timeframe},
            priority=1  # High priority for scalping
        )
        self.candle_data = candle_data
        self.timeframe = timeframe


class SignalGeneratedEvent(TradingEvent):
    """Event emitted when a new trading signal is generated."""
    
    def __init__(self, symbol: str, signal_data: Dict[str, Any], strategy_name: str, confidence: float):
        super().__init__(
            event_type=EventType.SIGNAL_GENERATED,
            timestamp=datetime.now(),
            symbol=symbol,
            data={'signal': signal_data, 'strategy': strategy_name, 'confidence': confidence},
            priority=1  # High priority for scalping
        )
        self.signal_data = signal_data
        self.strategy_name = strategy_name
        self.confidence = confidence


class OrderFilledEvent(TradingEvent):
    """Event emitted when an order is filled."""
    
    def __init__(self, symbol: str, order_id: str, side: str, quantity: float, price: float, commission: float):
        super().__init__(
            event_type=EventType.ORDER_FILLED,
            timestamp=datetime.now(),
            symbol=symbol,
            data={
                'order_id': order_id,
                'side': side,
                'quantity': quantity,
                'price': price,
                'commission': commission
            },
            priority=1  # High priority
        )
        self.order_id = order_id
        self.side = side
        self.quantity = quantity
        self.price = price
        self.commission = commission


class EventBus:
    """
    Event bus for managing event-driven architecture.
    
    Features:
    - Async event handling
    - Priority-based processing
    - Event filtering by symbol/type
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize event bus."""
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._symbol_handlers: Dict[str, Dict[EventType, List[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._lock = threading.Lock()
        
        logger.info("EventBus initialized for event-driven trading")
    
    def subscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """
        Subscribe to events.
        
        Args:
            event_type: Type of event to listen for
            handler: Function to call when event occurs
            symbol: Optional symbol filter (None for all symbols)
        """
        with self._lock:
            if symbol:
                self._symbol_handlers[symbol][event_type].append(handler)
                logger.debug(f"Subscribed handler for {symbol} {event_type.value}")
            else:
                self._handlers[event_type].append(handler)
                logger.debug(f"Subscribed global handler for {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """Unsubscribe from events."""
        with self._lock:
            if symbol and symbol in self._symbol_handlers:
                if event_type in self._symbol_handlers[symbol]:
                    try:
                        self._symbol_handlers[symbol][event_type].remove(handler)
                        logger.debug(f"Unsubscribed handler for {symbol} {event_type.value}")
                    except ValueError:
                        pass
            else:
                try:
                    self._handlers[event_type].remove(handler)
                    logger.debug(f"Unsubscribed global handler for {event_type.value}")
                except ValueError:
                    pass
    
    async def emit(self, event: TradingEvent):
        """
        Emit an event asynchronously.
        
        Args:
            event: Event to emit
        """
        await self._event_queue.put(event)
        logger.debug(f"Emitted {event.event_type.value} for {event.symbol}")
    
    def emit_sync(self, event: TradingEvent):
        """
        Emit an event synchronously.
        
        Args:
            event: Event to emit
        """
        asyncio.create_task(self._event_queue.put(event))
        logger.debug(f"Emitted sync {event.event_type.value} for {event.symbol}")
    
    async def start(self):
        """Start the event processing loop."""
        self._running = True
        logger.info("EventBus started - processing events")
        
        while self._running:
            try:
                # Get event with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _process_event(self, event: TradingEvent):
        """Process a single event."""
        try:
            # Process global handlers
            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in global handler for {event.event_type.value}: {e}")
            
            # Process symbol-specific handlers
            symbol_handlers = self._symbol_handlers.get(event.symbol, {}).get(event.event_type, [])
            for handler in symbol_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in symbol handler for {event.symbol} {event.event_type.value}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing event {event.event_type.value}: {e}")
    
    def stop(self):
        """Stop the event processing loop."""
        self._running = False
        logger.info("EventBus stopped")
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._event_queue.qsize()
    
    def get_subscription_count(self) -> Dict[str, int]:
        """Get count of subscriptions by event type."""
        counts = {}
        for event_type, handlers in self._handlers.items():
            counts[f"global_{event_type.value}"] = len(handlers)
        
        for symbol, symbol_events in self._symbol_handlers.items():
            for event_type, handlers in symbol_events.items():
                key = f"{symbol}_{event_type.value}"
                counts[key] = len(handlers)
        
        return counts


# Global event bus instance
event_bus = EventBus()


class EventHandler:
    """
    Base class for event handlers.
    Provides common functionality for handling trading events.
    """
    
    def __init__(self, event_bus: EventBus = None):
        """Initialize event handler."""
        self.event_bus = event_bus or globals()['event_bus']
        self._subscriptions: List[tuple] = []
    
    def subscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """Subscribe to events and track subscription."""
        self.event_bus.subscribe(event_type, handler, symbol)
        self._subscriptions.append((event_type, handler, symbol))
    
    def cleanup(self):
        """Unsubscribe from all events."""
        for event_type, handler, symbol in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler, symbol)
        self._subscriptions.clear()
    
    async def handle_candle_closed(self, event: CandleClosedEvent):
        """Handle candle closed events - override in subclasses."""
        pass
    
    async def handle_signal_generated(self, event: SignalGeneratedEvent):
        """Handle signal generated events - override in subclasses."""
        pass
    
    async def handle_order_filled(self, event: OrderFilledEvent):
        """Handle order filled events - override in subclasses."""
        pass
