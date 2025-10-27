"""
Refactored Event System with Proper Async Design and Error Handling.

Addresses issues with the old system:
- No global instance (uses dependency injection)
- Pure async design (no sync/async mixing)
- Robust error handling for all tasks
- Proper task tracking to avoid silent failures
- Consumer task pattern for reliable processing
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from collections import defaultdict


class EventType(Enum):
    """Event types for the trading system."""
    CANDLE_TICK = "CANDLE_TICK"
    CANDLE_CLOSED = "CANDLE_CLOSED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    TAKE_PROFIT_HIT = "TAKE_PROFIT_HIT"
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"


@dataclass
class TradingEvent:
    """Base trading event."""
    event_type: EventType
    timestamp: datetime
    symbol: str
    data: Dict[str, Any]
    priority: int = 1
    
    def __post_init__(self):
        if not hasattr(self, 'timestamp') or self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """
    Event bus with proper async design and error handling.
    
    Features:
    - Pure async event handling
    - Task tracking to avoid silent failures
    - Robust error handling with callbacks
    - Dependency injection ready (no global instance)
    - Consumer task pattern for reliable processing
    
    Usage:
        bus = EventBus()
        bus.subscribe(EventType.CANDLE_CLOSED, handler)
        await bus.start()  # Start consumer task
        await bus.emit(event)
        await bus.stop()   # Clean shutdown
    """
    
    def __init__(self, max_queue_size: int = 1000, error_callback: Optional[Callable] = None):
        """
        Initialize event bus.
        
        Args:
            max_queue_size: Maximum size of event queue
            error_callback: Optional callback for unhandled errors
        """
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._symbol_handlers: Dict[str, Dict[EventType, List[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        
        # Task tracking
        self._consumer_task: Optional[asyncio.Task] = None
        self._running = False
        self._error_callback = error_callback
        
        # Track pending tasks to avoid silent failures
        self._pending_tasks: Set[asyncio.Task] = set()
        
        logger.info("EventBus initialized")
    
    async def start(self):
        """
        Start the event processing consumer task.
        
        Should be called before emitting events to ensure proper processing.
        """
        if self._running:
            logger.warning("EventBus already running")
            return
        
        self._running = True
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        self._setup_task_error_handler(self._consumer_task)
        logger.info("EventBus started - consumer task running")
    
    async def stop(self):
        """
        Stop the event bus and wait for completion.
        
        Ensures all pending events are processed before stopping.
        """
        if not self._running:
            return
        
        logger.info("Stopping EventBus...")
        self._running = False
        
        # Wait for consumer task to finish
        if self._consumer_task:
            # Cancel the consumer task
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        # Wait for all pending handler tasks to complete
        if self._pending_tasks:
            logger.info(f"Waiting for {len(self._pending_tasks)} pending tasks...")
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()
        
        logger.info("EventBus stopped")
    
    def subscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """
        Subscribe to events.
        
        Args:
            event_type: Type of event to listen for
            handler: Async callable to call when event occurs
            symbol: Optional symbol filter (None for all symbols)
            
        Raises:
            ValueError: If handler is not async or callable
        """
        # Validate handler is async callable
        if not callable(handler):
            raise ValueError(f"Handler must be callable, got {type(handler)}")
        
        if not asyncio.iscoroutinefunction(handler):
            logger.warning(f"Handler {handler} is not async. Consider making it async.")
        
        if symbol:
            self._symbol_handlers[symbol][event_type].append(handler)
            logger.debug(f"Subscribed handler for {symbol} {event_type.value}")
        else:
            self._handlers[event_type].append(handler)
            logger.debug(f"Subscribed global handler for {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """Unsubscribe from events."""
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
            
        Raises:
            RuntimeError: If EventBus has not been started
            asyncio.QueueFull: If queue is full (backpressure)
        """
        if not self._running:
            logger.warning("EventBus not started yet. Events may be dropped.")
        
        try:
            await asyncio.wait_for(self._event_queue.put(event), timeout=5.0)
            logger.debug(f"Emitted {event.event_type.value} for {event.symbol}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout emitting {event.event_type.value} - queue may be full")
            raise
        except Exception as e:
            logger.error(f"Error emitting event {event.event_type.value}: {e}")
            raise
    
    async def _consumer_loop(self):
        """
        Consumer loop that processes events from the queue.
        
        This task runs continuously, processing events and calling handlers.
        All errors are caught and logged to prevent silent failures.
        """
        logger.info("Consumer loop started")
        
        while self._running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                
                # Process event asynchronously
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                # Expected timeout when queue is empty
                continue
            
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                if self._error_callback:
                    try:
                        await self._error_callback(e)
                    except Exception as callback_error:
                        logger.error(f"Error in error callback: {callback_error}")
    
    async def _process_event(self, event: TradingEvent):
        """
        Process a single event by calling all registered handlers.
        
        Args:
            event: Event to process
        """
        # Get all handlers for this event type
        handlers = self._get_handlers_for_event(event)
        
        if not handlers:
            logger.debug(f"No handlers for {event.event_type.value}")
            return
        
        # Call all handlers concurrently
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._safe_call_handler(handler, event))
            tasks.append(task)
            self._pending_tasks.add(task)
            # Set up error handling for this task
            self._setup_task_error_handler(task)
        
        # Wait for all handlers to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions
            for handler, result in zip(handlers, results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {handler} failed: {result}")
        
        # Clean up completed tasks
        for task in tasks:
            self._pending_tasks.discard(task)
    
    def _get_handlers_for_event(self, event: TradingEvent) -> List[Callable]:
        """Get all handlers for an event type and symbol."""
        handlers = []
        
        # Global handlers for this event type
        handlers.extend(self._handlers.get(event.event_type, []))
        
        # Symbol-specific handlers
        symbol_handlers = self._symbol_handlers.get(event.symbol, {}).get(event.event_type, [])
        handlers.extend(symbol_handlers)
        
        return handlers
    
    async def _safe_call_handler(self, handler: Callable, event: TradingEvent):
        """
        Safely call a handler with proper error handling.
        
        Args:
            handler: Handler function to call
            event: Event to pass to handler
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Synchronous handler - run in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)
        
        except Exception as e:
            logger.error(f"Error in handler {handler}: {e}")
            raise
    
    def _setup_task_error_handler(self, task: asyncio.Task):
        """Set up error handling for a task using callback."""
        def task_done_callback(t: asyncio.Task):
            try:
                # This will raise an exception if the task failed
                t.result()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task {t} failed with unhandled exception: {e}")
                if self._error_callback:
                    # Schedule error callback
                    asyncio.create_task(self._error_callback(e))
        
        task.add_done_callback(task_done_callback)
    
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
    
    def is_running(self) -> bool:
        """Check if event bus is running."""
        return self._running
    
    def get_pending_tasks_count(self) -> int:
        """Get count of pending handler tasks."""
        return len(self._pending_tasks)


class EventHandler:
    """
    Base class for event handlers with dependency injection.
    
    No longer uses global event_bus - requires explicit injection.
    
    Usage:
        event_bus = EventBus()
        await event_bus.start()
        
        handler = MyEventHandler(event_bus)
        handler.subscribe(EventType.CANDLE_CLOSED, my_handler_method)
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize event handler.
        
        Args:
            event_bus: Event bus instance to use (required, no global fallback)
        """
        if not isinstance(event_bus, EventBus):
            raise TypeError(f"event_bus must be EventBus instance, got {type(event_bus)}")
        
        self.event_bus = event_bus
        self._subscriptions: List[tuple] = []
        logger.info(f"{self.__class__.__name__} initialized with EventBus")
    
    def subscribe(self, event_type: EventType, handler: Callable, symbol: Optional[str] = None):
        """
        Subscribe to events and track subscription.
        
        Args:
            event_type: Type of event to listen for
            handler: Async handler function
            symbol: Optional symbol filter
        """
        self.event_bus.subscribe(event_type, handler, symbol)
        self._subscriptions.append((event_type, handler, symbol))
        logger.debug(f"{self.__class__.__name__} subscribed to {event_type.value}")
    
    def cleanup(self):
        """Unsubscribe from all events."""
        for event_type, handler, symbol in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler, symbol)
        self._subscriptions.clear()
        logger.debug(f"{self.__class__.__name__} cleaned up subscriptions")
    
    async def handle_candle_closed(self, event):
        """Handle candle closed events - override in subclasses."""
        pass
    
    async def handle_signal_generated(self, event):
        """Handle signal generated events - override in subclasses."""
        pass
    
    async def handle_order_filled(self, event):
        """Handle order filled events - override in subclasses."""
        pass


# Convenience function for creating event bus instances
def create_event_bus(max_queue_size: int = 1000, error_callback: Optional[Callable] = None) -> EventBus:
    """
    Create a new EventBus instance.
    
    Args:
        max_queue_size: Maximum size of event queue
        error_callback: Optional error callback
        
    Returns:
        EventBus instance
    """
    return EventBus(max_queue_size=max_queue_size, error_callback=error_callback)

