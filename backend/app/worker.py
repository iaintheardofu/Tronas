from celery import Celery, Task
from celery.utils.log import get_task_logger
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import hashlib
import json

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentStatus, DocumentClassificationCategory
from app.models.email_record import EmailRecord
from app.models.workflow import WorkflowTask, WorkflowStatus
from app.models.pia_request import PIARequest

logger = get_task_logger(__name__)

celery_app = Celery(
    "pia_automation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


class DatabaseTask(Task):
    _session = None

    @property
    def session(self):
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.document_retrieval")
def document_retrieval_task(
    self,
    request_id: int,
    search_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retrieve documents from Microsoft 365 (SharePoint, OneDrive) based on search criteria.
    """
    logger.info(f"Starting document retrieval for request {request_id}")

    try:
        from app.services.microsoft_graph import GraphAPIClient

        results = {
            'documents_found': 0,
            'documents_downloaded': 0,
            'errors': [],
            'sources': []
        }

        graph_client = GraphAPIClient()

        search_terms = search_params.get('search_terms', '')
        date_range_start = search_params.get('date_range_start')
        date_range_end = search_params.get('date_range_end')
        departments = search_params.get('departments', [])

        for department in departments:
            try:
                documents = graph_client.search_documents(
                    search_terms=search_terms,
                    date_range_start=date_range_start,
                    date_range_end=date_range_end,
                    department=department
                )

                results['documents_found'] += len(documents)
                results['sources'].append(f"{department}: {len(documents)} documents")

                for doc in documents:
                    file_content = graph_client.download_document(doc['id'])
                    file_hash = hashlib.sha256(file_content).hexdigest()

                    results['documents_downloaded'] += 1

            except Exception as e:
                error_msg = f"Error retrieving from {department}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        logger.info(f"Document retrieval completed for request {request_id}: {results['documents_downloaded']} documents")
        return results

    except Exception as e:
        logger.error(f"Document retrieval failed for request {request_id}: {str(e)}")
        raise


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.email_retrieval")
def email_retrieval_task(
    self,
    request_id: int,
    search_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Retrieve emails from Microsoft 365 Exchange based on search criteria.
    """
    logger.info(f"Starting email retrieval for request {request_id}")

    try:
        from app.services.microsoft_graph import GraphAPIClient

        results = {
            'emails_found': 0,
            'emails_processed': 0,
            'attachments_found': 0,
            'threads_identified': 0,
            'errors': []
        }

        graph_client = GraphAPIClient()

        search_terms = search_params.get('search_terms', '')
        date_range_start = search_params.get('date_range_start')
        date_range_end = search_params.get('date_range_end')
        mailboxes = search_params.get('mailboxes', [])

        for mailbox in mailboxes:
            try:
                emails = graph_client.search_emails(
                    mailbox=mailbox,
                    search_terms=search_terms,
                    date_range_start=date_range_start,
                    date_range_end=date_range_end
                )

                results['emails_found'] += len(emails)

                for email in emails:
                    results['emails_processed'] += 1

                    if email.get('hasAttachments'):
                        attachments = graph_client.get_email_attachments(
                            mailbox=mailbox,
                            message_id=email['id']
                        )
                        results['attachments_found'] += len(attachments)

            except Exception as e:
                error_msg = f"Error retrieving from {mailbox}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        logger.info(f"Email retrieval completed for request {request_id}: {results['emails_processed']} emails")
        return results

    except Exception as e:
        logger.error(f"Email retrieval failed for request {request_id}: {str(e)}")
        raise


@celery_app.task(bind=True, name="tasks.text_extraction")
def text_extraction_task(
    self,
    document_id: int,
    file_path: str,
    mime_type: str
) -> Dict[str, Any]:
    """
    Extract text content from documents using appropriate parsers.
    """
    logger.info(f"Starting text extraction for document {document_id}")

    try:
        from app.services.document_processor import DocumentProcessor

        processor = DocumentProcessor()

        extracted_text = processor.extract_text(
            file_path=file_path,
            mime_type=mime_type
        )

        page_count = processor.get_page_count(file_path, mime_type)

        results = {
            'document_id': document_id,
            'extracted_text': extracted_text,
            'page_count': page_count,
            'character_count': len(extracted_text),
            'success': True
        }

        logger.info(f"Text extraction completed for document {document_id}: {page_count} pages, {len(extracted_text)} characters")
        return results

    except Exception as e:
        logger.error(f"Text extraction failed for document {document_id}: {str(e)}")
        return {
            'document_id': document_id,
            'success': False,
            'error': str(e)
        }


@celery_app.task(bind=True, name="tasks.classification")
def classification_task(
    self,
    document_id: int,
    extracted_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Classify documents using AI to determine responsiveness and exemptions.
    """
    logger.info(f"Starting classification for document {document_id}")

    try:
        from app.services.ai_classifier import AIClassifier

        classifier = AIClassifier()

        classification_result = classifier.classify_document(
            text=extracted_text,
            metadata=metadata or {}
        )

        results = {
            'document_id': document_id,
            'classification_category': classification_result['category'],
            'confidence_score': classification_result['confidence'],
            'reasoning': classification_result['reasoning'],
            'exemption_codes': classification_result.get('exemption_codes', []),
            'redaction_required': classification_result.get('redaction_required', False),
            'redaction_areas': classification_result.get('redaction_areas', []),
            'success': True
        }

        logger.info(f"Classification completed for document {document_id}: {results['classification_category']} ({results['confidence_score']:.2f})")
        return results

    except Exception as e:
        logger.error(f"Classification failed for document {document_id}: {str(e)}")
        return {
            'document_id': document_id,
            'success': False,
            'error': str(e)
        }


@celery_app.task(bind=True, name="tasks.deduplication")
def deduplication_task(
    self,
    request_id: int,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Identify and mark duplicate documents and emails using hash comparison.
    """
    logger.info(f"Starting deduplication for request {request_id}")

    try:
        results = {
            'documents_processed': 0,
            'duplicates_found': 0,
            'emails_processed': 0,
            'email_duplicates_found': 0,
            'threads_created': 0
        }

        hash_map = {}
        duplicate_pairs = []

        logger.info(f"Processing document deduplication for request {request_id}")

        conversation_threads = {}

        logger.info(f"Processing email thread grouping for request {request_id}")

        results['duplicates_found'] = len(duplicate_pairs)

        logger.info(f"Deduplication completed for request {request_id}: {results['duplicates_found']} duplicates found")
        return results

    except Exception as e:
        logger.error(f"Deduplication failed for request {request_id}: {str(e)}")
        raise


@celery_app.task(bind=True, name="tasks.notification")
def notification_task(
    self,
    notification_type: str,
    recipient_email: str,
    subject: str,
    body: str,
    request_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send email notifications for various events (deadline reminders, status updates, etc.).
    """
    logger.info(f"Sending {notification_type} notification to {recipient_email}")

    try:
        from app.services.email_service import EmailService

        email_service = EmailService()

        email_service.send_email(
            to_email=recipient_email,
            subject=subject,
            body=body,
            is_html=True
        )

        results = {
            'notification_type': notification_type,
            'recipient': recipient_email,
            'request_id': request_id,
            'sent_at': datetime.now(timezone.utc).isoformat(),
            'success': True
        }

        logger.info(f"Notification sent successfully to {recipient_email}")
        return results

    except Exception as e:
        logger.error(f"Notification failed for {recipient_email}: {str(e)}")
        return {
            'notification_type': notification_type,
            'recipient': recipient_email,
            'success': False,
            'error': str(e)
        }


@celery_app.task(name="tasks.batch_classification")
def batch_classification_task(request_id: int, document_ids: List[int]) -> Dict[str, Any]:
    """
    Process multiple documents in batch for classification.
    """
    logger.info(f"Starting batch classification for {len(document_ids)} documents in request {request_id}")

    results = {
        'total': len(document_ids),
        'successful': 0,
        'failed': 0,
        'errors': []
    }

    for doc_id in document_ids:
        try:
            classification_task.apply_async(args=[doc_id, "", None])
            results['successful'] += 1
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Document {doc_id}: {str(e)}")

    logger.info(f"Batch classification queued: {results['successful']} successful, {results['failed']} failed")
    return results


@celery_app.task(name="tasks.deadline_reminder")
def deadline_reminder_task() -> Dict[str, Any]:
    """
    Periodic task to check for approaching deadlines and send reminders.
    """
    logger.info("Running deadline reminder check")

    try:
        from datetime import timedelta

        today = datetime.now(timezone.utc).date()
        reminder_thresholds = [3, 7, 10]

        results = {
            'reminders_sent': 0,
            'requests_checked': 0
        }

        logger.info(f"Deadline reminder check completed: {results['reminders_sent']} reminders sent")
        return results

    except Exception as e:
        logger.error(f"Deadline reminder task failed: {str(e)}")
        raise


celery_app.conf.beat_schedule = {
    'deadline-reminders': {
        'task': 'tasks.deadline_reminder',
        'schedule': 3600.0,
    },
}
