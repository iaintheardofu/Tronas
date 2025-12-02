"""
Document processing orchestration service.
Coordinates retrieval, extraction, classification, and deduplication.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from loguru import logger

from app.services.ai.text_extractor import TextExtractor, get_text_extractor
from app.services.ai.document_classifier import DocumentClassifier, get_document_classifier, ClassificationSummary
from app.services.ai.redaction_detector import RedactionDetector, get_redaction_detector
from app.services.documents.deduplication_service import DeduplicationService, get_deduplication_service


class DocumentProcessor:
    """
    Orchestrates the complete document processing pipeline:
    1. Text extraction
    2. Deduplication
    3. AI classification
    4. Redaction detection
    5. Label application
    """

    def __init__(
        self,
        text_extractor: Optional[TextExtractor] = None,
        classifier: Optional[DocumentClassifier] = None,
        redaction_detector: Optional[RedactionDetector] = None,
        dedup_service: Optional[DeduplicationService] = None,
    ):
        self.text_extractor = text_extractor or get_text_extractor()
        self.classifier = classifier or get_document_classifier()
        self.redaction_detector = redaction_detector or get_redaction_detector()
        self.dedup_service = dedup_service or get_deduplication_service()

    async def process_document(
        self,
        file_path: str = None,
        file_content: bytes = None,
        filename: str = None,
        mime_type: str = None,
        request_description: str = "",
        detect_redactions: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a single document through the complete pipeline.

        Args:
            file_path: Path to the file
            file_content: File content bytes
            filename: Original filename
            mime_type: MIME type
            request_description: PIA request description for classification
            detect_redactions: Whether to detect redaction areas

        Returns:
            Complete processing result
        """
        start_time = datetime.utcnow()

        # Step 1: Extract text
        extraction_result = await self.text_extractor.extract_text(
            file_path=file_path,
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
        )

        if not extraction_result.get("text"):
            return {
                "status": "error",
                "error": "Failed to extract text from document",
                "extraction": extraction_result,
                "processing_time_ms": self._elapsed_ms(start_time),
            }

        text_content = extraction_result["text"]

        # Step 2: Classify document
        classification_result = await self.classifier.classify_document(
            text_content=text_content,
            request_description=request_description,
            document_metadata={
                "filename": filename,
                "mime_type": mime_type,
                "word_count": extraction_result.get("word_count", 0),
            },
        )

        # Step 3: Detect redactions (if needed and document is responsive)
        redaction_result = None
        if detect_redactions and classification_result.get("classification") == "responsive":
            redaction_result = await self.redaction_detector.detect_all_redactions(
                text=text_content,
                context=request_description,
            )

        # Step 4: Generate labels
        labels = self._generate_labels(classification_result, redaction_result)

        return {
            "status": "success",
            "extraction": {
                "file_hash": extraction_result.get("file_hash"),
                "mime_type": extraction_result.get("mime_type"),
                "char_count": extraction_result.get("char_count"),
                "word_count": extraction_result.get("word_count"),
                "page_count": extraction_result.get("metadata", {}).get("page_count", 1),
            },
            "classification": classification_result,
            "redactions": redaction_result,
            "labels": labels,
            "processing_time_ms": self._elapsed_ms(start_time),
        }

    async def process_batch(
        self,
        documents: List[Dict[str, Any]],
        request_description: str,
        concurrency: int = 3,
        detect_redactions: bool = True,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Process multiple documents with progress tracking.

        Args:
            documents: List of documents with path/content/filename
            request_description: PIA request description
            concurrency: Number of concurrent processes
            detect_redactions: Whether to detect redactions
            progress_callback: Optional callback for progress updates

        Returns:
            Batch processing results with statistics
        """
        start_time = datetime.utcnow()
        total = len(documents)
        processed = 0
        results = []
        errors = []

        semaphore = asyncio.Semaphore(concurrency)
        summary = ClassificationSummary()

        async def process_with_limit(doc: Dict, index: int):
            nonlocal processed
            async with semaphore:
                try:
                    result = await self.process_document(
                        file_path=doc.get("path"),
                        file_content=doc.get("content"),
                        filename=doc.get("filename"),
                        mime_type=doc.get("mime_type"),
                        request_description=request_description,
                        detect_redactions=detect_redactions,
                    )
                    result["document_id"] = doc.get("id")
                    result["index"] = index

                    if result.get("classification"):
                        summary.add_result(result["classification"])

                    return result

                except Exception as e:
                    logger.error(f"Error processing document {index}: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "document_id": doc.get("id"),
                        "index": index,
                    }
                finally:
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, total)

        tasks = [process_with_limit(doc, i) for i, doc in enumerate(documents)]
        results = await asyncio.gather(*tasks)

        # Separate successful and failed
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]

        return {
            "total_documents": total,
            "successful": len(successful),
            "failed": len(failed),
            "results": results,
            "classification_summary": summary.to_dict(),
            "processing_time_ms": self._elapsed_ms(start_time),
            "avg_time_per_document_ms": self._elapsed_ms(start_time) / total if total > 0 else 0,
        }

    async def process_pia_request_documents(
        self,
        documents: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
        request_description: str,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Complete PIA request document processing pipeline.

        Args:
            documents: List of documents from SharePoint/OneDrive
            emails: List of email records from Outlook
            request_description: PIA request description
            progress_callback: Optional progress callback

        Returns:
            Complete processing results
        """
        start_time = datetime.utcnow()

        # Step 1: Deduplicate documents
        logger.info(f"Deduplicating {len(documents)} documents")
        doc_dedup = self.dedup_service.deduplicate_documents(documents)

        # Step 2: Process emails (deduplicate and group)
        logger.info(f"Processing {len(emails)} emails")
        email_processing = self.dedup_service.process_emails_for_pia(emails)

        # Step 3: Process unique documents
        logger.info(f"Classifying {len(doc_dedup['unique_documents'])} unique documents")

        doc_results = await self.process_batch(
            documents=doc_dedup["unique_documents"],
            request_description=request_description,
            detect_redactions=True,
            progress_callback=progress_callback,
        )

        # Step 4: Process email threads (classify representative emails)
        # For each thread, we classify the final email (contains full thread)
        thread_results = []
        for thread in email_processing["threads"]:
            review_emails = thread.get("review_emails", [])
            if review_emails:
                # Classify the representative email
                email = review_emails[0]
                classification = await self.classifier.classify_email(
                    subject=email.get("subject", ""),
                    body=email.get("body_text", "") or email.get("body_preview", ""),
                    sender=email.get("sender_email", ""),
                    recipients=email.get("recipient_to", []),
                    request_description=request_description,
                )
                thread["classification"] = classification
            thread_results.append(thread)

        # Step 5: Generate summary
        total_items = len(documents) + len(emails)
        items_for_review = (
            len(doc_dedup["unique_documents"]) +
            email_processing["processing_stats"]["review_email_count"]
        )

        return {
            "request_description": request_description,
            "processing_time_ms": self._elapsed_ms(start_time),
            "input_stats": {
                "total_documents": len(documents),
                "total_emails": len(emails),
                "total_items": total_items,
            },
            "deduplication_stats": {
                "documents": doc_dedup["stats"],
                "emails": email_processing["deduplication_stats"],
            },
            "processing_stats": {
                "documents_classified": doc_results["successful"],
                "documents_failed": doc_results["failed"],
                "email_threads": len(thread_results),
            },
            "efficiency_stats": {
                "items_requiring_review": items_for_review,
                "items_saved_from_review": total_items - items_for_review,
                "reduction_percent": round(
                    ((total_items - items_for_review) / total_items * 100) if total_items > 0 else 0, 1
                ),
            },
            "classification_summary": doc_results["classification_summary"],
            "document_results": doc_results["results"],
            "email_threads": thread_results,
        }

    def _generate_labels(
        self,
        classification: Dict[str, Any],
        redaction_result: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate document labels based on classification and redaction results."""
        labels = []

        # Classification label
        classification_type = classification.get("classification", "needs_review")
        labels.append({
            "label": classification_type.upper(),
            "label_type": "classification",
            "color": self._get_classification_color(classification_type),
            "ai_generated": True,
        })

        # Exemption labels
        for exemption in classification.get("exemptions", []):
            labels.append({
                "label": exemption.get("category", "").upper()[:30],
                "label_type": "exemption",
                "color": "#FFA500",  # Orange
                "ai_generated": True,
                "exemption_section": exemption.get("section"),
            })

        # Redaction label
        if redaction_result and redaction_result.get("summary", {}).get("total_redactions", 0) > 0:
            labels.append({
                "label": "REDACTION NEEDED",
                "label_type": "status",
                "color": "#FF4444",  # Red
                "ai_generated": True,
            })

        return labels

    def _get_classification_color(self, classification: str) -> str:
        """Get color for classification type."""
        colors = {
            "responsive": "#4CAF50",  # Green
            "non_responsive": "#9E9E9E",  # Gray
            "needs_review": "#FF9800",  # Orange
        }
        return colors.get(classification, "#9E9E9E")

    def _elapsed_ms(self, start_time: datetime) -> int:
        """Calculate elapsed milliseconds."""
        return int((datetime.utcnow() - start_time).total_seconds() * 1000)


# Singleton instance
_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """Get or create the document processor singleton."""
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
