from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Integer,
    Enum as SQLEnum, ForeignKey, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TaskType(str, enum.Enum):
    DOCUMENT_RETRIEVAL = "document_retrieval"
    EMAIL_RETRIEVAL = "email_retrieval"
    TEXT_EXTRACTION = "text_extraction"
    AI_CLASSIFICATION = "ai_classification"
    DEDUPLICATION = "deduplication"
    DEPARTMENT_REVIEW = "department_review"
    LEADERSHIP_APPROVAL = "leadership_approval"
    REDACTION_PREP = "redaction_prep"
    AG_SUBMISSION = "ag_submission"
    FINAL_REVIEW = "final_review"
    RESPONSE_GENERATION = "response_generation"
    NOTIFICATION = "notification"


class WorkflowTask(Base):
    """Individual workflow tasks for PIA request processing."""
    __tablename__ = "workflow_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Request association
    pia_request_id: Mapped[int] = mapped_column(
        ForeignKey("pia_requests.id"), index=True
    )

    # Task identification
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType))
    task_name: Mapped[str] = mapped_column(String(255))
    task_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow ordering
    sequence_order: Mapped[int] = mapped_column(Integer, default=0)
    depends_on: Mapped[Optional[List[int]]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[WorkflowStatus] = mapped_column(
        SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING, index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)

    # Assignment
    assigned_to: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    assigned_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timing
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Execution details
    is_automated: Mapped[bool] = mapped_column(default=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Results and errors
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Configuration
    task_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    # Relationships
    pia_request = relationship("PIARequest", back_populates="workflow_tasks")

    __table_args__ = (
        Index("ix_workflow_tasks_request_status", "pia_request_id", "status"),
        Index("ix_workflow_tasks_type", "task_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowTask {self.task_name} ({self.status.value})>"

    @property
    def is_ready(self) -> bool:
        """Check if task dependencies are met."""
        if not self.depends_on:
            return True
        # This would need to be checked against actual task statuses
        return False

    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate task duration if completed."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class WorkflowTemplate(Base):
    """Reusable workflow templates for different request types."""
    __tablename__ = "workflow_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Template configuration
    tasks: Mapped[List[dict]] = mapped_column(JSON)
    """
    Example tasks structure:
    [
        {
            "task_type": "document_retrieval",
            "task_name": "Retrieve Documents from SharePoint",
            "sequence_order": 1,
            "is_automated": true,
            "config": {"sources": ["sharepoint", "onedrive"]}
        },
        {
            "task_type": "ai_classification",
            "task_name": "AI Document Classification",
            "sequence_order": 2,
            "depends_on": [1],
            "is_automated": true
        }
    ]
    """

    # Timing defaults
    default_deadline_days: Mapped[int] = mapped_column(Integer, default=10)

    # Metadata
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    def __repr__(self) -> str:
        return f"<WorkflowTemplate {self.name}>"
