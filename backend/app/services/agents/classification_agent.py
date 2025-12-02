"""
Classification Agent for the PIA Request Automation System.
Autonomously classifies documents using AI for Texas PIA exemptions.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import asyncio
import json

from loguru import logger

from app.services.agents.base_agent import BaseAgent, RetryConfig, AgentState
from app.services.agents.event_bus import EventType, Event, EventBus
from app.services.ai.document_classifier import DocumentClassifier, get_document_classifier, ClassificationSummary
from app.services.ai.text_extractor import TextExtractor


class ClassificationAgent(BaseAgent):
    """
    Autonomous agent for classifying documents according to Texas PIA exemptions.

    Responsibilities:
    - Batch processes documents for classification
    - Handles rate limiting for LLM API calls
    - Stores classification results
    - Triggers redaction detection for sensitive content
    - Generates classification summaries
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        classifier: Optional[DocumentClassifier] = None,
        text_extractor: Optional[TextExtractor] = None,
        batch_size: int = 10,
        rate_limit_per_minute: int = 30,
        storage_path: str = "/tmp/pia_classifications",
    ):
        """
        Initialize the Classification Agent.

        Args:
            event_bus: Event bus for communication
            classifier: Document classifier instance
            text_extractor: Text extractor instance
            batch_size: Number of documents to process per batch
            rate_limit_per_minute: Maximum LLM calls per minute
            storage_path: Base path for storing classification results
        """
        super().__init__(
            agent_name="classification",
            event_bus=event_bus,
            retry_config=RetryConfig(max_retries=3, initial_delay=10.0, max_delay=300.0),
            run_interval=30.0,
            heartbeat_interval=30.0,
        )

        self.classifier = classifier
        self.text_extractor = text_extractor
        self.batch_size = batch_size
        self.rate_limit_per_minute = rate_limit_per_minute
        self.storage_path = Path(storage_path)

        self._pending_jobs: List[Dict[str, Any]] = []
        self._active_job: Optional[Dict[str, Any]] = None
        self._rate_limiter: Optional[asyncio.Semaphore] = None
        self._last_call_times: List[datetime] = []
        self._classification_results: Dict[int, List[Dict[str, Any]]] = {}
        self._classification_stats: Dict[str, int] = {
            "total_documents": 0,
            "classified": 0,
            "responsive": 0,
            "non_responsive": 0,
            "needs_review": 0,
            "with_exemptions": 0,
            "redaction_needed": 0,
            "failed": 0,
        }

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up handlers for events this agent responds to."""
        self.register_event_handler(
            EventType.DOCUMENTS_RETRIEVED,
            self._handle_documents_retrieved,
        )
        self.register_event_handler(
            EventType.EMAILS_RETRIEVED,
            self._handle_emails_retrieved,
        )
        self.register_event_handler(
            EventType.REQUEST_CANCELLED,
            self._handle_request_cancelled,
        )

    async def _on_start(self):
        """Initialize agent on startup."""
        logger.info(f"[{self.agent_name}] Initializing classification agent")

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._rate_limiter = asyncio.Semaphore(self.batch_size)

        if not self.classifier:
            self.classifier = get_document_classifier()

    async def _on_stop(self):
        """Clean up on agent stop."""
        logger.info(f"[{self.agent_name}] Shutting down classification agent")
        self._pending_jobs.clear()
        self._active_job = None

    async def run(self) -> bool:
        """
        Main execution cycle - process pending classification jobs.

        Returns:
            True if cycle completed successfully
        """
        if not self._pending_jobs and not self._active_job:
            logger.debug(f"[{self.agent_name}] No pending classification jobs")
            return True

        if not self._active_job and self._pending_jobs:
            self._active_job = self._pending_jobs.pop(0)
            self._reset_stats()

        if self._active_job:
            try:
                await self._process_classification_job(self._active_job)
                self._active_job = None
                return True
            except Exception as e:
                logger.error(f"[{self.agent_name}] Job failed: {e}")
                await self._emit_job_failed(self._active_job, str(e))
                self._active_job = None
                raise

        return True

    def _reset_stats(self):
        """Reset classification statistics for a new job."""
        self._classification_stats = {
            "total_documents": 0,
            "classified": 0,
            "responsive": 0,
            "non_responsive": 0,
            "needs_review": 0,
            "with_exemptions": 0,
            "redaction_needed": 0,
            "failed": 0,
        }
        self._last_call_times.clear()

    async def _process_classification_job(self, job: Dict[str, Any]):
        """
        Process a classification job.

        Args:
            job: Job configuration with request details
        """
        request_id = job.get("request_id")
        document_path = job.get("storage_path")
        request_description = job.get("request_description", "")
        content_type = job.get("content_type", "documents")

        logger.info(f"[{self.agent_name}] Starting classification for request {request_id}")

        documents = await self._load_documents(document_path, content_type)
        self._classification_stats["total_documents"] = len(documents)

        logger.info(f"[{self.agent_name}] Loaded {len(documents)} documents to classify")

        results = []
        summary = ClassificationSummary()

        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_results = await self._classify_batch(batch, request_description)

            for result in batch_results:
                results.append(result)
                self._update_stats(result)
                summary.add_result(result)

            await self._emit_event(
                EventType.CLASSIFICATION_PROGRESS,
                data={
                    "request_id": request_id,
                    "processed": len(results),
                    "total": len(documents),
                    "stats": self._classification_stats.copy(),
                },
                correlation_id=str(request_id),
            )

        await self._save_results(request_id, results, summary)

        self._classification_results[request_id] = results

        redaction_documents = [
            r for r in results
            if r.get("redaction_needed")
        ]

        await self._emit_event(
            EventType.CLASSIFICATION_COMPLETE,
            data={
                "request_id": request_id,
                "total_classified": self._classification_stats["classified"],
                "responsive": self._classification_stats["responsive"],
                "non_responsive": self._classification_stats["non_responsive"],
                "needs_review": self._classification_stats["needs_review"],
                "with_exemptions": self._classification_stats["with_exemptions"],
                "redaction_needed": self._classification_stats["redaction_needed"],
                "failed": self._classification_stats["failed"],
                "summary": summary.to_dict(),
                "documents_needing_redaction": len(redaction_documents),
            },
            correlation_id=str(request_id),
        )

        self._metrics.total_items_processed += self._classification_stats["classified"]

    async def _load_documents(
        self,
        storage_path: str,
        content_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Load documents for classification.

        Args:
            storage_path: Path to stored documents
            content_type: Type of content (documents or emails)

        Returns:
            List of document data for classification
        """
        documents = []
        path = Path(storage_path)

        if not path.exists():
            logger.warning(f"[{self.agent_name}] Storage path not found: {storage_path}")
            return documents

        if content_type == "emails":
            emails_path = path / "emails"
            if emails_path.exists():
                for conv_file in emails_path.glob("conv_*.json"):
                    try:
                        with open(conv_file) as f:
                            conv_data = json.load(f)

                        for msg in conv_data.get("messages", []):
                            documents.append({
                                "id": msg.get("message_id"),
                                "type": "email",
                                "filename": f"Email: {msg.get('subject', 'No Subject')[:50]}",
                                "text": self._build_email_text(msg),
                                "metadata": {
                                    "sender": msg.get("sender_email"),
                                    "recipients": msg.get("recipient_to", []),
                                    "date": msg.get("sent_date"),
                                    "document_type": "email",
                                },
                            })
                    except Exception as e:
                        logger.error(f"[{self.agent_name}] Failed to load email file: {e}")

        else:
            for file_path in path.iterdir():
                if file_path.is_file() and not file_path.name.startswith("."):
                    try:
                        text = await self._extract_text(file_path)

                        if text:
                            documents.append({
                                "id": file_path.name,
                                "type": "document",
                                "filename": file_path.name,
                                "text": text,
                                "metadata": {
                                    "filename": file_path.name,
                                    "document_type": file_path.suffix.lstrip("."),
                                    "size": file_path.stat().st_size,
                                },
                            })
                    except Exception as e:
                        logger.error(f"[{self.agent_name}] Failed to load document: {e}")

        return documents

    def _build_email_text(self, email_metadata: Dict[str, Any]) -> str:
        """Build text representation of an email for classification."""
        parts = [
            f"From: {email_metadata.get('sender_email', '')}",
            f"To: {', '.join(email_metadata.get('recipient_to', []))}",
            f"Subject: {email_metadata.get('subject', '')}",
            "",
            email_metadata.get("body_text") or email_metadata.get("body_preview", ""),
        ]
        return "\n".join(parts)

    async def _extract_text(self, file_path: Path) -> Optional[str]:
        """
        Extract text from a document file.

        Args:
            file_path: Path to the document

        Returns:
            Extracted text content
        """
        if self.text_extractor:
            try:
                return await self.text_extractor.extract(str(file_path))
            except Exception as e:
                logger.error(f"[{self.agent_name}] Text extraction failed: {e}")

        if file_path.suffix.lower() == ".txt":
            return file_path.read_text(errors="ignore")

        return None

    async def _classify_batch(
        self,
        documents: List[Dict[str, Any]],
        request_description: str,
    ) -> List[Dict[str, Any]]:
        """
        Classify a batch of documents with rate limiting.

        Args:
            documents: List of documents to classify
            request_description: PIA request description

        Returns:
            List of classification results
        """
        results = []

        for doc in documents:
            await self._wait_for_rate_limit()

            try:
                async with self._rate_limiter:
                    if doc.get("type") == "email":
                        result = await self._classify_email(doc, request_description)
                    else:
                        result = await self._classify_document(doc, request_description)

                    result["document_id"] = doc.get("id")
                    result["filename"] = doc.get("filename")
                    results.append(result)

                    self._classification_stats["classified"] += 1

            except Exception as e:
                logger.error(f"[{self.agent_name}] Classification failed for {doc.get('filename')}: {e}")
                results.append({
                    "document_id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "classification": "needs_review",
                    "confidence": 0.0,
                    "error": str(e),
                })
                self._classification_stats["failed"] += 1

        return results

    async def _classify_document(
        self,
        doc: Dict[str, Any],
        request_description: str,
    ) -> Dict[str, Any]:
        """Classify a single document."""
        return await self.classifier.classify_document(
            text_content=doc.get("text", ""),
            request_description=request_description,
            document_metadata=doc.get("metadata"),
        )

    async def _classify_email(
        self,
        doc: Dict[str, Any],
        request_description: str,
    ) -> Dict[str, Any]:
        """Classify a single email."""
        metadata = doc.get("metadata", {})
        text = doc.get("text", "")

        lines = text.split("\n", 4)
        subject = ""
        body = text

        for line in lines:
            if line.startswith("Subject:"):
                subject = line[8:].strip()
            elif not line.startswith(("From:", "To:")) and line.strip():
                body = line + "\n" + "\n".join(lines[lines.index(line)+1:]) if line in lines else text
                break

        return await self.classifier.classify_email(
            subject=subject,
            body=body,
            sender=metadata.get("sender", ""),
            recipients=metadata.get("recipients", []),
            request_description=request_description,
        )

    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        now = datetime.utcnow()

        self._last_call_times = [
            t for t in self._last_call_times
            if (now - t).total_seconds() < 60
        ]

        if len(self._last_call_times) >= self.rate_limit_per_minute:
            oldest = self._last_call_times[0]
            wait_time = 60 - (now - oldest).total_seconds()
            if wait_time > 0:
                logger.debug(f"[{self.agent_name}] Rate limiting: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._last_call_times.append(datetime.utcnow())

    def _update_stats(self, result: Dict[str, Any]):
        """Update classification statistics."""
        classification = result.get("classification", "needs_review")

        if classification == "responsive":
            self._classification_stats["responsive"] += 1
        elif classification == "non_responsive":
            self._classification_stats["non_responsive"] += 1
        else:
            self._classification_stats["needs_review"] += 1

        if result.get("exemptions"):
            self._classification_stats["with_exemptions"] += 1

        if result.get("redaction_needed"):
            self._classification_stats["redaction_needed"] += 1

    async def _save_results(
        self,
        request_id: int,
        results: List[Dict[str, Any]],
        summary: ClassificationSummary,
    ):
        """
        Save classification results to storage.

        Args:
            request_id: Associated request ID
            results: List of classification results
            summary: Classification summary
        """
        request_storage = self.storage_path / str(request_id)
        request_storage.mkdir(parents=True, exist_ok=True)

        results_file = request_storage / "classification_results.json"
        results_file.write_text(json.dumps({
            "request_id": request_id,
            "classification_date": datetime.utcnow().isoformat(),
            "results": results,
        }, indent=2, default=str))

        summary_file = request_storage / "classification_summary.json"
        summary_file.write_text(json.dumps({
            "request_id": request_id,
            "classification_date": datetime.utcnow().isoformat(),
            "summary": summary.to_dict(),
            "stats": self._classification_stats.copy(),
        }, indent=2, default=str))

        redaction_docs = [r for r in results if r.get("redaction_needed")]
        if redaction_docs:
            redaction_file = request_storage / "redaction_queue.json"
            redaction_file.write_text(json.dumps({
                "request_id": request_id,
                "documents_needing_redaction": redaction_docs,
            }, indent=2, default=str))

    async def _emit_job_failed(self, job: Dict[str, Any], error: str):
        """Emit failure event for a job."""
        await self._emit_event(
            EventType.CLASSIFICATION_FAILED,
            data={
                "request_id": job.get("request_id"),
                "error": error,
                "stats": self._classification_stats.copy(),
            },
            correlation_id=str(job.get("request_id")),
        )

    async def _handle_documents_retrieved(self, event: Event):
        """Handle documents retrieved events."""
        job = {
            "request_id": event.data.get("request_id"),
            "storage_path": event.data.get("storage_path"),
            "request_description": event.data.get("request_description", ""),
            "content_type": "documents",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._pending_jobs.append(job)
        logger.info(f"[{self.agent_name}] Queued document classification job for request {job['request_id']}")

    async def _handle_emails_retrieved(self, event: Event):
        """Handle emails retrieved events."""
        job = {
            "request_id": event.data.get("request_id"),
            "storage_path": event.data.get("storage_path"),
            "request_description": event.data.get("request_description", ""),
            "content_type": "emails",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._pending_jobs.append(job)
        logger.info(f"[{self.agent_name}] Queued email classification job for request {job['request_id']}")

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
        """Get current classification statistics."""
        return self._classification_stats.copy()

    def get_results(self, request_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get classification results for a request."""
        return self._classification_results.get(request_id)
