from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Date, Integer, Boolean,
    Enum as SQLEnum, ForeignKey, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PIARequestStatus(str, enum.Enum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    PENDING_DEPARTMENT_REVIEW = "pending_department_review"
    DEPARTMENT_REVIEW_COMPLETE = "department_review_complete"
    PENDING_LEADERSHIP_APPROVAL = "pending_leadership_approval"
    PENDING_AG_RULING = "pending_ag_ruling"
    AG_RULING_RECEIVED = "ag_ruling_received"
    READY_FOR_RELEASE = "ready_for_release"
    RELEASED = "released"
    CLOSED_NO_RECORDS = "closed_no_records"
    WITHDRAWN = "withdrawn"
    ON_HOLD = "on_hold"


class PIARequestPriority(str, enum.Enum):
    STANDARD = "standard"
    EXPEDITED = "expedited"
    URGENT = "urgent"


class PIARequest(Base):
    __tablename__ = "pia_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Request identification
    request_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )  # e.g., W721885-081925
    external_tracking_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Requester information
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requester_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requester_organization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requester_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request details
    description: Mapped[str] = mapped_column(Text)
    search_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_range_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    departments_involved: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Status and workflow
    status: Mapped[PIARequestStatus] = mapped_column(
        SQLEnum(PIARequestStatus), default=PIARequestStatus.RECEIVED, index=True
    )
    priority: Mapped[PIARequestPriority] = mapped_column(
        SQLEnum(PIARequestPriority), default=PIARequestPriority.STANDARD
    )
    assigned_to: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    client_department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Important dates (Texas PIA compliance)
    date_received: Mapped[datetime] = mapped_column(DateTime, index=True)
    date_acknowledged: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    response_deadline: Mapped[date] = mapped_column(Date, index=True)
    extension_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ag_submission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ag_ruling_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_completed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Document statistics
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    responsive_documents: Mapped[int] = mapped_column(Integer, default=0)
    redacted_documents: Mapped[int] = mapped_column(Integer, default=0)
    withheld_documents: Mapped[int] = mapped_column(Integer, default=0)

    # Processing status
    documents_retrieved: Mapped[bool] = mapped_column(Boolean, default=False)
    classification_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    department_review_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    leadership_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cost and fees
    estimated_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    fee_waived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes and comments
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    # Relationships
    assigned_to_user = relationship("User", back_populates="assigned_requests")
    documents = relationship("Document", back_populates="pia_request", cascade="all, delete-orphan")
    email_records = relationship("EmailRecord", back_populates="pia_request", cascade="all, delete-orphan")
    workflow_tasks = relationship("WorkflowTask", back_populates="pia_request", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="pia_request", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PIARequest {self.request_number}>"

    @property
    def days_until_deadline(self) -> int:
        """Calculate business days until response deadline."""
        from datetime import date
        today = date.today()
        if self.response_deadline < today:
            return -(today - self.response_deadline).days
        return (self.response_deadline - today).days

    @property
    def is_overdue(self) -> bool:
        """Check if the request is past its deadline."""
        from datetime import date
        return self.response_deadline < date.today() and self.status not in [
            PIARequestStatus.RELEASED,
            PIARequestStatus.CLOSED_NO_RECORDS,
            PIARequestStatus.WITHDRAWN
        ]

    @property
    def is_large_request(self) -> bool:
        """Check if this is a large request (5000+ pages)."""
        return self.total_pages >= 5000
