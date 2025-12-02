from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Integer, Boolean,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EmailRecord(Base):
    """Email records retrieved from Microsoft 365 for PIA requests."""
    __tablename__ = "email_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Request association
    pia_request_id: Mapped[int] = mapped_column(
        ForeignKey("pia_requests.id"), index=True
    )

    # Email identification
    message_id: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    internet_message_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Thread information
    thread_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_threads.id"), nullable=True
    )
    is_thread_root: Mapped[bool] = mapped_column(Boolean, default=False)
    thread_position: Mapped[int] = mapped_column(Integer, default=0)

    # Email metadata
    subject: Mapped[str] = mapped_column(String(1000))
    sender_email: Mapped[str] = mapped_column(String(255), index=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_to: Mapped[List[str]] = mapped_column(JSON)  # List of email addresses
    recipient_cc: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    recipient_bcc: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Dates
    sent_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    received_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Content
    body_preview: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Source information
    mailbox: Mapped[str] = mapped_column(String(255))
    folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Categories and importance
    categories: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    importance: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False)

    # Deduplication
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_records.id"), nullable=True
    )

    # Classification
    is_responsive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ai_classification: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    classification_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Review status
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    # Relationships
    pia_request = relationship("PIARequest", back_populates="email_records")
    thread = relationship("EmailThread", back_populates="emails")
    attachments = relationship(
        "Document",
        primaryjoin="EmailRecord.id == foreign(Document.source_id)",
        viewonly=True
    )

    __table_args__ = (
        Index("ix_email_records_request_sender", "pia_request_id", "sender_email"),
        Index("ix_email_records_conversation", "conversation_id", "sent_date"),
    )

    def __repr__(self) -> str:
        return f"<EmailRecord {self.subject[:50]}>"


class EmailThread(Base):
    """Email thread grouping for deduplication and consolidated review."""
    __tablename__ = "email_threads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Request association
    pia_request_id: Mapped[int] = mapped_column(
        ForeignKey("pia_requests.id"), index=True
    )

    # Thread identification
    conversation_id: Mapped[str] = mapped_column(String(500), index=True)
    thread_subject: Mapped[str] = mapped_column(String(1000))

    # Thread statistics
    email_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_participants: Mapped[List[str]] = mapped_column(JSON)
    first_email_date: Mapped[datetime] = mapped_column(DateTime)
    last_email_date: Mapped[datetime] = mapped_column(DateTime)

    # Content summary
    thread_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_attachments: Mapped[int] = mapped_column(Integer, default=0)

    # Classification (applied to entire thread)
    thread_classification: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_responsive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Review status
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    # Relationships
    emails = relationship("EmailRecord", back_populates="thread")

    def __repr__(self) -> str:
        return f"<EmailThread {self.thread_subject[:50]} ({self.email_count} emails)>"
