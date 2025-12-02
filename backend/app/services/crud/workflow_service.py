"""
CRUD service for Workflow Tasks.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload

from app.services.crud.base_service import BaseCRUDService
from app.models.workflow import WorkflowTask, WorkflowTaskType, WorkflowTaskStatus, WorkflowTemplate


class WorkflowService(BaseCRUDService[WorkflowTask]):
    """
    Service for Workflow Task CRUD operations.
    """

    def __init__(self):
        super().__init__(WorkflowTask)

    # Default PIA workflow task sequence
    DEFAULT_WORKFLOW_TASKS = [
        {
            "task_type": WorkflowTaskType.DOCUMENT_RETRIEVAL,
            "task_name": "Retrieve Documents from SharePoint/OneDrive",
            "sequence_order": 1,
            "is_automated": True,
        },
        {
            "task_type": WorkflowTaskType.EMAIL_RETRIEVAL,
            "task_name": "Retrieve Emails from Outlook",
            "sequence_order": 2,
            "is_automated": True,
        },
        {
            "task_type": WorkflowTaskType.TEXT_EXTRACTION,
            "task_name": "Extract Text from Documents",
            "sequence_order": 3,
            "is_automated": True,
            "depends_on": [WorkflowTaskType.DOCUMENT_RETRIEVAL.value],
        },
        {
            "task_type": WorkflowTaskType.DEDUPLICATION,
            "task_name": "Deduplicate Documents and Emails",
            "sequence_order": 4,
            "is_automated": True,
            "depends_on": [
                WorkflowTaskType.TEXT_EXTRACTION.value,
                WorkflowTaskType.EMAIL_RETRIEVAL.value,
            ],
        },
        {
            "task_type": WorkflowTaskType.CLASSIFICATION,
            "task_name": "AI Classification by Exemption Category",
            "sequence_order": 5,
            "is_automated": True,
            "depends_on": [WorkflowTaskType.DEDUPLICATION.value],
        },
        {
            "task_type": WorkflowTaskType.REDACTION_DETECTION,
            "task_name": "Detect Redaction Areas",
            "sequence_order": 6,
            "is_automated": True,
            "depends_on": [WorkflowTaskType.CLASSIFICATION.value],
        },
        {
            "task_type": WorkflowTaskType.DEPARTMENT_REVIEW,
            "task_name": "Department Review of Classifications",
            "sequence_order": 7,
            "is_automated": False,
            "depends_on": [WorkflowTaskType.REDACTION_DETECTION.value],
        },
        {
            "task_type": WorkflowTaskType.LEADERSHIP_APPROVAL,
            "task_name": "Leadership Approval",
            "sequence_order": 8,
            "is_automated": False,
            "depends_on": [WorkflowTaskType.DEPARTMENT_REVIEW.value],
        },
        {
            "task_type": WorkflowTaskType.REDACTION_APPLICATION,
            "task_name": "Apply Redactions to Documents",
            "sequence_order": 9,
            "is_automated": True,
            "depends_on": [WorkflowTaskType.LEADERSHIP_APPROVAL.value],
        },
        {
            "task_type": WorkflowTaskType.RESPONSE_GENERATION,
            "task_name": "Generate Response Package",
            "sequence_order": 10,
            "is_automated": True,
            "depends_on": [WorkflowTaskType.REDACTION_APPLICATION.value],
        },
        {
            "task_type": WorkflowTaskType.FINAL_REVIEW,
            "task_name": "Final Review Before Release",
            "sequence_order": 11,
            "is_automated": False,
            "depends_on": [WorkflowTaskType.RESPONSE_GENERATION.value],
        },
    ]

    async def initialize_workflow(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> List[WorkflowTask]:
        """
        Initialize the standard PIA workflow for a request.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            List of created workflow tasks
        """
        tasks = []

        for task_def in self.DEFAULT_WORKFLOW_TASKS:
            task_data = {
                "pia_request_id": request_id,
                "task_type": task_def["task_type"],
                "task_name": task_def["task_name"],
                "sequence_order": task_def["sequence_order"],
                "is_automated": task_def["is_automated"],
                "depends_on": task_def.get("depends_on", []),
                "status": WorkflowTaskStatus.PENDING,
            }

            task = await self.create(db, task_data)
            tasks.append(task)

        return tasks

    async def get_tasks_for_request(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> List[WorkflowTask]:
        """
        Get all workflow tasks for a request.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            List of workflow tasks ordered by sequence
        """
        query = (
            select(WorkflowTask)
            .where(WorkflowTask.pia_request_id == request_id)
            .order_by(WorkflowTask.sequence_order)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_next_runnable_tasks(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> List[WorkflowTask]:
        """
        Get tasks that can be executed next (dependencies satisfied).

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            List of runnable tasks
        """
        # Get all tasks for the request
        all_tasks = await self.get_tasks_for_request(db, request_id)

        # Get completed task types
        completed_types = {
            task.task_type.value
            for task in all_tasks
            if task.status == WorkflowTaskStatus.COMPLETED
        }

        # Find pending tasks with satisfied dependencies
        runnable = []
        for task in all_tasks:
            if task.status != WorkflowTaskStatus.PENDING:
                continue

            dependencies = task.depends_on or []
            if all(dep in completed_types for dep in dependencies):
                runnable.append(task)

        return runnable

    async def start_task(
        self,
        db: AsyncSession,
        task_id: int,
        celery_task_id: Optional[str] = None,
    ) -> Optional[WorkflowTask]:
        """
        Mark a task as in progress.

        Args:
            db: Database session
            task_id: Task ID
            celery_task_id: Optional Celery task ID

        Returns:
            Updated task or None
        """
        update_data = {
            "status": WorkflowTaskStatus.IN_PROGRESS,
            "started_at": datetime.utcnow(),
        }

        if celery_task_id:
            update_data["celery_task_id"] = celery_task_id

        return await self.update(db, task_id, update_data)

    async def complete_task(
        self,
        db: AsyncSession,
        task_id: int,
        result_data: Optional[Dict] = None,
    ) -> Optional[WorkflowTask]:
        """
        Mark a task as completed.

        Args:
            db: Database session
            task_id: Task ID
            result_data: Task result data

        Returns:
            Updated task or None
        """
        update_data = {
            "status": WorkflowTaskStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
        }

        if result_data:
            update_data["result_data"] = result_data

        return await self.update(db, task_id, update_data)

    async def fail_task(
        self,
        db: AsyncSession,
        task_id: int,
        error_message: str,
    ) -> Optional[WorkflowTask]:
        """
        Mark a task as failed.

        Args:
            db: Database session
            task_id: Task ID
            error_message: Error description

        Returns:
            Updated task or None
        """
        task = await self.get(db, task_id)
        if not task:
            return None

        update_data = {
            "status": WorkflowTaskStatus.FAILED,
            "error_message": error_message,
            "retry_count": (task.retry_count or 0) + 1,
        }

        return await self.update(db, task_id, update_data)

    async def assign_task(
        self,
        db: AsyncSession,
        task_id: int,
        user_id: int,
    ) -> Optional[WorkflowTask]:
        """
        Assign a manual task to a user.

        Args:
            db: Database session
            task_id: Task ID
            user_id: User ID to assign

        Returns:
            Updated task or None
        """
        return await self.update(
            db,
            task_id,
            {"assigned_to": user_id}
        )

    async def retry_task(
        self,
        db: AsyncSession,
        task_id: int,
    ) -> Optional[WorkflowTask]:
        """
        Reset a failed task for retry.

        Args:
            db: Database session
            task_id: Task ID

        Returns:
            Updated task or None
        """
        return await self.update(
            db,
            task_id,
            {
                "status": WorkflowTaskStatus.PENDING,
                "error_message": None,
                "started_at": None,
                "completed_at": None,
            }
        )

    async def get_task_by_type(
        self,
        db: AsyncSession,
        request_id: int,
        task_type: WorkflowTaskType,
    ) -> Optional[WorkflowTask]:
        """
        Get a specific task type for a request.

        Args:
            db: Database session
            request_id: PIA request ID
            task_type: Task type

        Returns:
            Workflow task or None
        """
        query = select(WorkflowTask).where(
            and_(
                WorkflowTask.pia_request_id == request_id,
                WorkflowTask.task_type == task_type,
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_workflow_status(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Dict[str, Any]:
        """
        Get workflow status summary.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            Workflow status summary
        """
        tasks = await self.get_tasks_for_request(db, request_id)

        if not tasks:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "pending_tasks": 0,
                "failed_tasks": 0,
                "progress_percentage": 0,
                "current_task": None,
                "next_tasks": [],
                "workflow_complete": False,
            }

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == WorkflowTaskStatus.COMPLETED)
        in_progress = sum(1 for t in tasks if t.status == WorkflowTaskStatus.IN_PROGRESS)
        pending = sum(1 for t in tasks if t.status == WorkflowTaskStatus.PENDING)
        failed = sum(1 for t in tasks if t.status == WorkflowTaskStatus.FAILED)

        # Find current task (first in-progress or first pending with satisfied deps)
        current_task = next(
            (t for t in tasks if t.status == WorkflowTaskStatus.IN_PROGRESS),
            None
        )

        # Get next runnable tasks
        next_tasks = await self.get_next_runnable_tasks(db, request_id)

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "pending_tasks": pending,
            "failed_tasks": failed,
            "progress_percentage": round((completed / total * 100) if total > 0 else 0, 1),
            "current_task": current_task.task_name if current_task else None,
            "current_task_type": current_task.task_type.value if current_task else None,
            "next_tasks": [t.task_name for t in next_tasks[:3]],
            "workflow_complete": completed == total,
            "has_failures": failed > 0,
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type.value,
                    "task_name": t.task_name,
                    "status": t.status.value,
                    "is_automated": t.is_automated,
                    "sequence_order": t.sequence_order,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    "error_message": t.error_message,
                }
                for t in tasks
            ],
        }

    async def get_pending_automated_tasks(
        self,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[WorkflowTask]:
        """
        Get pending automated tasks across all requests.

        Args:
            db: Database session
            limit: Maximum tasks to return

        Returns:
            List of pending automated tasks
        """
        query = (
            select(WorkflowTask)
            .where(
                and_(
                    WorkflowTask.status == WorkflowTaskStatus.PENDING,
                    WorkflowTask.is_automated == True,
                )
            )
            .order_by(WorkflowTask.created_at.asc())
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_workflow_timeline(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get workflow execution timeline.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            Timeline of task executions
        """
        tasks = await self.get_tasks_for_request(db, request_id)

        timeline = []
        for task in tasks:
            entry = {
                "task_name": task.task_name,
                "task_type": task.task_type.value,
                "status": task.status.value,
                "sequence_order": task.sequence_order,
            }

            if task.started_at:
                timeline.append({
                    **entry,
                    "event": "started",
                    "timestamp": task.started_at.isoformat(),
                })

            if task.completed_at:
                duration = None
                if task.started_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                timeline.append({
                    **entry,
                    "event": "completed",
                    "timestamp": task.completed_at.isoformat(),
                    "duration_seconds": duration,
                })

            if task.error_message:
                timeline.append({
                    **entry,
                    "event": "failed",
                    "timestamp": task.updated_at.isoformat() if task.updated_at else None,
                    "error": task.error_message,
                })

        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp") or "")

        return timeline


# Singleton instance
_workflow_service: Optional[WorkflowService] = None


def get_workflow_service() -> WorkflowService:
    """Get or create the workflow service singleton."""
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service
