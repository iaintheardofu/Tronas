"""
Request Monitor Agent for the PIA Request Automation System.
Monitors for new PIA requests and initializes automated workflows.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from loguru import logger

from app.services.agents.base_agent import BaseAgent, RetryConfig, AgentState
from app.services.agents.event_bus import EventType, Event, EventBus


class RequestMonitorAgent(BaseAgent):
    """
    Autonomous agent that monitors for new PIA requests.

    Responsibilities:
    - Polls the database for new requests
    - Initializes workflow for new requests
    - Dispatches document and email retrieval tasks
    - Tracks request lifecycle transitions
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        poll_interval: float = 30.0,
        batch_size: int = 10,
    ):
        """
        Initialize the Request Monitor Agent.

        Args:
            event_bus: Event bus for communication
            poll_interval: Seconds between polling cycles
            batch_size: Maximum requests to process per cycle
        """
        super().__init__(
            agent_name="request_monitor",
            event_bus=event_bus,
            retry_config=RetryConfig(max_retries=5, initial_delay=2.0),
            run_interval=poll_interval,
            heartbeat_interval=30.0,
        )

        self.batch_size = batch_size
        self._processed_request_ids: set = set()
        self._last_poll_time: Optional[datetime] = None
        self._pending_requests: List[Dict[str, Any]] = []

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up handlers for events this agent responds to."""
        self.register_event_handler(
            EventType.REQUEST_COMPLETED,
            self._handle_request_completed,
        )
        self.register_event_handler(
            EventType.WORKFLOW_COMPLETED,
            self._handle_workflow_completed,
        )
        self.register_event_handler(
            EventType.ERROR,
            self._handle_error,
        )

    async def _on_start(self):
        """Initialize the agent on startup."""
        logger.info(f"[{self.agent_name}] Initializing request monitor")
        self._processed_request_ids.clear()
        self._last_poll_time = None

    async def _on_stop(self):
        """Clean up on agent stop."""
        logger.info(f"[{self.agent_name}] Shutting down request monitor")

    async def run(self) -> bool:
        """
        Main execution cycle - poll for and process new requests.

        Returns:
            True if cycle completed successfully
        """
        try:
            new_requests = await self._poll_for_new_requests()

            if not new_requests:
                logger.debug(f"[{self.agent_name}] No new requests found")
                return True

            logger.info(f"[{self.agent_name}] Found {len(new_requests)} new request(s)")

            for request in new_requests:
                await self._process_new_request(request)

            self._last_poll_time = datetime.utcnow()
            return True

        except Exception as e:
            logger.error(f"[{self.agent_name}] Error in run cycle: {e}")
            raise

    async def _poll_for_new_requests(self) -> List[Dict[str, Any]]:
        """
        Poll the database for new PIA requests.

        Returns:
            List of new request data dictionaries
        """
        new_requests = []

        try:
            # In production, this would query the database
            # For now, simulate checking for new requests
            pending = await self._fetch_pending_requests()

            for request in pending:
                request_id = request.get("id")
                if request_id and request_id not in self._processed_request_ids:
                    new_requests.append(request)

            return new_requests[:self.batch_size]

        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to poll for requests: {e}")
            raise

    async def _fetch_pending_requests(self) -> List[Dict[str, Any]]:
        """
        Fetch pending requests from the database.

        Returns:
            List of pending request records
        """
        # This would be implemented with actual database queries
        # Example query logic:
        # SELECT * FROM pia_requests
        # WHERE status = 'pending'
        # AND workflow_initiated = false
        # ORDER BY created_at ASC
        # LIMIT batch_size

        return self._pending_requests

    async def _process_new_request(self, request: Dict[str, Any]):
        """
        Process a new PIA request and initialize its workflow.

        Args:
            request: Request data dictionary
        """
        request_id = request.get("id")
        request_number = request.get("request_number", f"REQ-{request_id}")

        logger.info(f"[{self.agent_name}] Processing new request: {request_number}")

        try:
            workflow_context = await self._create_workflow_context(request)

            await self._emit_event(
                EventType.REQUEST_CREATED,
                data={
                    "request_id": request_id,
                    "request_number": request_number,
                    "requester_name": request.get("requester_name"),
                    "requester_email": request.get("requester_email"),
                    "subject": request.get("subject"),
                    "description": request.get("description"),
                    "date_received": request.get("date_received"),
                    "deadline": request.get("deadline"),
                    "custodians": request.get("custodians", []),
                    "search_terms": request.get("search_terms", []),
                    "date_range": request.get("date_range"),
                    "workflow_context": workflow_context,
                },
                correlation_id=str(request_id),
            )

            await self._dispatch_retrieval_tasks(request, workflow_context)

            self._processed_request_ids.add(request_id)
            self._metrics.total_items_processed += 1

            logger.info(f"[{self.agent_name}] Successfully initiated workflow for {request_number}")

        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to process request {request_number}: {e}")
            await self._emit_event(
                EventType.ERROR,
                data={
                    "request_id": request_id,
                    "error": str(e),
                    "phase": "request_initialization",
                },
                correlation_id=str(request_id),
            )
            raise

    async def _create_workflow_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create workflow context for a request.

        Args:
            request: Request data

        Returns:
            Workflow context dictionary
        """
        context = {
            "request_id": request.get("id"),
            "initiated_at": datetime.utcnow().isoformat(),
            "custodians": request.get("custodians", []),
            "search_criteria": {
                "terms": request.get("search_terms", []),
                "date_from": request.get("date_range", {}).get("start"),
                "date_to": request.get("date_range", {}).get("end"),
                "file_types": request.get("file_types", []),
            },
            "sites_to_search": request.get("sharepoint_sites", []),
            "mailboxes_to_search": [
                c.get("email") for c in request.get("custodians", [])
                if c.get("email")
            ],
            "estimated_document_count": None,
            "workflow_tasks": [],
        }

        return context

    async def _dispatch_retrieval_tasks(
        self,
        request: Dict[str, Any],
        context: Dict[str, Any],
    ):
        """
        Dispatch document and email retrieval tasks.

        Args:
            request: Request data
            context: Workflow context
        """
        request_id = request.get("id")

        if context.get("sites_to_search"):
            await self._emit_event(
                EventType.DOCUMENT_RETRIEVAL_STARTED,
                data={
                    "request_id": request_id,
                    "sites": context.get("sites_to_search"),
                    "search_criteria": context.get("search_criteria"),
                },
                correlation_id=str(request_id),
            )

        if context.get("mailboxes_to_search"):
            await self._emit_event(
                EventType.EMAIL_RETRIEVAL_STARTED,
                data={
                    "request_id": request_id,
                    "mailboxes": context.get("mailboxes_to_search"),
                    "search_criteria": context.get("search_criteria"),
                },
                correlation_id=str(request_id),
            )

    async def _handle_request_completed(self, event: Event):
        """Handle request completion events."""
        request_id = event.data.get("request_id")
        if request_id in self._processed_request_ids:
            self._processed_request_ids.discard(request_id)
            logger.info(f"[{self.agent_name}] Request {request_id} completed and removed from tracking")

    async def _handle_workflow_completed(self, event: Event):
        """Handle workflow completion events."""
        request_id = event.data.get("request_id")
        logger.info(f"[{self.agent_name}] Workflow completed for request {request_id}")

    async def _handle_error(self, event: Event):
        """Handle error events."""
        if event.data.get("phase") == "request_initialization":
            request_id = event.data.get("request_id")
            logger.warning(f"[{self.agent_name}] Received error for request {request_id}")

    def add_pending_request(self, request: Dict[str, Any]):
        """
        Add a request to the pending queue for testing or manual injection.

        Args:
            request: Request data dictionary
        """
        self._pending_requests.append(request)

    def get_processed_request_ids(self) -> set:
        """Get set of processed request IDs."""
        return self._processed_request_ids.copy()

    def get_pending_count(self) -> int:
        """Get count of pending requests."""
        return len(self._pending_requests)
