from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Comprehensive audit logging for compliance and tracking."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Action details
    action: Mapped[str] = mapped_column(String(100), index=True)
    action_category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text)

    # Entity tracking
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Request association (optional)
    pia_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pia_requests.id"), nullable=True, index=True
    )

    # User tracking
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Change tracking
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Additional metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, index=True
    )

    # Relationships
    pia_request = relationship("PIARequest", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_email}>"


# Action categories for reference
class AuditAction:
    """Standard audit actions."""
    # Request lifecycle
    REQUEST_CREATED = "request_created"
    REQUEST_UPDATED = "request_updated"
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_ASSIGNED = "request_assigned"
    REQUEST_COMPLETED = "request_completed"

    # Document actions
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_CLASSIFIED = "document_classified"
    DOCUMENT_REVIEWED = "document_reviewed"
    DOCUMENT_REDACTED = "document_redacted"
    DOCUMENT_RELEASED = "document_released"
    DOCUMENT_WITHHELD = "document_withheld"

    # Email actions
    EMAIL_RETRIEVED = "email_retrieved"
    EMAIL_CLASSIFIED = "email_classified"
    THREAD_DEDUPLICATED = "thread_deduplicated"

    # Workflow actions
    WORKFLOW_STARTED = "workflow_started"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Review actions
    DEPARTMENT_REVIEW_SENT = "department_review_sent"
    DEPARTMENT_REVIEW_COMPLETED = "department_review_completed"
    LEADERSHIP_APPROVAL_REQUESTED = "leadership_approval_requested"
    LEADERSHIP_APPROVED = "leadership_approved"

    # AG actions
    AG_RULING_REQUESTED = "ag_ruling_requested"
    AG_RULING_RECEIVED = "ag_ruling_received"

    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"


class AuditCategory:
    """Standard audit categories."""
    REQUEST = "request"
    DOCUMENT = "document"
    EMAIL = "email"
    WORKFLOW = "workflow"
    REVIEW = "review"
    LEGAL = "legal"
    USER = "user"
    SYSTEM = "system"
