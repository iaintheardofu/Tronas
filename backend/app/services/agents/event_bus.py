"""
Event bus for inter-agent communication in the PIA Request Automation System.
Implements a publish/subscribe pattern for asynchronous event handling.
"""
from typing import Dict, List, Callable, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import uuid

from loguru import logger


class EventType(str, Enum):
    """Event types for the PIA automation system."""

    # Request lifecycle events
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_CANCELLED = "request_cancelled"

    # Document retrieval events
    DOCUMENT_RETRIEVAL_STARTED = "document_retrieval_started"
    DOCUMENT_RETRIEVAL_PROGRESS = "document_retrieval_progress"
    DOCUMENTS_RETRIEVED = "documents_retrieved"
    DOCUMENT_RETRIEVAL_FAILED = "document_retrieval_failed"

    # Email retrieval events
    EMAIL_RETRIEVAL_STARTED = "email_retrieval_started"
    EMAIL_RETRIEVAL_PROGRESS = "email_retrieval_progress"
    EMAILS_RETRIEVED = "emails_retrieved"
    EMAIL_RETRIEVAL_FAILED = "email_retrieval_failed"

    # Classification events
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_PROGRESS = "classification_progress"
    CLASSIFICATION_COMPLETE = "classification_complete"
    CLASSIFICATION_FAILED = "classification_failed"

    # Deadline events
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_CRITICAL = "deadline_critical"
    DEADLINE_OVERDUE = "deadline_overdue"

    # Workflow events
    WORKFLOW_TASK_STARTED = "workflow_task_started"
    WORKFLOW_TASK_COMPLETED = "workflow_task_completed"
    WORKFLOW_TASK_FAILED = "workflow_task_failed"
    WORKFLOW_COMPLETED = "workflow_completed"

    # Agent lifecycle events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    AGENT_HEARTBEAT = "agent_heartbeat"

    # System events
    ERROR = "error"
    WARNING = "warning"
    NOTIFICATION = "notification"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class Event:
    """Represents an event in the system."""

    event_type: EventType
    data: Dict[str, Any]
    source: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class Subscription:
    """Represents a subscription to events."""

    subscriber_id: str
    event_types: Set[EventType]
    callback: Callable[[Event], Any]
    is_async: bool = True
    filter_func: Optional[Callable[[Event], bool]] = None


class EventBus:
    """
    Central event bus for the PIA automation system.
    Supports async event handling with filtering and multiple subscribers.
    """

    def __init__(self, max_queue_size: int = 10000):
        self._subscriptions: Dict[str, Subscription] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running: bool = False
        self._processor_task: Optional[asyncio.Task] = None
        self._event_history: List[Event] = []
        self._max_history_size: int = 1000
        self._lock: asyncio.Lock = asyncio.Lock()

    def subscribe(
        self,
        subscriber_id: str,
        event_types: List[EventType],
        callback: Callable[[Event], Any],
        is_async: bool = True,
        filter_func: Optional[Callable[[Event], bool]] = None,
    ) -> str:
        """
        Subscribe to events.

        Args:
            subscriber_id: Unique identifier for the subscriber
            event_types: List of event types to subscribe to
            callback: Function to call when event is received
            is_async: Whether the callback is async
            filter_func: Optional filter function for events

        Returns:
            Subscription ID
        """
        subscription = Subscription(
            subscriber_id=subscriber_id,
            event_types=set(event_types),
            callback=callback,
            is_async=is_async,
            filter_func=filter_func,
        )
        self._subscriptions[subscriber_id] = subscription
        logger.debug(f"Subscriber '{subscriber_id}' registered for events: {[e.value for e in event_types]}")
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            subscriber_id: Subscriber ID to remove

        Returns:
            True if subscription was removed
        """
        if subscriber_id in self._subscriptions:
            del self._subscriptions[subscriber_id]
            logger.debug(f"Subscriber '{subscriber_id}' unsubscribed")
            return True
        return False

    async def publish(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """
        Publish an event to the bus.

        Args:
            event_type: Type of event
            data: Event data payload
            source: Source identifier (typically agent name)
            correlation_id: Optional correlation ID for tracking related events
            metadata: Optional additional metadata

        Returns:
            The created event
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        try:
            await self._event_queue.put(event)
            logger.debug(f"Event published: {event_type.value} from {source}")
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event: {event_type.value}")
            raise RuntimeError("Event queue is full")

        return event

    def publish_sync(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """
        Synchronously publish an event (for use in sync contexts).
        Creates event and schedules it for processing.
        """
        event = Event(
            event_type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        try:
            self._event_queue.put_nowait(event)
            logger.debug(f"Event published (sync): {event_type.value} from {source}")
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event: {event_type.value}")
            raise RuntimeError("Event queue is full")

        return event

    async def _process_event(self, event: Event):
        """Process a single event by notifying all matching subscribers."""
        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]

        tasks = []

        for subscription in self._subscriptions.values():
            if event.event_type not in subscription.event_types:
                continue

            if subscription.filter_func and not subscription.filter_func(event):
                continue

            if subscription.is_async:
                task = asyncio.create_task(
                    self._safe_callback(subscription.callback, event, subscription.subscriber_id)
                )
                tasks.append(task)
            else:
                try:
                    subscription.callback(event)
                except Exception as e:
                    logger.error(f"Subscriber '{subscription.subscriber_id}' callback error: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_callback(
        self,
        callback: Callable[[Event], Any],
        event: Event,
        subscriber_id: str,
    ):
        """Safely execute a callback with error handling."""
        try:
            await callback(event)
        except Exception as e:
            logger.error(f"Subscriber '{subscriber_id}' async callback error: {e}")

    async def _event_processor(self):
        """Main event processing loop."""
        logger.info("Event processor started")

        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._process_event(event)
                self._event_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processor error: {e}")

        logger.info("Event processor stopped")

    async def start(self):
        """Start the event bus processor."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._event_processor())
        logger.info("Event bus started")

    async def stop(self, drain: bool = True):
        """
        Stop the event bus processor.

        Args:
            drain: Whether to process remaining events before stopping
        """
        if not self._running:
            return

        if drain:
            while not self._event_queue.empty():
                try:
                    event = self._event_queue.get_nowait()
                    await self._process_event(event)
                    self._event_queue.task_done()
                except asyncio.QueueEmpty:
                    break

        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        Get event history with optional filtering.

        Args:
            event_type: Filter by event type
            source: Filter by source
            correlation_id: Filter by correlation ID
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        events = self._event_history.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]

        return events[-limit:]

    def get_queue_size(self) -> int:
        """Get current event queue size."""
        return self._event_queue.qsize()

    def get_subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self._subscriptions)

    def get_status(self) -> Dict[str, Any]:
        """Get event bus status."""
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "subscriber_count": len(self._subscriptions),
            "history_size": len(self._event_history),
            "subscribers": list(self._subscriptions.keys()),
        }


_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def init_event_bus() -> EventBus:
    """Initialize and start the global event bus."""
    bus = get_event_bus()
    await bus.start()
    return bus


async def shutdown_event_bus():
    """Shutdown the global event bus."""
    global _event_bus
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None
