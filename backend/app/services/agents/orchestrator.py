"""
Master Orchestrator for the PIA Request Automation System.
Manages all agent lifecycles and provides system-wide coordination.
"""
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
from enum import Enum
import asyncio
import signal

from loguru import logger

from app.services.agents.base_agent import BaseAgent, AgentState
from app.services.agents.event_bus import (
    EventBus, EventType, Event,
    get_event_bus, init_event_bus, shutdown_event_bus,
)
from app.services.agents.request_monitor_agent import RequestMonitorAgent
from app.services.agents.document_retrieval_agent import DocumentRetrievalAgent
from app.services.agents.email_retrieval_agent import EmailRetrievalAgent
from app.services.agents.classification_agent import ClassificationAgent
from app.services.agents.deadline_monitor_agent import DeadlineMonitorAgent


class OrchestratorState(str, Enum):
    """Possible states for the orchestrator."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentOrchestrator:
    """
    Master orchestrator for the PIA Request Automation System.

    Responsibilities:
    - Manages lifecycle of all agents
    - Handles inter-agent communication via event bus
    - Provides system-wide status monitoring
    - Implements graceful shutdown handling
    - Monitors agent health and restarts failed agents
    """

    def __init__(
        self,
        auto_restart_agents: bool = True,
        health_check_interval: float = 60.0,
        max_restart_attempts: int = 3,
    ):
        """
        Initialize the Agent Orchestrator.

        Args:
            auto_restart_agents: Whether to automatically restart failed agents
            health_check_interval: Seconds between health checks
            max_restart_attempts: Maximum restart attempts per agent
        """
        self.auto_restart_agents = auto_restart_agents
        self.health_check_interval = health_check_interval
        self.max_restart_attempts = max_restart_attempts

        self._state = OrchestratorState.STOPPED
        self._event_bus: Optional[EventBus] = None
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_restart_counts: Dict[str, int] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._start_time: Optional[datetime] = None

        self._registered_handlers: List[str] = []

    @property
    def state(self) -> OrchestratorState:
        """Get current orchestrator state."""
        return self._state

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents.copy()

    async def initialize(self) -> bool:
        """
        Initialize the orchestrator and create all agents.

        Returns:
            True if initialization successful
        """
        if self._state != OrchestratorState.STOPPED:
            logger.warning("Orchestrator already initialized")
            return False

        try:
            self._state = OrchestratorState.INITIALIZING
            logger.info("Initializing PIA Request Automation Orchestrator")

            self._event_bus = await init_event_bus()

            await self._register_event_handlers()

            await self._create_agents()

            logger.info(f"Orchestrator initialized with {len(self._agents)} agents")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            self._state = OrchestratorState.ERROR
            return False

    async def _create_agents(self):
        """Create all system agents."""
        self._agents = {
            "request_monitor": RequestMonitorAgent(
                event_bus=self._event_bus,
                poll_interval=30.0,
            ),
            "document_retrieval": DocumentRetrievalAgent(
                event_bus=self._event_bus,
                max_concurrent_downloads=5,
            ),
            "email_retrieval": EmailRetrievalAgent(
                event_bus=self._event_bus,
                max_concurrent_mailboxes=3,
            ),
            "classification": ClassificationAgent(
                event_bus=self._event_bus,
                batch_size=10,
                rate_limit_per_minute=30,
            ),
            "deadline_monitor": DeadlineMonitorAgent(
                event_bus=self._event_bus,
                check_interval_hours=4.0,
            ),
        }

        for agent_name in self._agents:
            self._agent_restart_counts[agent_name] = 0

    async def _register_event_handlers(self):
        """Register orchestrator-level event handlers."""
        self._event_bus.subscribe(
            subscriber_id="orchestrator_error_handler",
            event_types=[EventType.ERROR, EventType.AGENT_ERROR],
            callback=self._handle_error_event,
        )
        self._registered_handlers.append("orchestrator_error_handler")

        self._event_bus.subscribe(
            subscriber_id="orchestrator_agent_monitor",
            event_types=[EventType.AGENT_HEARTBEAT],
            callback=self._handle_heartbeat_event,
        )
        self._registered_handlers.append("orchestrator_agent_monitor")

        self._event_bus.subscribe(
            subscriber_id="orchestrator_workflow_tracker",
            event_types=[
                EventType.REQUEST_CREATED,
                EventType.WORKFLOW_COMPLETED,
                EventType.CLASSIFICATION_COMPLETE,
            ],
            callback=self._handle_workflow_event,
        )
        self._registered_handlers.append("orchestrator_workflow_tracker")

    async def start(self) -> bool:
        """
        Start all agents and begin orchestration.

        Returns:
            True if all agents started successfully
        """
        if self._state == OrchestratorState.RUNNING:
            logger.warning("Orchestrator already running")
            return True

        if self._state == OrchestratorState.STOPPED:
            if not await self.initialize():
                return False

        try:
            logger.info("Starting all agents")
            self._shutdown_event.clear()
            self._start_time = datetime.utcnow()

            start_tasks = []
            for agent_name, agent in self._agents.items():
                logger.info(f"Starting agent: {agent_name}")
                task = asyncio.create_task(agent.start())
                start_tasks.append((agent_name, task))

            results = await asyncio.gather(
                *[task for _, task in start_tasks],
                return_exceptions=True
            )

            all_started = True
            for (agent_name, _), result in zip(start_tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to start agent {agent_name}: {result}")
                    all_started = False
                elif not result:
                    logger.error(f"Agent {agent_name} failed to start")
                    all_started = False

            if all_started:
                self._state = OrchestratorState.RUNNING
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                logger.info("All agents started successfully")
                return True
            else:
                logger.error("Some agents failed to start")
                await self.stop()
                return False

        except Exception as e:
            logger.error(f"Failed to start orchestrator: {e}")
            self._state = OrchestratorState.ERROR
            return False

    async def stop(self, timeout: float = 60.0) -> bool:
        """
        Stop all agents gracefully.

        Args:
            timeout: Maximum seconds to wait for shutdown

        Returns:
            True if all agents stopped successfully
        """
        if self._state == OrchestratorState.STOPPED:
            return True

        try:
            self._state = OrchestratorState.STOPPING
            self._shutdown_event.set()

            logger.info("Stopping all agents")

            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await asyncio.wait_for(self._health_check_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            stop_tasks = []
            for agent_name, agent in self._agents.items():
                logger.info(f"Stopping agent: {agent_name}")
                task = asyncio.create_task(agent.stop(timeout=timeout/len(self._agents)))
                stop_tasks.append((agent_name, task))

            results = await asyncio.gather(
                *[task for _, task in stop_tasks],
                return_exceptions=True
            )

            all_stopped = True
            for (agent_name, _), result in zip(stop_tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Error stopping agent {agent_name}: {result}")
                    all_stopped = False
                elif not result:
                    logger.warning(f"Agent {agent_name} did not stop cleanly")

            for handler_id in self._registered_handlers:
                self._event_bus.unsubscribe(handler_id)
            self._registered_handlers.clear()

            await shutdown_event_bus()

            self._state = OrchestratorState.STOPPED
            logger.info("All agents stopped")
            return all_stopped

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            self._state = OrchestratorState.ERROR
            return False

    async def pause(self):
        """Pause all agents."""
        if self._state != OrchestratorState.RUNNING:
            return

        logger.info("Pausing all agents")
        for agent in self._agents.values():
            await agent.pause()
        self._state = OrchestratorState.PAUSED

    async def resume(self):
        """Resume all agents."""
        if self._state != OrchestratorState.PAUSED:
            return

        logger.info("Resuming all agents")
        for agent in self._agents.values():
            await agent.resume()
        self._state = OrchestratorState.RUNNING

    async def _health_check_loop(self):
        """Periodically check agent health and restart if needed."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)

                if self._shutdown_event.is_set():
                    break

                for agent_name, agent in self._agents.items():
                    if agent.state == AgentState.ERROR:
                        await self._handle_agent_failure(agent_name, agent)
                    elif agent.state == AgentState.STOPPED and self._state == OrchestratorState.RUNNING:
                        await self._handle_agent_failure(agent_name, agent)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _handle_agent_failure(self, agent_name: str, agent: BaseAgent):
        """
        Handle a failed agent.

        Args:
            agent_name: Name of the failed agent
            agent: The agent instance
        """
        restart_count = self._agent_restart_counts.get(agent_name, 0)

        if not self.auto_restart_agents:
            logger.warning(f"Agent {agent_name} failed but auto-restart is disabled")
            return

        if restart_count >= self.max_restart_attempts:
            logger.error(
                f"Agent {agent_name} exceeded max restart attempts ({self.max_restart_attempts})"
            )
            await self._event_bus.publish(
                EventType.ERROR,
                data={
                    "agent_name": agent_name,
                    "error": "Max restart attempts exceeded",
                    "restart_count": restart_count,
                },
                source="orchestrator",
            )
            return

        logger.warning(f"Attempting to restart agent {agent_name} (attempt {restart_count + 1})")

        try:
            await agent.stop(timeout=10.0)
            await asyncio.sleep(2.0)
            success = await agent.start()

            if success:
                self._agent_restart_counts[agent_name] = restart_count + 1
                logger.info(f"Successfully restarted agent {agent_name}")
            else:
                self._agent_restart_counts[agent_name] = restart_count + 1
                logger.error(f"Failed to restart agent {agent_name}")

        except Exception as e:
            self._agent_restart_counts[agent_name] = restart_count + 1
            logger.error(f"Error restarting agent {agent_name}: {e}")

    async def _handle_error_event(self, event: Event):
        """Handle error events from agents."""
        source = event.source
        error_data = event.data

        logger.error(
            f"Error event from {source}: {error_data.get('error', 'Unknown error')}"
        )

    async def _handle_heartbeat_event(self, event: Event):
        """Handle heartbeat events from agents."""
        agent_name = event.source
        state = event.data.get("state")

        logger.debug(f"Heartbeat from {agent_name}: {state}")

    async def _handle_workflow_event(self, event: Event):
        """Handle workflow-related events."""
        event_type = event.event_type
        request_id = event.data.get("request_id")

        if event_type == EventType.REQUEST_CREATED:
            logger.info(f"New request workflow started: {request_id}")
        elif event_type == EventType.WORKFLOW_COMPLETED:
            logger.info(f"Workflow completed: {request_id}")
        elif event_type == EventType.CLASSIFICATION_COMPLETE:
            logger.info(
                f"Classification complete for request {request_id}: "
                f"{event.data.get('total_classified')} documents"
            )

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self._agents.get(agent_name)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status."""
        agent_statuses = {}
        for agent_name, agent in self._agents.items():
            agent_statuses[agent_name] = agent.get_status()

        uptime = None
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "orchestrator_state": self._state.value,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "agent_count": len(self._agents),
            "agents": agent_statuses,
            "restart_counts": self._agent_restart_counts.copy(),
            "event_bus_status": self._event_bus.get_status() if self._event_bus else None,
            "config": {
                "auto_restart_agents": self.auto_restart_agents,
                "health_check_interval": self.health_check_interval,
                "max_restart_attempts": self.max_restart_attempts,
            },
        }

    async def run_forever(self):
        """
        Run the orchestrator until shutdown signal is received.
        Suitable for use as a background service.
        """
        if not await self.start():
            logger.error("Failed to start orchestrator")
            return

        loop = asyncio.get_event_loop()

        def signal_handler():
            logger.info("Shutdown signal received")
            self._shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                pass

        logger.info("Orchestrator running. Press Ctrl+C to stop.")

        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


async def start_orchestrator() -> AgentOrchestrator:
    """Start the global orchestrator."""
    orchestrator = get_orchestrator()
    await orchestrator.start()
    return orchestrator


async def stop_orchestrator():
    """Stop the global orchestrator."""
    global _orchestrator
    if _orchestrator:
        await _orchestrator.stop()
        _orchestrator = None


async def run_orchestrator_service():
    """
    Run the orchestrator as a service.
    This is the main entry point for running the agent system.
    """
    orchestrator = get_orchestrator()
    await orchestrator.run_forever()
