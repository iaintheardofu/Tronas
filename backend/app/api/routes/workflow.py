"""
Workflow management API endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class WorkflowTaskResponse(BaseModel):
    """Workflow task response schema."""
    id: int
    task_type: str
    task_name: str
    status: str
    sequence_order: int
    is_automated: bool
    assigned_role: Optional[str]
    progress_percent: int


@router.get("/tasks")
async def list_workflow_tasks(
    request_id: int = Query(..., description="PIA request ID"),
):
    """
    List all workflow tasks for a PIA request.
    """
    return {
        "request_id": request_id,
        "total_tasks": 11,
        "completed_tasks": 6,
        "in_progress_tasks": 1,
        "pending_tasks": 4,
        "overall_progress": 55,
        "tasks": [
            {
                "id": 1,
                "task_type": "document_retrieval",
                "task_name": "Retrieve Documents from M365",
                "status": "completed",
                "sequence_order": 1,
                "is_automated": True,
                "assigned_role": None,
                "progress_percent": 100,
                "completed_at": "2025-08-20T10:30:00Z",
                "duration_seconds": 345,
            },
            {
                "id": 2,
                "task_type": "email_retrieval",
                "task_name": "Retrieve Emails from Outlook",
                "status": "completed",
                "sequence_order": 2,
                "is_automated": True,
                "assigned_role": None,
                "progress_percent": 100,
                "completed_at": "2025-08-20T10:45:00Z",
            },
            {
                "id": 3,
                "task_type": "text_extraction",
                "task_name": "Extract Text from Documents",
                "status": "completed",
                "sequence_order": 3,
                "is_automated": True,
                "progress_percent": 100,
            },
            {
                "id": 4,
                "task_type": "deduplication",
                "task_name": "Deduplicate and Group Emails",
                "status": "completed",
                "sequence_order": 4,
                "is_automated": True,
                "progress_percent": 100,
            },
            {
                "id": 5,
                "task_type": "ai_classification",
                "task_name": "AI Document Classification",
                "status": "completed",
                "sequence_order": 5,
                "is_automated": True,
                "progress_percent": 100,
            },
            {
                "id": 6,
                "task_type": "redaction_prep",
                "task_name": "Prepare Redaction Areas",
                "status": "completed",
                "sequence_order": 6,
                "is_automated": True,
                "progress_percent": 100,
            },
            {
                "id": 7,
                "task_type": "department_review",
                "task_name": "Department Review",
                "status": "in_progress",
                "sequence_order": 7,
                "is_automated": False,
                "assigned_role": "department_reviewer",
                "progress_percent": 65,
            },
            {
                "id": 8,
                "task_type": "leadership_approval",
                "task_name": "Leadership Approval",
                "status": "pending",
                "sequence_order": 8,
                "is_automated": False,
                "assigned_role": "legal_reviewer",
                "progress_percent": 0,
            },
            {
                "id": 9,
                "task_type": "final_review",
                "task_name": "Final Review and Release",
                "status": "pending",
                "sequence_order": 9,
                "is_automated": False,
                "assigned_role": "records_liaison",
                "progress_percent": 0,
            },
            {
                "id": 10,
                "task_type": "response_generation",
                "task_name": "Generate Response Letter",
                "status": "pending",
                "sequence_order": 10,
                "is_automated": True,
                "progress_percent": 0,
            },
            {
                "id": 11,
                "task_type": "notification",
                "task_name": "Send Notifications",
                "status": "pending",
                "sequence_order": 11,
                "is_automated": True,
                "progress_percent": 0,
            },
        ],
    }


@router.get("/status")
async def get_workflow_status(request_id: int):
    """
    Get overall workflow status summary.
    """
    return {
        "request_id": request_id,
        "overall_status": "in_progress",
        "overall_progress": 55,
        "phases": {
            "document_retrieval": "completed",
            "classification": "completed",
            "review": "in_progress",
            "release": "pending",
        },
        "next_action": {
            "task": "Department Review",
            "assigned_to": "department_reviewer",
            "documents_pending_review": 15,
        },
        "timeline": {
            "started": "2025-08-20T09:00:00Z",
            "estimated_completion": "2025-08-28T17:00:00Z",
            "deadline": "2025-09-02",
            "on_track": True,
        },
        "automation_stats": {
            "automated_tasks_completed": 6,
            "manual_tasks_completed": 0,
            "manual_tasks_remaining": 3,
            "time_saved_hours": 8.5,
        },
    }


@router.post("/tasks/{task_id}/complete")
async def complete_workflow_task(
    task_id: int,
    notes: Optional[str] = None,
):
    """
    Mark a manual workflow task as completed.
    """
    return {
        "task_id": task_id,
        "status": "completed",
        "completed_by": 1,
        "completed_at": "2025-08-25T14:30:00Z",
        "notes": notes,
        "next_task": {
            "id": 8,
            "task_name": "Leadership Approval",
            "assigned_role": "legal_reviewer",
        },
    }


@router.post("/tasks/{task_id}/assign")
async def assign_workflow_task(
    task_id: int,
    user_id: int,
):
    """
    Assign a task to a specific user.
    """
    return {
        "task_id": task_id,
        "assigned_to": user_id,
        "status": "assigned",
        "notification_sent": True,
    }


@router.post("/tasks/{task_id}/retry")
async def retry_failed_task(task_id: int):
    """
    Retry a failed automated task.
    """
    return {
        "task_id": task_id,
        "status": "retrying",
        "retry_count": 2,
        "max_retries": 3,
    }


@router.get("/timeline")
async def get_workflow_timeline(request_id: int):
    """
    Get workflow execution timeline for visualization.
    """
    return {
        "request_id": request_id,
        "timeline": [
            {
                "date": "2025-08-19",
                "events": [
                    {"time": "14:30", "event": "Request received", "type": "milestone"},
                ]
            },
            {
                "date": "2025-08-20",
                "events": [
                    {"time": "09:00", "event": "Processing started", "type": "automation"},
                    {"time": "09:15", "event": "Document retrieval completed (150 docs)", "type": "automation"},
                    {"time": "09:30", "event": "Email retrieval completed (285 unique emails)", "type": "automation"},
                    {"time": "10:00", "event": "Text extraction completed", "type": "automation"},
                    {"time": "10:30", "event": "AI classification completed", "type": "automation"},
                    {"time": "11:00", "event": "Redaction detection completed", "type": "automation"},
                    {"time": "11:30", "event": "Sent to department for review", "type": "handoff"},
                ]
            },
            {
                "date": "2025-08-23",
                "events": [
                    {"time": "15:00", "event": "Department review 65% complete", "type": "progress"},
                ]
            },
        ],
        "estimated_completion": {
            "department_review": "2025-08-26",
            "leadership_approval": "2025-08-27",
            "final_release": "2025-08-28",
        },
    }


@router.get("/metrics")
async def get_workflow_metrics():
    """
    Get aggregated workflow performance metrics.
    """
    return {
        "period": "last_30_days",
        "requests_processed": 45,
        "average_processing_time": {
            "document_retrieval": "12 minutes",
            "ai_classification": "25 minutes",
            "total_automated": "52 minutes",
            "total_with_review": "4.2 days",
        },
        "automation_impact": {
            "documents_auto_classified": 6750,
            "emails_deduplicated": 4200,
            "estimated_hours_saved": 380,
            "manual_review_reduction_percent": 68,
        },
        "deadline_compliance": {
            "on_time": 42,
            "late": 3,
            "compliance_rate": 93.3,
        },
    }
