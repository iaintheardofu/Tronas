"""
Agentic Orchestration Layer for PIA Request Automation System.

This module provides a fully autonomous agent-based system for processing
Public Information Act (PIA) requests. The system includes:

- Event Bus: Publish/subscribe pattern for inter-agent communication
- Base Agent: Foundation class with state machine, retry logic, and monitoring
- Request Monitor: Detects and initiates processing for new requests
- Document Retrieval: Fetches documents from SharePoint/OneDrive
- Email Retrieval: Retrieves emails from Outlook mailboxes
- Classification: Automated document classification for PIA exemptions
- Deadline Monitor: Tracks deadlines and sends notifications
- Orchestrator: Manages all agent lifecycles and coordination

Usage:
    from app.services.agents import run_orchestrator_service

    # Run as a background service
    await run_orchestrator_service()

Or for programmatic control:
    from app.services.agents import get_orchestrator, AgentOrchestrator

    orchestrator = get_orchestrator()
    await orchestrator.start()
    # ... do work ...
    await orchestrator.stop()
"""

from app.services.agents.event_bus import (
    EventBus,
    EventType,
    Event,
    Subscription,
    get_event_bus,
    init_event_bus,
    shutdown_event_bus,
)

from app.services.agents.base_agent import (
    BaseAgent,
    AgentState,
    RetryConfig,
    AgentMetrics,
)

from app.services.agents.request_monitor_agent import RequestMonitorAgent
from app.services.agents.document_retrieval_agent import DocumentRetrievalAgent
from app.services.agents.email_retrieval_agent import EmailRetrievalAgent
from app.services.agents.classification_agent import ClassificationAgent
from app.services.agents.deadline_monitor_agent import DeadlineMonitorAgent

from app.services.agents.orchestrator import (
    AgentOrchestrator,
    OrchestratorState,
    get_orchestrator,
    start_orchestrator,
    stop_orchestrator,
    run_orchestrator_service,
)


__all__ = [
    # Event Bus
    "EventBus",
    "EventType",
    "Event",
    "Subscription",
    "get_event_bus",
    "init_event_bus",
    "shutdown_event_bus",

    # Base Agent
    "BaseAgent",
    "AgentState",
    "RetryConfig",
    "AgentMetrics",

    # Agents
    "RequestMonitorAgent",
    "DocumentRetrievalAgent",
    "EmailRetrievalAgent",
    "ClassificationAgent",
    "DeadlineMonitorAgent",

    # Orchestrator
    "AgentOrchestrator",
    "OrchestratorState",
    "get_orchestrator",
    "start_orchestrator",
    "stop_orchestrator",
    "run_orchestrator_service",
]
