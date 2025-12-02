"""
PIA Request API endpoints with real database operations.
"""
from typing import List, Optional
from datetime import date, datetime
import re
import html

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.crud.request_service import get_request_service
from app.services.crud.workflow_service import get_workflow_service
from app.services.crud.audit_service import get_audit_service
from app.services.workflow.deadline_manager import get_deadline_manager
from app.models.pia_request import PIARequestStatus, PIARequestPriority

router = APIRouter()


def sanitize_text_input(text: str, max_length: int = 5000) -> str:
    """Sanitize text input to prevent XSS and injection attacks."""
    if not text:
        return ""
    text = html.escape(text)
    text = text.replace('\x00', '')
    return text[:max_length]


# Request schemas
class PIARequestCreate(BaseModel):
    """Schema for creating a new PIA request with input validation."""
    request_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9\-_]+$",
        description="Request tracking number"
    )
    requester_name: str = Field(..., min_length=1, max_length=255)
    requester_email: Optional[EmailStr] = None
    requester_phone: Optional[str] = Field(
        None,
        max_length=50,
        pattern=r"^[\d\s\-\(\)\+\.ext]+$"
    )
    requester_organization: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=1, max_length=10000)
    search_terms: Optional[str] = Field(None, max_length=1000)
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    departments_involved: Optional[List[str]] = Field(None, max_length=20)
    date_received: date
    priority: str = Field("standard", pattern=r"^(standard|expedited|urgent)$")

    @field_validator("description", "search_terms", "requester_name", "requester_organization", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v):
        if v is None:
            return v
        return sanitize_text_input(str(v))

    @field_validator("departments_involved", mode="before")
    @classmethod
    def validate_departments(cls, v):
        if v is None:
            return v
        return [sanitize_text_input(str(dept), 100) for dept in v]

    @field_validator("date_range_end")
    @classmethod
    def validate_date_range(cls, v, info):
        if v and info.data.get("date_range_start"):
            if v < info.data["date_range_start"]:
                raise ValueError("date_range_end must be after date_range_start")
        return v


class PIARequestUpdate(BaseModel):
    """Schema for updating a PIA request."""
    requester_name: Optional[str] = Field(None, max_length=255)
    requester_email: Optional[EmailStr] = None
    requester_phone: Optional[str] = Field(None, max_length=50)
    requester_organization: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=10000)
    search_terms: Optional[str] = Field(None, max_length=1000)
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    departments_involved: Optional[List[str]] = None
    priority: Optional[str] = Field(None, pattern=r"^(standard|expedited|urgent)$")
    status: Optional[str] = None
    internal_notes: Optional[str] = Field(None, max_length=10000)


class PIARequestResponse(BaseModel):
    """Schema for PIA request response."""
    id: int
    request_number: str
    requester_name: str
    description: str
    status: str
    priority: str
    date_received: datetime
    response_deadline: date
    days_until_deadline: int
    is_overdue: bool
    total_documents: int
    total_pages: int
    classification_complete: bool

    class Config:
        from_attributes = True


class PIARequestDetail(BaseModel):
    """Detailed PIA request response."""
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
    status: str
    priority: str
    date_received: datetime
    response_deadline: date
    extension_deadline: Optional[date]
    ag_submission_date: Optional[date]
    ag_ruling_deadline: Optional[date]
    days_until_deadline: int
    is_overdue: bool
    total_documents: int
    total_pages: int
    responsive_documents: int
    redacted_documents: int
    withheld_documents: int
    documents_retrieved: bool
    classification_complete: bool
    department_review_complete: bool
    leadership_approved: bool
    assigned_to: Optional[int]
    internal_notes: Optional[str]
    deadline_status: dict

    class Config:
        from_attributes = True


def request_to_response(request, deadline_manager) -> dict:
    """Convert a PIARequest model to response dict."""
    deadline_status = deadline_manager.get_deadline_status(request.response_deadline)
    return {
        "id": request.id,
        "request_number": request.request_number,
        "requester_name": request.requester_name,
        "description": request.description,
        "status": request.status.value if hasattr(request.status, 'value') else request.status,
        "priority": request.priority.value if hasattr(request.priority, 'value') else request.priority,
        "date_received": request.date_received,
        "response_deadline": request.response_deadline,
        "days_until_deadline": deadline_status["business_days_remaining"],
        "is_overdue": deadline_status["is_overdue"],
        "total_documents": request.total_documents,
        "total_pages": request.total_pages,
        "classification_complete": request.classification_complete,
    }


