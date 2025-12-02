"""
Base autonomous agent class for the PIA Request Automation System.
Provides state machine, retry logic, heartbeat monitoring, and event emission.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import traceback

from loguru import logger

from app.services.agents.event_bus import EventBus, EventType, Event, get_event_bus


class AgentState(str, Enum):
    """Possible states for an agent."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 300.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class AgentMetrics:
    """Metrics tracked by an agent."""

    start_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    last_run: Optional[datetime] = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_items_processed: int = 0
    current_retry_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)


class BaseAgent(ABC):
    """
    Base class for autonomous agents in the PIA automation system.

    Provides:
    - State machine with lifecycle management
    - Retry logic with exponential backoff
    - Heartbeat monitoring
    - Event emission for inter-agent communication
    - Structured logging
    """

    def __init__(
        self,
        agent_name: str,
        event_bus: Optional[EventBus] = None,
        retry_config: Optional[RetryConfig] = None,
        heartbeat_interval: float = 30.0,
        run_interval: float = 60.0,
    ):
        """
        Initialize the base agent.

        Args:
            agent_name: Unique name for this agent
            event_bus: Event bus for inter-agent communication
            retry_config: Configuration for retry behavior
            heartbeat_interval: Seconds between heartbeat emissions
            run_interval: Seconds between agent run cycles
        """
        self.agent_name = agent_name
        self.event_bus = event_bus or get_event_bus()
        self.retry_config = retry_config or RetryConfig()
        self.heartbeat_interval = heartbeat_interval
        self.run_interval = run_interval

        self._state = AgentState.IDLE
        self._state_lock = asyncio.Lock()
        self._metrics = AgentMetrics()
        self._run_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        self._subscribed_events: List[EventType] = []
        self._event_handlers: Dict[EventType, Callable[[Event], Any]] = {}

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if agent is actively running."""
        return self._state == AgentState.RUNNING

    @property
    def metrics(self) -> AgentMetrics:
        """Get agent metrics."""
        return self._metrics

    async def _set_state(self, new_state: AgentState):
        """Set agent state with thread safety."""
        async with self._state_lock:
            old_state = self._state
            self._state = new_state
            logger.info(f"[{self.agent_name}] State transition: {old_state.value} -> {new_state.value}")

            if new_state == AgentState.ERROR:
                await self._emit_event(EventType.AGENT_ERROR, {
                    "previous_state": old_state.value,
                    "error_count": len(self._metrics.errors),
                })

    async def start(self) -> bool:
        """
        Start the agent.

        Returns:
            True if agent started successfully
        """
        if self._state not in [AgentState.IDLE, AgentState.STOPPED, AgentState.ERROR]:
            logger.warning(f"[{self.agent_name}] Cannot start from state: {self._state.value}")
            return False

        try:
            await self._set_state(AgentState.STARTING)
            self._shutdown_event.clear()
            self._pause_event.set()
            self._metrics.start_time = datetime.utcnow()

            await self._on_start()
            await self._subscribe_to_events()

            self._run_task = asyncio.create_task(self._run_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            await self._set_state(AgentState.RUNNING)
            await self._emit_event(EventType.AGENT_STARTED, {
                "start_time": self._metrics.start_time.isoformat(),
            })

            logger.info(f"[{self.agent_name}] Agent started successfully")
            return True

        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to start: {e}")
            await self._set_state(AgentState.ERROR)
            self._add_error("start_failed", str(e))
            return False

    async def stop(self, timeout: float = 30.0) -> bool:
        """
        Stop the agent gracefully.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        Returns:
            True if agent stopped successfully
        """
        if self._state == AgentState.STOPPED:
            return True

        try:
            await self._set_state(AgentState.STOPPING)
            self._shutdown_event.set()
            self._pause_event.set()

            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await asyncio.wait_for(self._heartbeat_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            if self._run_task:
                try:
                    await asyncio.wait_for(self._run_task, timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"[{self.agent_name}] Forcing stop after timeout")
                    self._run_task.cancel()
                    try:
                        await self._run_task
                    except asyncio.CancelledError:
                        pass

            await self._on_stop()
            await self._unsubscribe_from_events()

            await self._set_state(AgentState.STOPPED)
            await self._emit_event(EventType.AGENT_STOPPED, {
                "uptime_seconds": (datetime.utcnow() - self._metrics.start_time).total_seconds()
                if self._metrics.start_time else 0,
                "total_runs": self._metrics.total_runs,
            })

            logger.info(f"[{self.agent_name}] Agent stopped")
            return True

        except Exception as e:
            logger.error(f"[{self.agent_name}] Error during stop: {e}")
            await self._set_state(AgentState.ERROR)
            return False

    async def pause(self):
        """Pause agent execution."""
        if self._state == AgentState.RUNNING:
            self._pause_event.clear()
            await self._set_state(AgentState.PAUSED)
            logger.info(f"[{self.agent_name}] Agent paused")

    async def resume(self):
        """Resume agent execution."""
        if self._state == AgentState.PAUSED:
            self._pause_event.set()
            await self._set_state(AgentState.RUNNING)
            logger.info(f"[{self.agent_name}] Agent resumed")

    async def _run_loop(self):
        """Main agent run loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._pause_event.wait()

                if self._shutdown_event.is_set():
                    break

                self._metrics.last_run = datetime.utcnow()
                self._metrics.total_runs += 1

                try:
                    result = await self._execute_with_retry(self.run)

                    if result:
                        self._metrics.successful_runs += 1
                        self._metrics.current_retry_count = 0
                    else:
                        self._metrics.failed_runs += 1

                except Exception as e:
                    self._metrics.failed_runs += 1
                    self._add_error("run_error", str(e))
                    logger.error(f"[{self.agent_name}] Run error: {e}")

                await self._wait_for_interval()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.agent_name}] Run loop error: {e}")
                await asyncio.sleep(5.0)

    async def _wait_for_interval(self):
        """Wait for the run interval, checking for shutdown."""
        interval_remaining = self.run_interval
        check_interval = 1.0

        while interval_remaining > 0 and not self._shutdown_event.is_set():
            sleep_time = min(check_interval, interval_remaining)
            await asyncio.sleep(sleep_time)
            interval_remaining -= sleep_time

    async def _heartbeat_loop(self):
        """Heartbeat emission loop."""
        while not self._shutdown_event.is_set():
            try:
                self._metrics.last_heartbeat = datetime.utcnow()

                await self._emit_event(EventType.AGENT_HEARTBEAT, {
                    "state": self._state.value,
                    "uptime_seconds": (datetime.utcnow() - self._metrics.start_time).total_seconds()
                    if self._metrics.start_time else 0,
                    "total_runs": self._metrics.total_runs,
                    "items_processed": self._metrics.total_items_processed,
                    "error_count": len(self._metrics.errors),
                })

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.agent_name}] Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic and exponential backoff.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result
        """
        last_exception = None
        delay = self.retry_config.initial_delay

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if attempt > 0:
                    await self._set_state(AgentState.RECOVERING)
                    logger.info(f"[{self.agent_name}] Retry attempt {attempt}/{self.retry_config.max_retries}")

                result = await func(*args, **kwargs)

                if attempt > 0:
                    await self._set_state(AgentState.RUNNING)

                return result

            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_exception = e
                self._metrics.current_retry_count = attempt + 1

                if attempt < self.retry_config.max_retries:
                    if self.retry_config.jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    wait_time = min(delay, self.retry_config.max_delay)
                    logger.warning(
                        f"[{self.agent_name}] Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s"
                    )

                    await asyncio.sleep(wait_time)
                    delay *= self.retry_config.exponential_base
                else:
                    logger.error(f"[{self.agent_name}] All retry attempts exhausted: {e}")
                    await self._set_state(AgentState.ERROR)

        raise last_exception

    async def _emit_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ):
        """
        Emit an event to the event bus.

        Args:
            event_type: Type of event
            data: Event data
            correlation_id: Optional correlation ID
        """
        try:
            await self.event_bus.publish(
                event_type=event_type,
                data=data,
                source=self.agent_name,
                correlation_id=correlation_id,
            )
        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to emit event: {e}")

    async def _subscribe_to_events(self):
        """Subscribe to events this agent is interested in."""
        if self._subscribed_events and self._event_handlers:
            self.event_bus.subscribe(
                subscriber_id=self.agent_name,
                event_types=self._subscribed_events,
                callback=self._handle_event,
                is_async=True,
            )

    async def _unsubscribe_from_events(self):
        """Unsubscribe from all events."""
        self.event_bus.unsubscribe(self.agent_name)

    async def _handle_event(self, event: Event):
        """
        Handle an incoming event.

        Args:
            event: The event to handle
        """
        handler = self._event_handlers.get(event.event_type)
        if handler:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"[{self.agent_name}] Error handling event {event.event_type}: {e}")

    def register_event_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
    ):
        """
        Register a handler for an event type.

        Args:
            event_type: Event type to handle
            handler: Async handler function
        """
        self._subscribed_events.append(event_type)
        self._event_handlers[event_type] = handler

    def _add_error(self, error_type: str, message: str):
        """Add an error to the metrics."""
        self._metrics.errors.append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "traceback": traceback.format_exc(),
        })

        if len(self._metrics.errors) > 100:
            self._metrics.errors = self._metrics.errors[-100:]

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        return {
            "agent_name": self.agent_name,
            "state": self._state.value,
            "metrics": {
                "start_time": self._metrics.start_time.isoformat() if self._metrics.start_time else None,
                "last_heartbeat": self._metrics.last_heartbeat.isoformat() if self._metrics.last_heartbeat else None,
                "last_run": self._metrics.last_run.isoformat() if self._metrics.last_run else None,
                "total_runs": self._metrics.total_runs,
                "successful_runs": self._metrics.successful_runs,
                "failed_runs": self._metrics.failed_runs,
                "items_processed": self._metrics.total_items_processed,
                "current_retry_count": self._metrics.current_retry_count,
                "recent_errors": self._metrics.errors[-5:] if self._metrics.errors else [],
            },
            "config": {
                "run_interval": self.run_interval,
                "heartbeat_interval": self.heartbeat_interval,
                "max_retries": self.retry_config.max_retries,
            },
        }

    @abstractmethod
    async def run(self) -> bool:
        """
        Main execution logic for the agent.
        Must be implemented by subclasses.

        Returns:
            True if run was successful
        """
        pass

    async def _on_start(self):
        """
        Hook called when agent starts.
        Override in subclasses for initialization logic.
        """
        pass

    async def _on_stop(self):
        """
        Hook called when agent stops.
        Override in subclasses for cleanup logic.
        """
        pass
