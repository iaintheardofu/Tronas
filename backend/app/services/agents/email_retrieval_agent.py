"""
Email Retrieval Agent for the PIA Request Automation System.
Autonomously retrieves emails from Microsoft Outlook mailboxes.
"""
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, date
from pathlib import Path
import asyncio
import json

from loguru import logger

from app.services.agents.base_agent import BaseAgent, RetryConfig, AgentState
from app.services.agents.event_bus import EventType, Event, EventBus
from app.services.microsoft.outlook_service import OutlookService, get_outlook_service


class EmailRetrievalAgent(BaseAgent):
    """
    Autonomous agent for retrieving emails from Microsoft 365 mailboxes.

    Responsibilities:
    - Searches Outlook mailboxes for relevant emails
    - Handles pagination for large result sets
    - Extracts and downloads attachments
    - Deduplicates emails by content hash
    - Groups emails by conversation thread
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        outlook_service: Optional[OutlookService] = None,
        storage_path: str = "/tmp/pia_emails",
        max_results_per_mailbox: int = 1000,
        max_concurrent_mailboxes: int = 3,
    ):
        """
        Initialize the Email Retrieval Agent.

        Args:
            event_bus: Event bus for communication
            outlook_service: Outlook service instance
            storage_path: Base path for storing downloaded emails
            max_results_per_mailbox: Maximum emails to retrieve per mailbox
            max_concurrent_mailboxes: Maximum concurrent mailbox searches
        """
        super().__init__(
            agent_name="email_retrieval",
            event_bus=event_bus,
            retry_config=RetryConfig(max_retries=3, initial_delay=5.0, max_delay=120.0),
            run_interval=60.0,
            heartbeat_interval=30.0,
        )

        self.outlook = outlook_service
        self.storage_path = Path(storage_path)
        self.max_results_per_mailbox = max_results_per_mailbox
        self.max_concurrent_mailboxes = max_concurrent_mailboxes

        self._pending_jobs: List[Dict[str, Any]] = []
        self._active_job: Optional[Dict[str, Any]] = None
        self._mailbox_semaphore: Optional[asyncio.Semaphore] = None
        self._email_hashes: Set[str] = set()
        self._conversation_threads: Dict[str, List[Dict[str, Any]]] = {}
        self._retrieval_stats: Dict[str, int] = {
            "total_found": 0,
            "processed": 0,
            "skipped_duplicate": 0,
            "attachments_downloaded": 0,
            "failed": 0,
        }

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up handlers for events this agent responds to."""
        self.register_event_handler(
            EventType.EMAIL_RETRIEVAL_STARTED,
            self._handle_retrieval_started,
        )
        self.register_event_handler(
            EventType.REQUEST_CANCELLED,
            self._handle_request_cancelled,
        )

    async def _on_start(self):
        """Initialize agent on startup."""
        logger.info(f"[{self.agent_name}] Initializing email retrieval agent")

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._mailbox_semaphore = asyncio.Semaphore(self.max_concurrent_mailboxes)

        if not self.outlook:
            self.outlook = get_outlook_service()

    async def _on_stop(self):
        """Clean up on agent stop."""
        logger.info(f"[{self.agent_name}] Shutting down email retrieval agent")
        self._pending_jobs.clear()
        self._active_job = None

    async def run(self) -> bool:
        """
        Main execution cycle - process pending retrieval jobs.

        Returns:
            True if cycle completed successfully
        """
        if not self._pending_jobs and not self._active_job:
            logger.debug(f"[{self.agent_name}] No pending email retrieval jobs")
            return True

        if not self._active_job and self._pending_jobs:
            self._active_job = self._pending_jobs.pop(0)
            self._reset_stats()

        if self._active_job:
            try:
                await self._process_retrieval_job(self._active_job)
                self._active_job = None
                return True
            except Exception as e:
                logger.error(f"[{self.agent_name}] Job failed: {e}")
                await self._emit_job_failed(self._active_job, str(e))
                self._active_job = None
                raise

        return True

    def _reset_stats(self):
        """Reset retrieval statistics for a new job."""
        self._retrieval_stats = {
            "total_found": 0,
            "processed": 0,
            "skipped_duplicate": 0,
            "attachments_downloaded": 0,
            "failed": 0,
        }
        self._email_hashes.clear()
        self._conversation_threads.clear()

    async def _process_retrieval_job(self, job: Dict[str, Any]):
        """
        Process an email retrieval job.

        Args:
            job: Job configuration with request details
        """
        request_id = job.get("request_id")
        mailboxes = job.get("mailboxes", [])
        search_criteria = job.get("search_criteria", {})

        logger.info(f"[{self.agent_name}] Starting email retrieval for request {request_id}")
        logger.info(f"[{self.agent_name}] Mailboxes to search: {len(mailboxes)}")

        all_emails = []

        search_tasks = []
        for mailbox in mailboxes:
            task = self._search_mailbox(
                mailbox=mailbox,
                search_criteria=search_criteria,
                request_id=request_id,
            )
            search_tasks.append(task)

        batch_size = self.max_concurrent_mailboxes
        for i in range(0, len(search_tasks), batch_size):
            batch = search_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"[{self.agent_name}] Mailbox search error: {result}")
                    self._retrieval_stats["failed"] += 1
                elif isinstance(result, list):
                    all_emails.extend(result)

            processed_mailboxes = min(i + batch_size, len(mailboxes))
            await self._emit_event(
                EventType.EMAIL_RETRIEVAL_PROGRESS,
                data={
                    "request_id": request_id,
                    "mailboxes_processed": processed_mailboxes,
                    "total_mailboxes": len(mailboxes),
                    "emails_found": len(all_emails),
                    "stats": self._retrieval_stats.copy(),
                },
                correlation_id=str(request_id),
            )

        unique_emails = await self._deduplicate_emails(all_emails)
        grouped_emails = await self._group_by_conversation(unique_emails)
        await self._save_emails(grouped_emails, request_id)
        await self._download_attachments(unique_emails, request_id)

        await self._emit_event(
            EventType.EMAILS_RETRIEVED,
            data={
                "request_id": request_id,
                "total_emails": self._retrieval_stats["total_found"],
                "unique_emails": self._retrieval_stats["processed"],
                "duplicates_removed": self._retrieval_stats["skipped_duplicate"],
                "attachments_downloaded": self._retrieval_stats["attachments_downloaded"],
                "conversation_threads": len(grouped_emails),
                "storage_path": str(self.storage_path / str(request_id)),
            },
            correlation_id=str(request_id),
        )

        self._metrics.total_items_processed += self._retrieval_stats["processed"]

    async def _search_mailbox(
        self,
        mailbox: str,
        search_criteria: Dict[str, Any],
        request_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Search a single mailbox for emails.

        Args:
            mailbox: Email address to search
            search_criteria: Search parameters
            request_id: Associated request ID

        Returns:
            List of email messages
        """
        async with self._mailbox_semaphore:
            try:
                logger.info(f"[{self.agent_name}] Searching mailbox: {mailbox}")

                search_terms = search_criteria.get("terms", [])
                query = " OR ".join(search_terms) if search_terms else ""

                date_from = None
                date_to = None
                if search_criteria.get("date_from"):
                    date_from = date.fromisoformat(search_criteria["date_from"])
                if search_criteria.get("date_to"):
                    date_to = date.fromisoformat(search_criteria["date_to"])

                messages = await self.outlook.search_mailbox(
                    mailbox=mailbox,
                    query=query,
                    date_from=date_from,
                    date_to=date_to,
                    max_results=self.max_results_per_mailbox,
                )

                for msg in messages:
                    msg["_mailbox"] = mailbox
                    msg["_request_id"] = request_id

                self._retrieval_stats["total_found"] += len(messages)

                logger.info(f"[{self.agent_name}] Found {len(messages)} emails in {mailbox}")
                return messages

            except Exception as e:
                logger.error(f"[{self.agent_name}] Failed to search mailbox {mailbox}: {e}")
                raise

    async def _deduplicate_emails(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate emails by content hash.

        Args:
            emails: List of email messages

        Returns:
            Deduplicated list of emails
        """
        unique_emails = []

        for email in emails:
            email_hash = self.outlook.compute_email_hash(email)

            if email_hash in self._email_hashes:
                self._retrieval_stats["skipped_duplicate"] += 1
                continue

            self._email_hashes.add(email_hash)
            email["_content_hash"] = email_hash
            unique_emails.append(email)

        logger.info(
            f"[{self.agent_name}] Deduplicated {len(emails)} -> {len(unique_emails)} emails"
        )

        self._retrieval_stats["processed"] = len(unique_emails)
        return unique_emails

    async def _group_by_conversation(
        self,
        emails: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group emails by conversation thread.

        Args:
            emails: List of email messages

        Returns:
            Dictionary mapping conversation ID to email list
        """
        conversations: Dict[str, List[Dict[str, Any]]] = {}

        for email in emails:
            conv_id = email.get("conversationId", email.get("id"))

            if conv_id not in conversations:
                conversations[conv_id] = []

            conversations[conv_id].append(email)

        for conv_id in conversations:
            conversations[conv_id].sort(
                key=lambda x: x.get("receivedDateTime", "")
            )

        self._conversation_threads = conversations

        logger.info(
            f"[{self.agent_name}] Grouped {len(emails)} emails into "
            f"{len(conversations)} conversation threads"
        )

        return conversations

    async def _save_emails(
        self,
        grouped_emails: Dict[str, List[Dict[str, Any]]],
        request_id: int,
    ):
        """
        Save emails to storage.

        Args:
            grouped_emails: Grouped email conversations
            request_id: Associated request ID
        """
        request_storage = self.storage_path / str(request_id) / "emails"
        request_storage.mkdir(parents=True, exist_ok=True)

        for conv_id, emails in grouped_emails.items():
            safe_conv_id = conv_id[:50].replace("/", "_").replace("\\", "_")

            conv_data = {
                "conversation_id": conv_id,
                "email_count": len(emails),
                "messages": [
                    self.outlook.extract_email_metadata(email)
                    for email in emails
                ],
            }

            conv_file = request_storage / f"conv_{safe_conv_id}.json"
            conv_file.write_text(json.dumps(conv_data, indent=2, default=str))

        summary = {
            "request_id": request_id,
            "total_emails": self._retrieval_stats["processed"],
            "conversation_count": len(grouped_emails),
            "retrieval_date": datetime.utcnow().isoformat(),
            "conversations": [
                {
                    "conversation_id": conv_id,
                    "email_count": len(emails),
                    "subject": emails[0].get("subject", "No Subject") if emails else "",
                }
                for conv_id, emails in grouped_emails.items()
            ],
        }

        summary_file = request_storage / "summary.json"
        summary_file.write_text(json.dumps(summary, indent=2, default=str))

    async def _download_attachments(
        self,
        emails: List[Dict[str, Any]],
        request_id: int,
    ):
        """
        Download attachments from emails.

        Args:
            emails: List of email messages
            request_id: Associated request ID
        """
        attachment_storage = self.storage_path / str(request_id) / "attachments"
        attachment_storage.mkdir(parents=True, exist_ok=True)

        for email in emails:
            if not email.get("hasAttachments"):
                continue

            mailbox = email.get("_mailbox")
            message_id = email.get("id")

            try:
                attachments = await self.outlook.get_message_attachments(
                    mailbox=mailbox,
                    message_id=message_id,
                )

                for attachment in attachments:
                    await self._save_attachment(
                        attachment=attachment,
                        mailbox=mailbox,
                        message_id=message_id,
                        storage_path=attachment_storage,
                    )

            except Exception as e:
                logger.error(
                    f"[{self.agent_name}] Failed to download attachments "
                    f"for message {message_id}: {e}"
                )

    async def _save_attachment(
        self,
        attachment: Dict[str, Any],
        mailbox: str,
        message_id: str,
        storage_path: Path,
    ):
        """
        Save a single attachment.

        Args:
            attachment: Attachment data
            mailbox: Source mailbox
            message_id: Source message ID
            storage_path: Path to save attachment
        """
        try:
            att_type = attachment.get("@odata.type", "")

            if "#microsoft.graph.fileAttachment" in att_type:
                filename = attachment.get("name", "attachment")
                content_bytes = attachment.get("contentBytes", "")

                if content_bytes:
                    import base64
                    content = base64.b64decode(content_bytes)

                    safe_filename = self._sanitize_filename(filename)
                    file_path = storage_path / safe_filename

                    counter = 1
                    while file_path.exists():
                        stem = file_path.stem
                        suffix = file_path.suffix
                        file_path = storage_path / f"{stem}_{counter}{suffix}"
                        counter += 1

                    file_path.write_bytes(content)
                    self._retrieval_stats["attachments_downloaded"] += 1

                    logger.debug(f"[{self.agent_name}] Saved attachment: {filename}")

        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to save attachment: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:255]

    async def _emit_job_failed(self, job: Dict[str, Any], error: str):
        """Emit failure event for a job."""
        await self._emit_event(
            EventType.EMAIL_RETRIEVAL_FAILED,
            data={
                "request_id": job.get("request_id"),
                "error": error,
                "stats": self._retrieval_stats.copy(),
            },
            correlation_id=str(job.get("request_id")),
        )

    async def _handle_retrieval_started(self, event: Event):
        """Handle email retrieval start events."""
        job = {
            "request_id": event.data.get("request_id"),
            "mailboxes": event.data.get("mailboxes", []),
            "search_criteria": event.data.get("search_criteria", {}),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._pending_jobs.append(job)
        logger.info(f"[{self.agent_name}] Queued email retrieval job for request {job['request_id']}")

    async def _handle_request_cancelled(self, event: Event):
        """Handle request cancellation events."""
        request_id = event.data.get("request_id")

        self._pending_jobs = [
            job for job in self._pending_jobs
            if job.get("request_id") != request_id
        ]

        if self._active_job and self._active_job.get("request_id") == request_id:
            logger.info(f"[{self.agent_name}] Cancelling active job for request {request_id}")

    def get_pending_job_count(self) -> int:
        """Get count of pending jobs."""
        return len(self._pending_jobs)

    def get_current_stats(self) -> Dict[str, int]:
        """Get current retrieval statistics."""
        return self._retrieval_stats.copy()

    def get_conversation_threads(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current conversation threads."""
        return self._conversation_threads.copy()
