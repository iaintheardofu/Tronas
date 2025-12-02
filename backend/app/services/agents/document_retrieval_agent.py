"""
Document Retrieval Agent for the PIA Request Automation System.
Autonomously retrieves documents from Microsoft SharePoint and OneDrive.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from pathlib import Path
import asyncio

from loguru import logger

from app.services.agents.base_agent import BaseAgent, RetryConfig, AgentState
from app.services.agents.event_bus import EventType, Event, EventBus
from app.services.microsoft.sharepoint_service import SharePointService, get_sharepoint_service
from app.services.microsoft.graph_client import MSGraphClient, get_graph_client


class DocumentRetrievalAgent(BaseAgent):
    """
    Autonomous agent for retrieving documents from Microsoft 365.

    Responsibilities:
    - Connects to Microsoft Graph API
    - Crawls SharePoint sites and OneDrive
    - Downloads and stores documents locally
    - Reports progress and handles errors
    - Deduplicates documents by content hash
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        sharepoint_service: Optional[SharePointService] = None,
        storage_path: str = "/tmp/pia_documents",
        max_concurrent_downloads: int = 5,
        max_file_size_mb: int = 100,
    ):
        """
        Initialize the Document Retrieval Agent.

        Args:
            event_bus: Event bus for communication
            sharepoint_service: SharePoint service instance
            storage_path: Base path for storing downloaded documents
            max_concurrent_downloads: Maximum concurrent download tasks
            max_file_size_mb: Maximum file size to download in MB
        """
        super().__init__(
            agent_name="document_retrieval",
            event_bus=event_bus,
            retry_config=RetryConfig(max_retries=3, initial_delay=5.0, max_delay=120.0),
            run_interval=60.0,
            heartbeat_interval=30.0,
        )

        self.sharepoint = sharepoint_service
        self.storage_path = Path(storage_path)
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

        self._pending_jobs: List[Dict[str, Any]] = []
        self._active_job: Optional[Dict[str, Any]] = None
        self._download_semaphore: Optional[asyncio.Semaphore] = None
        self._document_hashes: set = set()
        self._retrieval_stats: Dict[str, int] = {
            "total_found": 0,
            "downloaded": 0,
            "skipped_duplicate": 0,
            "skipped_size": 0,
            "failed": 0,
        }

        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up handlers for events this agent responds to."""
        self.register_event_handler(
            EventType.DOCUMENT_RETRIEVAL_STARTED,
            self._handle_retrieval_started,
        )
        self.register_event_handler(
            EventType.REQUEST_CANCELLED,
            self._handle_request_cancelled,
        )

    async def _on_start(self):
        """Initialize agent on startup."""
        logger.info(f"[{self.agent_name}] Initializing document retrieval agent")

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        if not self.sharepoint:
            self.sharepoint = get_sharepoint_service()

    async def _on_stop(self):
        """Clean up on agent stop."""
        logger.info(f"[{self.agent_name}] Shutting down document retrieval agent")
        self._pending_jobs.clear()
        self._active_job = None

    async def run(self) -> bool:
        """
        Main execution cycle - process pending retrieval jobs.

        Returns:
            True if cycle completed successfully
        """
        if not self._pending_jobs and not self._active_job:
            logger.debug(f"[{self.agent_name}] No pending retrieval jobs")
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
            "downloaded": 0,
            "skipped_duplicate": 0,
            "skipped_size": 0,
            "failed": 0,
        }
        self._document_hashes.clear()

    async def _process_retrieval_job(self, job: Dict[str, Any]):
        """
        Process a document retrieval job.

        Args:
            job: Job configuration with request details
        """
        request_id = job.get("request_id")
        sites = job.get("sites", [])
        search_criteria = job.get("search_criteria", {})

        logger.info(f"[{self.agent_name}] Starting retrieval for request {request_id}")
        logger.info(f"[{self.agent_name}] Sites to search: {len(sites)}")

        all_documents = []

        for site_config in sites:
            site_id = site_config.get("site_id") or site_config.get("id")
            site_name = site_config.get("name", site_id)

            logger.info(f"[{self.agent_name}] Processing site: {site_name}")

            try:
                site_documents = await self._crawl_site(
                    site_id=site_id,
                    search_criteria=search_criteria,
                    request_id=request_id,
                )
                all_documents.extend(site_documents)

                await self._emit_event(
                    EventType.DOCUMENT_RETRIEVAL_PROGRESS,
                    data={
                        "request_id": request_id,
                        "site_name": site_name,
                        "documents_found": len(site_documents),
                        "total_so_far": len(all_documents),
                        "stats": self._retrieval_stats.copy(),
                    },
                    correlation_id=str(request_id),
                )

            except Exception as e:
                logger.error(f"[{self.agent_name}] Failed to crawl site {site_name}: {e}")
                self._retrieval_stats["failed"] += 1

        await self._download_documents(all_documents, request_id)

        await self._emit_event(
            EventType.DOCUMENTS_RETRIEVED,
            data={
                "request_id": request_id,
                "total_documents": len(all_documents),
                "downloaded": self._retrieval_stats["downloaded"],
                "skipped_duplicate": self._retrieval_stats["skipped_duplicate"],
                "skipped_size": self._retrieval_stats["skipped_size"],
                "failed": self._retrieval_stats["failed"],
                "storage_path": str(self.storage_path / str(request_id)),
            },
            correlation_id=str(request_id),
        )

        self._metrics.total_items_processed += self._retrieval_stats["downloaded"]

    async def _crawl_site(
        self,
        site_id: str,
        search_criteria: Dict[str, Any],
        request_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Crawl a SharePoint site for documents.

        Args:
            site_id: SharePoint site ID
            search_criteria: Search parameters
            request_id: Associated request ID

        Returns:
            List of document metadata
        """
        documents = []

        try:
            drives = await self.sharepoint.get_drives(site_id)

            for drive in drives:
                drive_id = drive.get("id")
                drive_name = drive.get("name", drive_id)

                logger.debug(f"[{self.agent_name}] Crawling drive: {drive_name}")

                file_types = search_criteria.get("file_types", [
                    "pdf", "doc", "docx", "xls", "xlsx",
                    "ppt", "pptx", "txt", "msg", "eml",
                ])

                drive_docs = await self.sharepoint.crawl_library(
                    site_id=site_id,
                    drive_id=drive_id,
                    recursive=True,
                    file_filter=file_types,
                )

                for doc in drive_docs:
                    doc["request_id"] = request_id
                    doc["drive_name"] = drive_name

                documents.extend(drive_docs)

        except Exception as e:
            logger.error(f"[{self.agent_name}] Error crawling site {site_id}: {e}")
            raise

        self._retrieval_stats["total_found"] += len(documents)
        return documents

    async def _download_documents(
        self,
        documents: List[Dict[str, Any]],
        request_id: int,
    ):
        """
        Download documents concurrently with rate limiting.

        Args:
            documents: List of document metadata
            request_id: Associated request ID
        """
        request_storage = self.storage_path / str(request_id)
        request_storage.mkdir(parents=True, exist_ok=True)

        tasks = []
        for doc in documents:
            task = self._download_single_document(doc, request_storage)
            tasks.append(task)

        batch_size = self.max_concurrent_downloads * 2
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)

            if i + batch_size < len(tasks):
                await asyncio.sleep(0.5)

    async def _download_single_document(
        self,
        doc: Dict[str, Any],
        storage_path: Path,
    ) -> Optional[str]:
        """
        Download a single document.

        Args:
            doc: Document metadata
            storage_path: Path to store the document

        Returns:
            Local file path if successful
        """
        async with self._download_semaphore:
            try:
                file_size = doc.get("size", 0)
                if file_size > self.max_file_size_bytes:
                    logger.debug(f"[{self.agent_name}] Skipping large file: {doc.get('name')}")
                    self._retrieval_stats["skipped_size"] += 1
                    return None

                site_id = doc.get("site_id")
                drive_id = doc.get("drive_id")
                item_id = doc.get("id")
                filename = doc.get("name", f"document_{item_id}")

                content = await self.sharepoint.download_document(
                    site_id=site_id,
                    drive_id=drive_id,
                    item_id=item_id,
                )

                content_hash = self.sharepoint.compute_document_hash(content)

                if content_hash in self._document_hashes:
                    logger.debug(f"[{self.agent_name}] Skipping duplicate: {filename}")
                    self._retrieval_stats["skipped_duplicate"] += 1
                    return None

                self._document_hashes.add(content_hash)

                safe_filename = self._sanitize_filename(filename)
                file_path = storage_path / safe_filename

                counter = 1
                while file_path.exists():
                    stem = file_path.stem
                    suffix = file_path.suffix
                    file_path = storage_path / f"{stem}_{counter}{suffix}"
                    counter += 1

                file_path.write_bytes(content)
                self._retrieval_stats["downloaded"] += 1

                logger.debug(f"[{self.agent_name}] Downloaded: {filename}")
                return str(file_path)

            except Exception as e:
                logger.error(f"[{self.agent_name}] Download failed for {doc.get('name')}: {e}")
                self._retrieval_stats["failed"] += 1
                return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:255]

    async def _emit_job_failed(self, job: Dict[str, Any], error: str):
        """Emit failure event for a job."""
        await self._emit_event(
            EventType.DOCUMENT_RETRIEVAL_FAILED,
            data={
                "request_id": job.get("request_id"),
                "error": error,
                "stats": self._retrieval_stats.copy(),
            },
            correlation_id=str(job.get("request_id")),
        )

    async def _handle_retrieval_started(self, event: Event):
        """Handle document retrieval start events."""
        job = {
            "request_id": event.data.get("request_id"),
            "sites": event.data.get("sites", []),
            "search_criteria": event.data.get("search_criteria", {}),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._pending_jobs.append(job)
        logger.info(f"[{self.agent_name}] Queued retrieval job for request {job['request_id']}")

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