def request_to_detail(request, deadline_manager) -> dict:
    """Convert a PIARequest model to detailed response dict."""
    deadline_status = deadline_manager.get_deadline_status(request.response_deadline)
    return {
        "id": request.id,
        "request_number": request.request_number,
        "requester_name": request.requester_name,
        "requester_email": request.requester_email,
        "requester_phone": request.requester_phone,
        "requester_organization": request.requester_organization,
        "description": request.description,
        "search_terms": request.search_terms,
        "date_range_start": request.date_range_start,
        "date_range_end": request.date_range_end,
        "departments_involved": request.departments_involved,
        "status": request.status.value if hasattr(request.status, 'value') else request.status,
        "priority": request.priority.value if hasattr(request.priority, 'value') else request.priority,
        "date_received": request.date_received,
        "response_deadline": request.response_deadline,
        "extension_deadline": request.extension_deadline,
        "ag_submission_date": request.ag_submission_date,
        "ag_ruling_deadline": request.ag_ruling_deadline,
        "days_until_deadline": deadline_status["business_days_remaining"],
        "is_overdue": deadline_status["is_overdue"],
        "total_documents": request.total_documents,
        "total_pages": request.total_pages,
        "responsive_documents": request.responsive_documents,
        "redacted_documents": request.redacted_documents,
        "withheld_documents": request.withheld_documents,
        "documents_retrieved": request.documents_retrieved,
        "classification_complete": request.classification_complete,
        "department_review_complete": request.department_review_complete,
        "leadership_approved": request.leadership_approved,
        "assigned_to": request.assigned_to,
        "internal_notes": request.internal_notes,
        "deadline_status": deadline_status,
    }


@router.get("/", response_model=List[PIARequestResponse])
async def list_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    overdue: Optional[bool] = Query(None, description="Filter overdue requests"),
    search: Optional[str] = Query(None, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all PIA requests with optional filtering.
    """
    request_service = get_request_service()
    deadline_manager = get_deadline_manager()

    if search:
        requests = await request_service.search_requests(db, search, skip, limit)
    elif overdue:
        requests = await request_service.get_overdue_requests(db)
    elif status:
        try:
            status_enum = PIARequestStatus(status)
            requests = await request_service.get_requests_by_status(db, status_enum, skip, limit)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        filters = {}
        if priority:
            try:
                filters["priority"] = PIARequestPriority(priority)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

        requests = await request_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters=filters if filters else None,
            order_by=request_service.model.date_received.desc(),
        )

    return [request_to_response(r, deadline_manager) for r in requests]


@router.post("/", response_model=PIARequestDetail, status_code=201)
async def create_request(
    request_data: PIARequestCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new PIA request.
    """
    request_service = get_request_service()
    workflow_service = get_workflow_service()
    audit_service = get_audit_service()
    deadline_manager = get_deadline_manager()

    # Check if request number already exists
    existing = await request_service.get_by_field(db, "request_number", request_data.request_number)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Request number {request_data.request_number} already exists"
        )

    # Create request
    request_dict = request_data.model_dump()
    if request_dict.get("priority"):
        request_dict["priority"] = PIARequestPriority(request_dict["priority"])

    new_request = await request_service.create_request(db, request_dict)

    # Initialize workflow
    await workflow_service.initialize_workflow(db, new_request.id)

    # Log creation
    await audit_service.log_request_created(
        db=db,
        request_id=new_request.id,
        user_id=1,  # Would come from auth
        request_data={"request_number": new_request.request_number},
        ip_address=http_request.client.host if http_request.client else None,
    )

    await db.commit()

    return request_to_detail(new_request, deadline_manager)


