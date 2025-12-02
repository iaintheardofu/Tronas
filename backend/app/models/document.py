from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Integer, Float, Boolean,
    Enum as SQLEnum, ForeignKey, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentType(str, enum.Enum):
    EMAIL = "email"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    TEXT = "text"
    MSG_FILE = "msg_file"
    EML_FILE = "eml_file"
    OTHER = "other"


class DocumentClassificationCategory(str, enum.Enum):
    RESPONSIVE = "responsive"
    NON_RESPONSIVE = "non_responsive"
    ATTORNEY_CLIENT_PRIVILEGE = "attorney_client_privilege"
    LEGISLATIVE_PRIVILEGE = "legislative_privilege"
    LAW_ENFORCEMENT = "law_enforcement"
    MEDICAL_INFORMATION = "medical_information"
    PERSONNEL_RECORDS = "personnel_records"
    TRADE_SECRETS = "trade_secrets"
    DELIBERATIVE_PROCESS = "deliberative_process"
    PENDING_LITIGATION = "pending_litigation"
    PERSONAL_INFORMATION = "personal_information"
    NEEDS_REVIEW = "needs_review"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CLASSIFIED = "classified"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REDACTION_NEEDED = "redaction_needed"
    REDACTED = "redacted"
    RELEASED = "released"
    WITHHELD = "withheld"
    ERROR = "error"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Request association
    pia_request_id: Mapped[int] = mapped_column(
        ForeignKey("pia_requests.id"), index=True
    )

    # File information
    filename: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_size: Mapped[int] = mapped_column(Integer)  # bytes
    file_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256
    mime_type: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType))

    # Document content
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_extraction_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source information (for Microsoft 365 integration)
    source_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_site: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_library: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Metadata from source
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Classification
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, index=True
    )
    ai_classification: Mapped[Optional[DocumentClassificationCategory]] = mapped_column(
        SQLEnum(DocumentClassificationCategory), nullable=True
    )
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_classification: Mapped[Optional[DocumentClassificationCategory]] = mapped_column(
        SQLEnum(DocumentClassificationCategory), nullable=True
    )

    # Classification reasoning
    classification_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exemption_codes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Review status
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Redaction
    redaction_required: Mapped[bool] = mapped_column(Boolean, default=False)
    redaction_areas: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    redacted_file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Deduplication
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    pia_request = relationship("PIARequest", back_populates="documents")
    labels = relationship("DocumentLabel", back_populates="document", cascade="all, delete-orphan")
    classifications = relationship(
        "DocumentClassification", back_populates="document", cascade="all, delete-orphan"
    )
    duplicates = relationship("Document", remote_side=[id])

    __table_args__ = (
        Index("ix_documents_request_status", "pia_request_id", "status"),
        Index("ix_documents_classification", "ai_classification"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.filename}>"


class DocumentLabel(Base):
    """Labels applied to documents for quick identification during review."""
    __tablename__ = "document_labels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    label: Mapped[str] = mapped_column(String(100), index=True)
    label_type: Mapped[str] = mapped_column(String(50))  # "exemption", "category", "custom"
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    applied_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Position for visual display (for PDF highlighting)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="labels")


class DocumentClassification(Base):
    """Detailed classification records including AI analysis."""
    __tablename__ = "document_classifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    classification_category: Mapped[DocumentClassificationCategory] = mapped_column(
        SQLEnum(DocumentClassificationCategory)
    )
    confidence_score: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)

    # Model information
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Texas PIA exemption references
    exemption_section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    exemption_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    document = relationship("Document", back_populates="classifications")

    __table_args__ = (
        Index("ix_doc_classifications_doc_category", "document_id", "classification_category"),
    )
