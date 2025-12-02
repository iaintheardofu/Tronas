"""
CRUD service for Email Records and Threads.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import hashlib

from app.services.crud.base_service import BaseCRUDService
from app.models.email_record import EmailRecord, EmailThread


class EmailService(BaseCRUDService[EmailRecord]):
    """
    Service for Email Record CRUD operations.
    """

    def __init__(self):
        super().__init__(EmailRecord)

    async def create_email(
        self,
        db: AsyncSession,
        request_id: int,
        message_id: str,
        subject: str,
        sender: str,
        recipients: List[str],
        body_text: str,
        received_date: datetime,
        mailbox: str,
        conversation_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        has_attachments: bool = False,
        attachment_count: int = 0,
        importance: str = "normal",
        headers: Optional[Dict] = None,
    ) -> EmailRecord:
        """
        Create a new email record.

        Args:
            db: Database session
            request_id: Associated PIA request ID
            message_id: Unique message ID
            subject: Email subject
            sender: Sender email address
            recipients: List of recipient addresses
            body_text: Email body content
            received_date: When email was received
            mailbox: Source mailbox
            conversation_id: Outlook conversation ID
            thread_id: Thread ID for grouping
            has_attachments: Whether email has attachments
            attachment_count: Number of attachments
            importance: Email importance level
            headers: Email headers

        Returns:
            Created email record
        """
        # Generate content hash for deduplication
        content_for_hash = f"{sender}:{subject}:{body_text[:1000]}"
        content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

        email_data = {
            "pia_request_id": request_id,
            "message_id": message_id,
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "body_text": body_text,
            "received_date": received_date,
            "mailbox": mailbox,
            "conversation_id": conversation_id,
            "thread_id": thread_id,
            "has_attachments": has_attachments,
            "attachment_count": attachment_count,
            "importance": importance,
            "headers": headers or {},
            "content_hash": content_hash,
        }

        return await self.create(db, email_data)

    async def get_emails_for_request(
        self,
        db: AsyncSession,
        request_id: int,
        include_duplicates: bool = False,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[EmailRecord]:
        """
        Get all emails for a PIA request.

        Args:
            db: Database session
            request_id: PIA request ID
            include_duplicates: Whether to include duplicates
            skip: Pagination offset
            limit: Page size

        Returns:
            List of email records
        """
        query = select(EmailRecord).where(EmailRecord.pia_request_id == request_id)

        if not include_duplicates:
            query = query.where(EmailRecord.is_duplicate == False)

        query = query.order_by(EmailRecord.received_date.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_email_by_message_id(
        self,
        db: AsyncSession,
        message_id: str,
        request_id: int,
    ) -> Optional[EmailRecord]:
        """
        Get email by its message ID.

        Args:
            db: Database session
            message_id: Unique message ID
            request_id: PIA request ID

        Returns:
            Email record or None
        """
        query = select(EmailRecord).where(
            and_(
                EmailRecord.message_id == message_id,
                EmailRecord.pia_request_id == request_id,
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def find_duplicate_by_hash(
        self,
        db: AsyncSession,
        content_hash: str,
        request_id: int,
        exclude_id: Optional[int] = None,
    ) -> Optional[EmailRecord]:
        """
        Find email by content hash for deduplication.

        Args:
            db: Database session
            content_hash: Content hash
            request_id: PIA request ID
            exclude_id: Email ID to exclude

        Returns:
            Matching email or None
        """
        query = select(EmailRecord).where(
            and_(
                EmailRecord.content_hash == content_hash,
                EmailRecord.pia_request_id == request_id,
                EmailRecord.is_duplicate == False,
            )
        )

        if exclude_id:
            query = query.where(EmailRecord.id != exclude_id)

        query = query.order_by(EmailRecord.created_at.asc()).limit(1)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def mark_as_duplicate(
        self,
        db: AsyncSession,
        email_id: int,
        duplicate_of_id: int,
    ) -> Optional[EmailRecord]:
        """
        Mark an email as a duplicate.

        Args:
            db: Database session
            email_id: Email ID to mark
            duplicate_of_id: ID of the original email

        Returns:
            Updated email or None
        """
        return await self.update(
            db,
            email_id,
            {
                "is_duplicate": True,
                "duplicate_of_id": duplicate_of_id,
            }
        )

    async def update_classification(
        self,
        db: AsyncSession,
        email_id: int,
        classification: str,
        is_responsive: bool,
        exemptions: Optional[List[Dict]] = None,
    ) -> Optional[EmailRecord]:
        """
        Update email classification.

        Args:
            db: Database session
            email_id: Email ID
            classification: Classification result
            is_responsive: Whether email is responsive
            exemptions: Exemption details

        Returns:
            Updated email or None
        """
        return await self.update(
            db,
            email_id,
            {
                "ai_classification": classification,
                "is_responsive": is_responsive,
                "exemptions_detected": exemptions or [],
            }
        )

    async def get_unclassified_emails(
        self,
        db: AsyncSession,
        request_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[EmailRecord]:
        """
        Get emails that haven't been classified.

        Args:
            db: Database session
            request_id: Optional filter by request
            limit: Maximum to return

        Returns:
            List of unclassified emails
        """
        query = select(EmailRecord).where(
            and_(
                EmailRecord.ai_classification == None,
                EmailRecord.is_duplicate == False,
            )
        )

        if request_id:
            query = query.where(EmailRecord.pia_request_id == request_id)

        query = query.order_by(EmailRecord.created_at.asc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


class EmailThreadService(BaseCRUDService[EmailThread]):
    """
    Service for Email Thread operations.
    """

    def __init__(self):
        super().__init__(EmailThread)

    async def create_or_update_thread(
        self,
        db: AsyncSession,
        request_id: int,
        conversation_id: str,
        subject: str,
        participants: List[str],
        email_count: int = 1,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
    ) -> EmailThread:
        """
        Create or update an email thread.

        Args:
            db: Database session
            request_id: PIA request ID
            conversation_id: Outlook conversation ID
            subject: Thread subject
            participants: All thread participants
            email_count: Number of emails in thread
            date_range_start: Earliest email date
            date_range_end: Latest email date

        Returns:
            Created or updated thread
        """
        # Check if thread exists
        existing = await self.get_thread_by_conversation_id(
            db, conversation_id, request_id
        )

        if existing:
            # Update existing thread
            update_data = {
                "email_count": email_count,
                "unique_participants": list(set(existing.unique_participants + participants)),
            }
            if date_range_start and (not existing.date_range_start or date_range_start < existing.date_range_start):
                update_data["date_range_start"] = date_range_start
            if date_range_end and (not existing.date_range_end or date_range_end > existing.date_range_end):
                update_data["date_range_end"] = date_range_end

            return await self.update(db, existing.id, update_data)

        # Create new thread
        thread_data = {
            "pia_request_id": request_id,
            "conversation_id": conversation_id,
            "subject": subject,
            "unique_participants": list(set(participants)),
            "email_count": email_count,
            "date_range_start": date_range_start,
            "date_range_end": date_range_end,
        }

        return await self.create(db, thread_data)

    async def get_thread_by_conversation_id(
        self,
        db: AsyncSession,
        conversation_id: str,
        request_id: int,
    ) -> Optional[EmailThread]:
        """
        Get thread by conversation ID.

        Args:
            db: Database session
            conversation_id: Outlook conversation ID
            request_id: PIA request ID

        Returns:
            Email thread or None
        """
        query = select(EmailThread).where(
            and_(
                EmailThread.conversation_id == conversation_id,
                EmailThread.pia_request_id == request_id,
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_threads_for_request(
        self,
        db: AsyncSession,
        request_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[EmailThread]:
        """
        Get all threads for a request.

        Args:
            db: Database session
            request_id: PIA request ID
            skip: Pagination offset
            limit: Page size

        Returns:
            List of email threads
        """
        query = (
            select(EmailThread)
            .where(EmailThread.pia_request_id == request_id)
            .options(selectinload(EmailThread.emails))
            .order_by(EmailThread.date_range_end.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_thread_with_emails(
        self,
        db: AsyncSession,
        thread_id: int,
    ) -> Optional[EmailThread]:
        """
        Get thread with all its emails.

        Args:
            db: Database session
            thread_id: Thread ID

        Returns:
            Thread with emails or None
        """
        query = (
            select(EmailThread)
            .where(EmailThread.id == thread_id)
            .options(selectinload(EmailThread.emails))
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_thread_summary(
        self,
        db: AsyncSession,
        thread_id: int,
        summary: str,
        representative_email_id: Optional[int] = None,
    ) -> Optional[EmailThread]:
        """
        Update thread summary.

        Args:
            db: Database session
            thread_id: Thread ID
            summary: AI-generated summary
            representative_email_id: ID of best email for review

        Returns:
            Updated thread or None
        """
        update_data = {"summary": summary}
        if representative_email_id:
            update_data["representative_email_id"] = representative_email_id

        return await self.update(db, thread_id, update_data)

    async def get_email_statistics(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Dict[str, Any]:
        """
        Get email statistics for a request.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            Email statistics
        """
        # Total emails (non-duplicate)
        total_query = (
            select(func.count())
            .select_from(EmailRecord)
            .where(
                and_(
                    EmailRecord.pia_request_id == request_id,
                    EmailRecord.is_duplicate == False,
                )
            )
        )
        total_result = await db.execute(total_query)
        total_emails = total_result.scalar() or 0

        # Total threads
        threads_query = (
            select(func.count())
            .select_from(EmailThread)
            .where(EmailThread.pia_request_id == request_id)
        )
        threads_result = await db.execute(threads_query)
        total_threads = threads_result.scalar() or 0

        # Duplicates found
        dupes_query = (
            select(func.count())
            .select_from(EmailRecord)
            .where(
                and_(
                    EmailRecord.pia_request_id == request_id,
                    EmailRecord.is_duplicate == True,
                )
            )
        )
        dupes_result = await db.execute(dupes_query)
        duplicates = dupes_result.scalar() or 0

        # Responsive emails
        responsive_query = (
            select(func.count())
            .select_from(EmailRecord)
            .where(
                and_(
                    EmailRecord.pia_request_id == request_id,
                    EmailRecord.is_duplicate == False,
                    EmailRecord.is_responsive == True,
                )
            )
        )
        responsive_result = await db.execute(responsive_query)
        responsive = responsive_result.scalar() or 0

        # Calculate deduplication rate
        total_with_dupes = total_emails + duplicates
        dedup_rate = round((duplicates / total_with_dupes * 100) if total_with_dupes > 0 else 0, 1)

        return {
            "total_emails": total_emails,
            "total_threads": total_threads,
            "duplicates_removed": duplicates,
            "deduplication_rate": dedup_rate,
            "responsive_emails": responsive,
            "original_count": total_with_dupes,
        }


# Singleton instances
_email_service: Optional[EmailService] = None
_email_thread_service: Optional[EmailThreadService] = None


def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def get_email_thread_service() -> EmailThreadService:
    """Get or create the email thread service singleton."""
    global _email_thread_service
    if _email_thread_service is None:
        _email_thread_service = EmailThreadService()
    return _email_thread_service