@router.get("/{request_id}", response_model=PIARequestDetail)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific PIA request.
    """
    request_service = get_request_service()
    deadline_manager = get_deadline_manager()

    request = await request_service.get_request_with_relations(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return request_to_detail(request, deadline_manager)


@router.patch("/{request_id}", response_model=PIARequestDetail)
async def update_request(
    request_id: int,
    update_data: PIARequestUpdate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a PIA request.
    """
    request_service = get_request_service()
    audit_service = get_audit_service()
    deadline_manager = get_deadline_manager()

    existing = await request_service.get(db, request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Request not found")

    old_values = {"status": existing.status.value if hasattr(existing.status, 'value') else existing.status}

    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle status change
    if update_dict.get("status"):
        try:
            update_dict["status"] = PIARequestStatus(update_dict["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

    # Handle priority change
    if update_dict.get("priority"):
        try:
            update_dict["priority"] = PIARequestPriority(update_dict["priority"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority")

    updated = await request_service.update(db, request_id, update_dict)

    # Log update
    await audit_service.log_request_updated(
        db=db,
        request_id=request_id,
        user_id=1,
        old_values=old_values,
        new_values=update_dict,
        ip_address=http_request.client.host if http_request.client else None,
    )

    await db.commit()

    return request_to_detail(updated, deadline_manager)


@router.post("/{request_id}/start-processing")
async def start_processing(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Start automated processing for a PIA request.
    """
    request_service = get_request_service()
    workflow_service = get_workflow_service()
    audit_service = get_audit_service()

    request = await request_service.get(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Update status to in progress
    await request_service.update_request_status(db, request_id, PIARequestStatus.IN_PROGRESS)

    # Get workflow tasks
    tasks = await workflow_service.get_tasks_for_request(db, request_id)

    # Start first runnable tasks
    runnable = await workflow_service.get_next_runnable_tasks(db, request_id)
    started_tasks = []

    for task in runnable:
        if task.is_automated:
            await workflow_service.start_task(db, task.id)
            started_tasks.append(task.task_name)

    # Log event
    await audit_service.log_workflow_event(
        db=db,
        request_id=request_id,
        task_type="processing",
        event="started",
        details=f"Started automated processing with {len(started_tasks)} tasks",
    )

    await db.commit()

    return {
        "request_id": request_id,
        "status": "processing_started",
        "message": "Automated processing initiated",
        "tasks_created": len(tasks),
        "tasks_started": started_tasks,
        "next_steps": [
            "Document retrieval in progress",
            "Email retrieval in progress",
        ]
    }


@router.get("/{request_id}/deadlines")
async def get_request_deadlines(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all deadline information for a request.
    """
    request_service = get_request_service()
    deadline_manager = get_deadline_manager()

    request = await request_service.get(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Get date received
    date_received = request.date_received
    if isinstance(date_received, datetime):
        date_received = date_received.date()

    return deadline_manager.get_all_deadlines(date_received)


@router.post("/{request_id}/request-extension")
async def request_extension(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a 10-day extension for the response deadline.
    """
    request_service = get_request_service()
    audit_service = get_audit_service()
    deadline_manager = get_deadline_manager()

    request = await request_service.get(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check if extension already granted
    if request.extension_deadline:
        raise HTTPException(status_code=400, detail="Extension already granted")

    original_deadline = request.response_deadline
    updated = await request_service.request_extension(db, request_id)

    # Log event
    await audit_service.log_workflow_event(
        db=db,
        request_id=request_id,
        task_type="deadline",
        event="extension_requested",
        details=f"Extended deadline from {original_deadline} to {updated.response_deadline}",
    )

    await db.commit()

    return {
        "request_id": request_id,
        "original_deadline": original_deadline.isoformat(),
        "new_deadline": updated.response_deadline.isoformat(),
        "extension_days": 10,
        "notice_required": True,
        "notice_template": "Extension notice must be sent to requester within 10 days of original request.",
    }


@router.post("/{request_id}/request-ag-ruling")
async def request_ag_ruling(
    request_id: int,
    exemptions: List[str],
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate an Attorney General ruling request.
    """
    request_service = get_request_service()
    audit_service = get_audit_service()
    deadline_manager = get_deadline_manager()

    request = await request_service.get(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check if AG ruling already requested
    if request.ag_submission_date:
        raise HTTPException(status_code=400, detail="AG ruling already requested")

    updated = await request_service.initiate_ag_ruling(db, request_id, exemptions)

    # Log event
    await audit_service.log_workflow_event(
        db=db,
        request_id=request_id,
        task_type="ag_ruling",
        event="requested",
        details=f"AG ruling requested for exemptions: {', '.join(exemptions)}",
    )

    await db.commit()

    return {
        "request_id": request_id,
        "ag_submission_date": updated.ag_submission_date.isoformat(),
        "ag_ruling_deadline": updated.ag_ruling_deadline.isoformat(),
        "exemptions_cited": exemptions,
        "status": "ag_ruling_requested",
        "next_steps": [
            "Prepare brief for AG",
            "Submit documentation within 15 days",
            "Await AG decision (up to 45 days)",
        ]
    }


@router.get("/{request_id}/workflow-status")
async def get_workflow_status(
    request_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get workflow status for a request.
    """
    request_service = get_request_service()
    workflow_service = get_workflow_service()

    request = await request_service.get(db, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return await workflow_service.get_workflow_status(db, request_id)
