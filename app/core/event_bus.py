"""
Event bus for strategy signals and system events
"""
import asyncio
from typing import Dict, List, Callable, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from app.utils.logger import log


class EventType(Enum):
    """Event types"""
    # Trading signals
    SIGNAL_BUY = "signal_buy"
    SIGNAL_SELL = "signal_sell"
    SIGNAL_CLOSE = "signal_close"
    
    # Order events
    ORDER_CREATED = "order_created"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_FAILED = "order_failed"
    
    # Position events
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"
    
    # Strategy events
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    STRATEGY_ERROR = "strategy_error"
    
    # System events
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    MARKET_DATA_UPDATED = "market_data_updated"
    RISK_LIMIT_HIT = "risk_limit_hit"


@dataclass
class Event:
    """Event data structure"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = None
    source: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class EventBus:
    """Event bus for pub/sub pattern"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.processor_task: asyncio.Task = None
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
        log.debug(f"Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                log.debug(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass
    
    async def publish(self, event: Event):
        """Publish an event to the bus"""
        await self.event_queue.put(event)
        log.debug(f"Published event: {event.event_type.value}")
    
    async def emit(self, event_type: EventType, data: Dict[str, Any], source: str = ""):
        """Convenience method to emit an event"""
        event = Event(event_type=event_type, data=data, source=source)
        await self.publish(event)
    
    async def _process_events(self):
        """Process events from the queue"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Call all subscribers for this event type
                if event.event_type in self.subscribers:
                    callbacks = self.subscribers[event.event_type]
                    
                    # Execute callbacks
                    for callback in callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(event)
                            else:
                                callback(event)
                        except Exception as e:
                            log.error(f"Error in event callback: {e}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.error(f"Error processing event: {e}")
    
    async def start(self):
        """Start the event processor"""
        if not self.running:
            self.running = True
            self.processor_task = asyncio.create_task(self._process_events())
            log.info("Event bus started")
    
    async def stop(self):
        """Stop the event processor"""
        if self.running:
            self.running = False
            if self.processor_task:
                await self.processor_task
            log.info("Event bus stopped")
    
    def get_queue_size(self) -> int:
        """Get current event queue size"""
        return self.event_queue.qsize()


# Global event bus instance
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

