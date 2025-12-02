"""
Deadline Monitor Agent for the PIA Request Automation System.
Monitors PIA request deadlines and sends notifications for approaching/overdue deadlines.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
import asyncio

from loguru import logger

from app.services.agents.base_agent import BaseAgent, RetryConfig, AgentState
from app.services.agents.event_bus import EventType, Event, EventBus
from app.services.workflow.deadline_manager import DeadlineManager, get_deadline_manager


class DeadlineMonitorAgent(BaseAgent):
    """
    Autonomous agent that monitors PIA request deadlines.

    Responsibilities:
    - Runs on a configurable schedule (default: daily)
    - Identifies approaching deadlines
    - Sends notifications to relevant users
    - Escalates overdue requests
    - Generates deadline status reports
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        deadline_manager: Optional[DeadlineManager] = None,
        check_interval_hours: float = 4.0,
        warning_thresholds: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize the Deadline Monitor Agent.

        Args:
            event_bus: Event bus for communication
            deadline_manager: Deadline manager instance
            check_interval_hours: Hours between deadline checks
            warning_thresholds: Custom warning thresholds (days before deadline)
        """
        super().__init__(
            agent_name="deadline_monitor",
            event_bus=event_bus,
            retry_config=RetryConfig(max_retries=3, initial_delay=30.0),
            run_interval=check_interval_hours * 3600,
            heartbeat_interval=60.0,
        )

        self.deadline_manager = deadline_manager
        self.warning_thresholds = warning_thresholds or {
            "critical": 0,
            "urgent": 2,
            "warning": 5,
            "approaching": 7,
        }

        self._tracked_requests: Dict[int, Dict[str, Any]] = {}
        self._last_check_time: Optional[datetime] = None
        self._notification_history: List[Dict[str, Any]] = []
        self._escalation_counts: Dict[int, int] = {}
        self._monitor_stats: Dict[str, int] = {
            "requests_monitored": 0,
            "critical_count": 0,
            "urgent_count": 0,
            "warning_count": 0,
            "notifications_sent": 0,
            "escalations": 0,
        }

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up handlers for events this agent responds to."""
        self.register_event_handler(
            EventType.REQUEST_CREATED,
            self._handle_request_created,
        )
        self.register_event_handler(
            EventType.REQUEST_COMPLETED,
            self._handle_request_completed,
        )
        self.register_event_handler(
            EventType.REQUEST_CANCELLED,
            self._handle_request_cancelled,
        )
        self.register_event_handler(
            EventType.REQUEST_UPDATED,
            self._handle_request_updated,
        )

    async def _on_start(self):
        """Initialize agent on startup."""
        logger.info(f"[{self.agent_name}] Initializing deadline monitor agent")

        if not self.deadline_manager:
            self.deadline_manager = get_deadline_manager()

        await self._load_tracked_requests()

    async def _on_stop(self):
        """Clean up on agent stop."""
        logger.info(f"[{self.agent_name}] Shutting down deadline monitor agent")

    async def _load_tracked_requests(self):
        """Load currently tracked requests from the database."""
        # This would query the database for active requests
        # For now, we rely on events to populate tracked requests
        pass

    async def run(self) -> bool:
        """
        Main execution cycle - check deadlines and send notifications.

        Returns:
            True if cycle completed successfully
        """
        try:
            logger.info(f"[{self.agent_name}] Running deadline check")

            self._reset_stats()

            deadline_statuses = await self._check_all_deadlines()

            categorized = self._categorize_by_urgency(deadline_statuses)

            await self._process_critical(categorized.get("critical", []))
            await self._process_urgent(categorized.get("urgent", []))
            await self._process_warnings(categorized.get("warning", []))
            await self._process_approaching(categorized.get("approaching", []))

            await self._send_daily_summary(deadline_statuses, categorized)

            self._last_check_time = datetime.utcnow()

            logger.info(
                f"[{self.agent_name}] Deadline check complete: "
                f"{self._monitor_stats['critical_count']} critical, "
                f"{self._monitor_stats['urgent_count']} urgent, "
                f"{self._monitor_stats['warning_count']} warnings"
            )

            return True

        except Exception as e:
            logger.error(f"[{self.agent_name}] Error in deadline check: {e}")
            raise

    def _reset_stats(self):
        """Reset monitoring statistics."""
        self._monitor_stats = {
            "requests_monitored": len(self._tracked_requests),
            "critical_count": 0,
            "urgent_count": 0,
            "warning_count": 0,
            "notifications_sent": 0,
            "escalations": 0,
        }

    async def _check_all_deadlines(self) -> List[Dict[str, Any]]:
        """
        Check deadlines for all tracked requests.

        Returns:
            List of deadline status dictionaries
        """
        statuses = []

        for request_id, request_data in self._tracked_requests.items():
            deadline_date = request_data.get("deadline")

            if isinstance(deadline_date, str):
                deadline_date = date.fromisoformat(deadline_date)

            status = self.deadline_manager.get_deadline_status(deadline_date)

            status_data = {
                "request_id": request_id,
                "request_number": request_data.get("request_number"),
                "requester_name": request_data.get("requester_name"),
                "requester_email": request_data.get("requester_email"),
                "subject": request_data.get("subject"),
                "assigned_to": request_data.get("assigned_to"),
                **status,
            }

            statuses.append(status_data)

        return statuses

    def _categorize_by_urgency(
        self,
        statuses: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize requests by urgency level.

        Args:
            statuses: List of deadline statuses

        Returns:
            Dictionary mapping urgency level to requests
        """
        categories: Dict[str, List[Dict[str, Any]]] = {
            "critical": [],
            "urgent": [],
            "warning": [],
            "approaching": [],
        }

        for status in statuses:
            days_remaining = status.get("business_days_remaining", 999)

            if days_remaining <= self.warning_thresholds["critical"]:
                categories["critical"].append(status)
                self._monitor_stats["critical_count"] += 1
            elif days_remaining <= self.warning_thresholds["urgent"]:
                categories["urgent"].append(status)
                self._monitor_stats["urgent_count"] += 1
            elif days_remaining <= self.warning_thresholds["warning"]:
                categories["warning"].append(status)
                self._monitor_stats["warning_count"] += 1
            elif days_remaining <= self.warning_thresholds["approaching"]:
                categories["approaching"].append(status)

        return categories

    async def _process_critical(self, requests: List[Dict[str, Any]]):
        """
        Process critical deadline requests (due today or overdue).

        Args:
            requests: List of critical requests
        """
        for request in requests:
            request_id = request.get("request_id")
            is_overdue = request.get("is_overdue", False)

            await self._emit_event(
                EventType.DEADLINE_OVERDUE if is_overdue else EventType.DEADLINE_CRITICAL,
                data={
                    "request_id": request_id,
                    "request_number": request.get("request_number"),
                    "deadline": request.get("deadline"),
                    "business_days_remaining": request.get("business_days_remaining"),
                    "is_overdue": is_overdue,
                    "requester_name": request.get("requester_name"),
                    "subject": request.get("subject"),
                    "severity": "critical",
                },
                correlation_id=str(request_id),
            )

            if is_overdue:
                await self._escalate_request(request)

            self._add_notification_history(request, "critical")
            self._monitor_stats["notifications_sent"] += 1

    async def _process_urgent(self, requests: List[Dict[str, Any]]):
        """
        Process urgent deadline requests (1-2 days remaining).

        Args:
            requests: List of urgent requests
        """
        for request in requests:
            request_id = request.get("request_id")

            await self._emit_event(
                EventType.DEADLINE_APPROACHING,
                data={
                    "request_id": request_id,
                    "request_number": request.get("request_number"),
                    "deadline": request.get("deadline"),
                    "business_days_remaining": request.get("business_days_remaining"),
                    "requester_name": request.get("requester_name"),
                    "subject": request.get("subject"),
                    "severity": "urgent",
                },
                correlation_id=str(request_id),
            )

            self._add_notification_history(request, "urgent")
            self._monitor_stats["notifications_sent"] += 1

    async def _process_warnings(self, requests: List[Dict[str, Any]]):
        """
        Process warning level requests (3-5 days remaining).

        Args:
            requests: List of warning level requests
        """
        for request in requests:
            request_id = request.get("request_id")

            await self._emit_event(
                EventType.DEADLINE_APPROACHING,
                data={
                    "request_id": request_id,
                    "request_number": request.get("request_number"),
                    "deadline": request.get("deadline"),
                    "business_days_remaining": request.get("business_days_remaining"),
                    "requester_name": request.get("requester_name"),
                    "subject": request.get("subject"),
                    "severity": "warning",
                },
                correlation_id=str(request_id),
            )

            self._add_notification_history(request, "warning")
            self._monitor_stats["notifications_sent"] += 1

    async def _process_approaching(self, requests: List[Dict[str, Any]]):
        """
        Process approaching deadline requests (6-7 days remaining).

        Args:
            requests: List of approaching deadline requests
        """
        for request in requests:
            request_id = request.get("request_id")

            if not self._should_notify_approaching(request_id):
                continue

            await self._emit_event(
                EventType.DEADLINE_APPROACHING,
                data={
                    "request_id": request_id,
                    "request_number": request.get("request_number"),
                    "deadline": request.get("deadline"),
                    "business_days_remaining": request.get("business_days_remaining"),
                    "requester_name": request.get("requester_name"),
                    "subject": request.get("subject"),
                    "severity": "info",
                },
                correlation_id=str(request_id),
            )

            self._add_notification_history(request, "approaching")

    def _should_notify_approaching(self, request_id: int) -> bool:
        """
        Check if we should send an approaching notification.
        Avoids spamming by limiting notifications.

        Args:
            request_id: Request ID

        Returns:
            True if notification should be sent
        """
        recent_notifications = [
            n for n in self._notification_history
            if n.get("request_id") == request_id
            and n.get("level") == "approaching"
            and (datetime.utcnow() - n.get("timestamp", datetime.min)).days < 1
        ]

        return len(recent_notifications) == 0

    async def _escalate_request(self, request: Dict[str, Any]):
        """
        Escalate an overdue request.

        Args:
            request: Request data
        """
        request_id = request.get("request_id")

        self._escalation_counts[request_id] = self._escalation_counts.get(request_id, 0) + 1
        escalation_level = self._escalation_counts[request_id]

        await self._emit_event(
            EventType.NOTIFICATION,
            data={
                "notification_type": "escalation",
                "request_id": request_id,
                "request_number": request.get("request_number"),
                "escalation_level": escalation_level,
                "days_overdue": abs(request.get("business_days_remaining", 0)),
                "message": self._generate_escalation_message(request, escalation_level),
                "recipients": self._get_escalation_recipients(escalation_level),
            },
            correlation_id=str(request_id),
        )

        self._monitor_stats["escalations"] += 1

        logger.warning(
            f"[{self.agent_name}] Escalated request {request.get('request_number')} "
            f"to level {escalation_level}"
        )

    def _generate_escalation_message(
        self,
        request: Dict[str, Any],
        escalation_level: int,
    ) -> str:
        """Generate escalation notification message."""
        days_overdue = abs(request.get("business_days_remaining", 0))

        return (
            f"PIA Request {request.get('request_number')} is {days_overdue} business days overdue.\n"
            f"Subject: {request.get('subject')}\n"
            f"Requester: {request.get('requester_name')}\n"
            f"Escalation Level: {escalation_level}\n"
            f"Immediate action required."
        )

    def _get_escalation_recipients(self, escalation_level: int) -> List[str]:
        """
        Get recipients for escalation based on level.

        Args:
            escalation_level: Current escalation level

        Returns:
            List of recipient identifiers
        """
        if escalation_level >= 3:
            return ["department_head", "legal_counsel", "records_manager"]
        elif escalation_level >= 2:
            return ["supervisor", "records_manager"]
        else:
            return ["assigned_user", "records_liaison"]

    def _add_notification_history(
        self,
        request: Dict[str, Any],
        level: str,
    ):
        """Add notification to history."""
        self._notification_history.append({
            "request_id": request.get("request_id"),
            "request_number": request.get("request_number"),
            "level": level,
            "timestamp": datetime.utcnow(),
        })

        if len(self._notification_history) > 1000:
            self._notification_history = self._notification_history[-500:]

    async def _send_daily_summary(
        self,
        all_statuses: List[Dict[str, Any]],
        categorized: Dict[str, List[Dict[str, Any]]],
    ):
        """
        Send a daily summary of deadline statuses.

        Args:
            all_statuses: All deadline statuses
            categorized: Categorized deadline data
        """
        if not all_statuses:
            return

        summary_data = {
            "total_active_requests": len(all_statuses),
            "critical_count": len(categorized.get("critical", [])),
            "urgent_count": len(categorized.get("urgent", [])),
            "warning_count": len(categorized.get("warning", [])),
            "approaching_count": len(categorized.get("approaching", [])),
            "critical_requests": [
                {
                    "request_number": r.get("request_number"),
                    "deadline": r.get("deadline"),
                    "days_remaining": r.get("business_days_remaining"),
                    "is_overdue": r.get("is_overdue"),
                }
                for r in categorized.get("critical", [])
            ],
            "report_date": date.today().isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
        }

        await self._emit_event(
            EventType.NOTIFICATION,
            data={
                "notification_type": "daily_deadline_summary",
                "summary": summary_data,
            },
        )

    async def _handle_request_created(self, event: Event):
        """Handle new request creation events."""
        request_id = event.data.get("request_id")

        self._tracked_requests[request_id] = {
            "request_id": request_id,
            "request_number": event.data.get("request_number"),
            "requester_name": event.data.get("requester_name"),
            "requester_email": event.data.get("requester_email"),
            "subject": event.data.get("subject"),
            "deadline": event.data.get("deadline"),
            "assigned_to": event.data.get("assigned_to"),
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"[{self.agent_name}] Now tracking request {event.data.get('request_number')}")

    async def _handle_request_completed(self, event: Event):
        """Handle request completion events."""
        request_id = event.data.get("request_id")

        if request_id in self._tracked_requests:
            del self._tracked_requests[request_id]
            logger.info(f"[{self.agent_name}] Stopped tracking completed request {request_id}")

        if request_id in self._escalation_counts:
            del self._escalation_counts[request_id]

    async def _handle_request_cancelled(self, event: Event):
        """Handle request cancellation events."""
        request_id = event.data.get("request_id")

        if request_id in self._tracked_requests:
            del self._tracked_requests[request_id]
            logger.info(f"[{self.agent_name}] Stopped tracking cancelled request {request_id}")

        if request_id in self._escalation_counts:
            del self._escalation_counts[request_id]

    async def _handle_request_updated(self, event: Event):
        """Handle request update events."""
        request_id = event.data.get("request_id")

        if request_id in self._tracked_requests:
            if event.data.get("deadline"):
                self._tracked_requests[request_id]["deadline"] = event.data.get("deadline")
            if event.data.get("assigned_to"):
                self._tracked_requests[request_id]["assigned_to"] = event.data.get("assigned_to")

            logger.debug(f"[{self.agent_name}] Updated tracking for request {request_id}")

    def add_request_to_track(self, request_data: Dict[str, Any]):
        """
        Manually add a request to track.

        Args:
            request_data: Request data dictionary
        """
        request_id = request_data.get("request_id") or request_data.get("id")
        self._tracked_requests[request_id] = request_data

    def get_tracked_requests(self) -> Dict[int, Dict[str, Any]]:
        """Get all tracked requests."""
        return self._tracked_requests.copy()

    def get_current_stats(self) -> Dict[str, int]:
        """Get current monitoring statistics."""
        return self._monitor_stats.copy()

    def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent notification history."""
        return self._notification_history[-limit:]
