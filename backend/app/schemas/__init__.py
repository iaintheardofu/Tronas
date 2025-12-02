from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


class PIARequestStatus(str, Enum):
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


class PIARequestPriority(str, Enum):
    STANDARD = "standard"
    EXPEDITED = "expedited"
    URGENT = "urgent"


class UserRole(str, Enum):
    ADMIN = "admin"
    LEGAL_REVIEWER = "legal_reviewer"
    RECORDS_LIAISON = "records_liaison"
    DEPARTMENT_REVIEWER = "department_reviewer"
    VIEWER = "viewer"


class DocumentClassificationCategory(str, Enum):
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


class DocumentStatus(str, Enum):
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


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TaskType(str, Enum):
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


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    department: Optional[str] = None
    role: UserRole = UserRole.VIEWER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    department: Optional[str]
    role: UserRole
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PIARequestCreate(BaseModel):
    requester_name: str = Field(..., min_length=1, max_length=255)
    requester_email: Optional[EmailStr] = None
    requester_phone: Optional[str] = None
    requester_organization: Optional[str] = None
    requester_address: Optional[str] = None
    description: str = Field(..., min_length=1)
    search_terms: Optional[str] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    departments_involved: Optional[List[str]] = None
    priority: PIARequestPriority = PIARequestPriority.STANDARD


class PIARequestUpdate(BaseModel):
    requester_name: Optional[str] = None
    requester_email: Optional[EmailStr] = None
    requester_phone: Optional[str] = None
    requester_organization: Optional[str] = None
    description: Optional[str] = None
    search_terms: Optional[str] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    departments_involved: Optional[List[str]] = None
    status: Optional[PIARequestStatus] = None
    priority: Optional[PIARequestPriority] = None
    assigned_to: Optional[int] = None
    internal_notes: Optional[str] = None
    response_letter: Optional[str] = None


class PIARequestResponse(BaseModel):
    id: int
    request_number: str
    requester_name: str
    requester_email: Optional[str]
    requester_phone: Optional[str]
    requester_organization: Optional[str]
    description: str
    search_terms: Optional[str]
    date_range_start: Optional[date]
    date_range_end: Optional[date]
    departments_involved: Optional[List[str]]
    status: PIARequestStatus
    priority: PIARequestPriority
    assigned_to: Optional[int]
    client_department: Optional[str]
    date_received: datetime
    response_deadline: date
    extension_deadline: Optional[date]
    ag_submission_date: Optional[date]
    ag_ruling_deadline: Optional[date]
    date_completed: Optional[datetime]
    total_documents: int
    total_pages: int
    responsive_documents: int
    redacted_documents: int
    withheld_documents: int
    documents_retrieved: bool
    classification_complete: bool
    department_review_complete: bool
    leadership_approved: bool
    estimated_cost: Optional[float]
    actual_cost: Optional[float]
    fee_waived: bool
    internal_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_hash: str
    mime_type: str
    source_system: Optional[str] = None
    source_id: Optional[str] = None
    author: Optional[str] = None


class DocumentClassificationResult(BaseModel):
    classification_category: DocumentClassificationCategory
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    exemption_codes: Optional[List[str]] = None
    redaction_required: bool = False


class DocumentResponse(BaseModel):
    id: int
    pia_request_id: int
    filename: str
    original_filename: str
    file_size: int
    file_hash: str
    mime_type: str
    page_count: int
    status: DocumentStatus
    ai_classification: Optional[DocumentClassificationCategory]
    ai_confidence_score: Optional[float]
    final_classification: Optional[DocumentClassificationCategory]
    classification_reasoning: Optional[str]
    exemption_codes: Optional[List[str]]
    redaction_required: bool
    is_duplicate: bool
    duplicate_of_id: Optional[int]
    reviewed: bool = Field(default=False, alias="reviewed")
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @property
    def reviewed(self) -> bool:
        return self.reviewed_at is not None


class EmailRecordResponse(BaseModel):
    id: int
    pia_request_id: int
    message_id: str
    conversation_id: Optional[str]
    thread_id: Optional[int]
    subject: str
    sender_email: str
    sender_name: Optional[str]
    recipient_to: List[str]
    recipient_cc: Optional[List[str]]
    recipient_bcc: Optional[List[str]]
    sent_date: datetime
    body_preview: Optional[str]
    has_attachments: bool
    attachment_count: int
    mailbox: str
    folder: Optional[str]
    is_duplicate: bool
    duplicate_of_id: Optional[int]
    is_responsive: Optional[bool]
    ai_classification: Optional[str]
    classification_confidence: Optional[float]
    reviewed: bool
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailThreadResponse(BaseModel):
    id: int
    pia_request_id: int
    conversation_id: str
    thread_subject: str
    email_count: int
    unique_participants: List[str]
    first_email_date: datetime
    last_email_date: datetime
    thread_summary: Optional[str]
    total_attachments: int
    thread_classification: Optional[str]
    is_responsive: Optional[bool]
    reviewed: bool
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowTaskResponse(BaseModel):
    id: int
    pia_request_id: int
    task_type: TaskType
    task_name: str
    task_description: Optional[str]
    sequence_order: int
    status: WorkflowStatus
    progress_percent: int
    assigned_to: Optional[int]
    assigned_role: Optional[str]
    scheduled_start: Optional[datetime]
    deadline: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    is_automated: bool
    retry_count: int
    max_retries: int
    result_data: Optional[dict]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowStatusResponse(BaseModel):
    request_id: int
    request_number: str
    overall_status: PIARequestStatus
    tasks: List[WorkflowTaskResponse]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percent: int


class DashboardOverview(BaseModel):
    total_requests: int
    active_requests: int
    overdue_requests: int
    requests_this_week: int
    requests_this_month: int
    avg_processing_time_days: float
    total_documents_processed: int
    total_pages_processed: int
    requests_by_status: dict[str, int]
    requests_by_priority: dict[str, int]
    upcoming_deadlines: List[dict]


class UrgentItem(BaseModel):
    request_id: int
    request_number: str
    requester_name: str
    description: str
    status: PIARequestStatus
    priority: PIARequestPriority
    response_deadline: date
    days_until_deadline: int
    is_overdue: bool


class UrgentItems(BaseModel):
    overdue: List[UrgentItem]
    due_within_3_days: List[UrgentItem]
    due_within_7_days: List[UrgentItem]
    pending_approvals: List[UrgentItem]


class AuditLogCreate(BaseModel):
    action: str
    action_category: str
    description: str
    entity_type: str
    entity_id: Optional[int] = None
    pia_request_id: Optional[int] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    metadata: Optional[dict] = None


class AuditLogResponse(BaseModel):
    id: int
    action: str
    action_category: str
    description: str
    entity_type: str
    entity_id: Optional[int]
    pia_request_id: Optional[int]
    user_id: Optional[int]
    user_email: Optional[str]
    old_values: Optional[dict]
    new_values: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "PIARequestStatus",
    "PIARequestPriority",
    "UserRole",
    "DocumentClassificationCategory",
    "DocumentStatus",
    "WorkflowStatus",
    "TaskType",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "PIARequestCreate",
    "PIARequestUpdate",
    "PIARequestResponse",
    "DocumentCreate",
    "DocumentClassificationResult",
    "DocumentResponse",
    "EmailRecordResponse",
    "EmailThreadResponse",
    "WorkflowTaskResponse",
    "WorkflowStatusResponse",
    "DashboardOverview",
    "UrgentItem",
    "UrgentItems",
    "AuditLogCreate",
    "AuditLogResponse",
]
