"""
Email management API endpoints.
"""
from typing import List, Optional
import re
import html

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field, field_validator

router = APIRouter()


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent injection attacks.
    Removes potentially dangerous characters while preserving search functionality.
    """
    if not query:
        return ""
    # HTML escape to prevent XSS
    query = html.escape(query)
    # Remove any SQL-like injection patterns
    query = re.sub(r'[;\'"\\]', '', query)
    # Limit length
    return query[:500]


class EmailResponse(BaseModel):
    """Email response schema."""
    id: int
    message_id: str
    subject: str
    sender_email: str
    sent_date: str
    has_attachments: bool
    is_duplicate: bool
    is_responsive: Optional[bool]
    ai_classification: Optional[str]
    thread_id: Optional[int]


class EmailThreadResponse(BaseModel):
    """Email thread response schema."""
    id: int
    thread_subject: str
    email_count: int
    participant_count: int
    first_email_date: str
    last_email_date: str
    total_attachments: int
    is_responsive: Optional[bool]
    review_strategy: str


@router.get("/", response_model=List[EmailResponse])
async def list_emails(
    request_id: int = Query(..., description="PIA request ID"),
    include_duplicates: bool = Query(False),
    classification: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
):
    """
    List emails for a PIA request.
    """
    return [
        {
            "id": 1,
            "message_id": "AAMkAGI2TG93AAA=",
            "subject": "RE: Project X Budget Approval",
            "sender_email": "john.doe@city.gov",
            "sent_date": "2025-02-15T10:30:00Z",
            "has_attachments": True,
            "is_duplicate": False,
            "is_responsive": True,
            "ai_classification": "responsive",
            "thread_id": 1,
        },
        {
            "id": 2,
            "message_id": "AAMkAGI2TG94AAA=",
            "subject": "FW: Project X Budget Approval",
            "sender_email": "jane.smith@city.gov",
            "sent_date": "2025-02-15T14:22:00Z",
            "has_attachments": False,
            "is_duplicate": True,
            "is_responsive": None,
            "ai_classification": None,
            "thread_id": 1,
        },
    ]


@router.get("/threads", response_model=List[EmailThreadResponse])
async def list_email_threads(
    request_id: int = Query(..., description="PIA request ID"),
    skip: int = 0,
    limit: int = 50,
):
    """
    List email threads for a PIA request.

    Threads are consolidated for efficient review - long email chains
    only require reviewing the final email which contains the full thread.
    """
    return [
        {
            "id": 1,
            "thread_subject": "Project X Budget Approval",
            "email_count": 8,
            "participant_count": 4,
            "first_email_date": "2025-02-10T09:00:00Z",
            "last_email_date": "2025-02-15T14:22:00Z",
            "total_attachments": 3,
            "is_responsive": True,
            "review_strategy": "review_final",
        },
        {
            "id": 2,
            "thread_subject": "Weekly Status Update",
            "email_count": 2,
            "participant_count": 2,
            "first_email_date": "2025-02-12T08:00:00Z",
            "last_email_date": "2025-02-12T16:30:00Z",
            "total_attachments": 0,
            "is_responsive": False,
            "review_strategy": "review_all",
        },
    ]


@router.get("/threads/{thread_id}")
async def get_email_thread(thread_id: int):
    """
    Get detailed email thread information.
    """
    return {
        "id": thread_id,
        "thread_subject": "Project X Budget Approval",
        "email_count": 8,
        "unique_participants": [
            "john.doe@city.gov",
            "jane.smith@city.gov",
            "bob.wilson@city.gov",
            "alice.johnson@city.gov",
        ],
        "first_email_date": "2025-02-10T09:00:00Z",
        "last_email_date": "2025-02-15T14:22:00Z",
        "total_attachments": 3,
        "review_strategy": "review_final",
        "review_email_count": 1,
        "emails_saved_from_review": 7,
        "classification": {
            "classification": "responsive",
            "confidence": 0.89,
            "exemptions": [],
        },
        "emails": [
            {
                "id": 1,
                "subject": "Project X Budget Approval",
                "sender": "john.doe@city.gov",
                "sent_date": "2025-02-10T09:00:00Z",
                "is_review_email": False,
            },
            # ... more emails
            {
                "id": 8,
                "subject": "RE: Project X Budget Approval",
                "sender": "jane.smith@city.gov",
                "sent_date": "2025-02-15T14:22:00Z",
                "is_review_email": True,  # This one contains the full thread
            },
        ],
    }


class EmailRetrievalRequest(BaseModel):
    """Request schema for email retrieval with validation."""
    request_id: int = Field(..., gt=0, description="PIA request ID")
    mailboxes: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of mailbox addresses to search"
    )
    search_query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string"
    )
    date_from: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("mailboxes")
    @classmethod
    def validate_mailboxes(cls, v: List[str]) -> List[str]:
        """Validate mailbox format."""
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for mailbox in v:
            if not email_pattern.match(mailbox):
                raise ValueError(f"Invalid email format: {mailbox}")
        return v

    @field_validator("search_query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize search query."""
        return sanitize_search_query(v)


@router.post("/retrieve")
async def retrieve_emails(request: EmailRetrievalRequest):
    """
    Retrieve emails from Microsoft 365 mailboxes.

    This will:
    1. Search specified mailboxes
    2. Retrieve matching emails
    3. Deduplicate and group into threads
    4. Classify for responsiveness
    """
    return {
        "request_id": request.request_id,
        "status": "retrieval_started",
        "mailboxes_searched": len(request.mailboxes),
        "search_query": request.search_query,
        "estimated_time": "5-10 minutes",
        "task_id": "email-retrieval-123",
    }


@router.get("/statistics")
async def get_email_statistics(request_id: int):
    """
    Get email processing statistics for a PIA request.
    """
    return {
        "request_id": request_id,
        "retrieval_stats": {
            "total_retrieved": 450,
            "mailboxes_searched": 5,
            "date_range": "2025-01-01 to 2025-03-31",
        },
        "deduplication_stats": {
            "total_input": 450,
            "unique_emails": 285,
            "duplicates_removed": 165,
            "reduction_percent": 36.7,
        },
        "thread_stats": {
            "total_threads": 42,
            "emails_for_review": 58,
            "emails_saved_from_review": 227,
            "efficiency_gain_percent": 79.6,
        },
        "classification_stats": {
            "responsive": 35,
            "non_responsive": 18,
            "needs_review": 5,
        },
        "time_saved_estimate": {
            "emails_not_requiring_individual_review": 227,
            "estimated_minutes_saved": 680,
            "estimated_hours_saved": 11.3,
        },
    }


@router.post("/threads/{thread_id}/classify")
async def classify_email_thread(thread_id: int):
    """
    Trigger AI classification for an email thread.
    """
    return {
        "thread_id": thread_id,
        "status": "classified",
        "result": {
            "classification": "responsive",
            "confidence": 0.91,
            "exemptions": [],
            "reasoning": "Thread discusses budget approval process which is responsive to the request.",
        }
    }


@router.post("/threads/{thread_id}/review")
async def submit_thread_review(
    thread_id: int,
    is_responsive: bool,
    classification: Optional[str] = None,
    review_notes: Optional[str] = None,
):
    """
    Submit human review for an email thread.
    """
    return {
        "thread_id": thread_id,
        "status": "reviewed",
        "is_responsive": is_responsive,
        "classification": classification,
        "reviewed_by": 1,
        "review_notes": review_notes,
    }
