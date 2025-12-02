"""
Workflow automation engine for PIA request processing.
Orchestrates the complete request lifecycle with task scheduling.
"""
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.workflow import WorkflowTask, WorkflowStatus, TaskType
from app.models.pia_request import PIARequest, PIARequestStatus


class WorkflowEngine:
    """
    Orchestrates PIA request workflow automation.
    Manages task execution, dependencies, and status transitions.
    """

    # Default workflow template for PIA requests
    DEFAULT_WORKFLOW = [
        {
            "task_type": TaskType.DOCUMENT_RETRIEVAL,
            "task_name": "Retrieve Documents from M365",
            "sequence_order": 1,
            "is_automated": True,
            "config": {"sources": ["sharepoint", "onedrive"]},
        },
        {
            "task_type": TaskType.EMAIL_RETRIEVAL,
            "task_name": "Retrieve Emails from Outlook",
            "sequence_order": 2,
            "is_automated": True,
            "config": {},
        },
        {
            "task_type": TaskType.TEXT_EXTRACTION,
            "task_name": "Extract Text from Documents",
            "sequence_order": 3,
            "depends_on": [1, 2],
            "is_automated": True,
        },
        {
            "task_type": TaskType.DEDUPLICATION,
            "task_name": "Deduplicate and Group Emails",
            "sequence_order": 4,
            "depends_on": [2],
            "is_automated": True,
        },
        {
            "task_type": TaskType.AI_CLASSIFICATION,
            "task_name": "AI Document Classification",
            "sequence_order": 5,
            "depends_on": [3, 4],
            "is_automated": True,
        },
        {
            "task_type": TaskType.REDACTION_PREP,
            "task_name": "Prepare Redaction Areas",
            "sequence_order": 6,
            "depends_on": [5],
            "is_automated": True,
        },
        {
            "task_type": TaskType.DEPARTMENT_REVIEW,
            "task_name": "Department Review",
            "sequence_order": 7,
            "depends_on": [6],
            "is_automated": False,
            "assigned_role": "department_reviewer",
        },
        {
            "task_type": TaskType.LEADERSHIP_APPROVAL,
            "task_name": "Leadership Approval",
            "sequence_order": 8,
            "depends_on": [7],
            "is_automated": False,
            "assigned_role": "legal_reviewer",
        },
        {
            "task_type": TaskType.FINAL_REVIEW,
            "task_name": "Final Review and Release",
            "sequence_order": 9,
            "depends_on": [8],
            "is_automated": False,
            "assigned_role": "records_liaison",
        },
        {
            "task_type": TaskType.RESPONSE_GENERATION,
            "task_name": "Generate Response Letter",
            "sequence_order": 10,
            "depends_on": [9],
            "is_automated": True,
        },
        {
            "task_type": TaskType.NOTIFICATION,
            "task_name": "Send Notifications",
            "sequence_order": 11,
            "depends_on": [10],
            "is_automated": True,
        },
    ]

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.task_handlers: Dict[TaskType, Callable] = {}

    def register_task_handler(
        self,
        task_type: TaskType,
        handler: Callable,
    ):
        """Register a handler function for a task type."""
        self.task_handlers[task_type] = handler

    async def create_workflow_for_request(
        self,
        request_id: int,
        template: List[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Create workflow tasks for a PIA request.

        Args:
            request_id: ID of the PIA request
            template: Optional custom workflow template

        Returns:
            List of created task configurations
        """
        template = template or self.DEFAULT_WORKFLOW
        created_tasks = []

        for task_config in template:
            task = WorkflowTask(
                pia_request_id=request_id,
                task_type=task_config["task_type"],
                task_name=task_config["task_name"],
                sequence_order=task_config["sequence_order"],
                depends_on=task_config.get("depends_on"),
                is_automated=task_config.get("is_automated", True),
                assigned_role=task_config.get("assigned_role"),
                task_config=task_config.get("config"),
                status=WorkflowStatus.PENDING,
            )

            if self.db:
                self.db.add(task)
                created_tasks.append({
                    "task_type": task.task_type.value,
                    "task_name": task.task_name,
                    "sequence_order": task.sequence_order,
                })

        if self.db:
            await self.db.commit()

        logger.info(f"Created {len(created_tasks)} workflow tasks for request {request_id}")
        return created_tasks

    async def get_runnable_tasks(
        self,
        request_id: int,
    ) -> List[WorkflowTask]:
        """
        Get tasks that are ready to run (dependencies satisfied).

        Args:
            request_id: PIA request ID

        Returns:
            List of runnable tasks
        """
        # This would query the database for tasks where:
        # 1. Status is PENDING
        # 2. All dependencies are COMPLETED
        # For now, return empty list - would be implemented with actual DB queries
        return []

    async def execute_task(
        self,
        task: WorkflowTask,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single workflow task.

        Args:
            task: Task to execute
            context: Execution context (request data, etc.)

        Returns:
            Task execution result
        """
        task.status = WorkflowStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()

        if self.db:
            await self.db.commit()

        try:
            handler = self.task_handlers.get(task.task_type)

            if handler and task.is_automated:
                result = await handler(task, context)
            elif not task.is_automated:
                # Manual task - just mark as waiting
                task.status = WorkflowStatus.WAITING_APPROVAL
                result = {"status": "waiting_for_manual_action"}
            else:
                result = {"status": "no_handler", "message": f"No handler for {task.task_type}"}

            if task.is_automated and result.get("status") != "error":
                task.status = WorkflowStatus.COMPLETED
                task.completed_at = datetime.utcnow()

            task.result_data = result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.status = WorkflowStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            result = {"status": "error", "error": str(e)}

        if self.db:
            await self.db.commit()

        return result

    async def process_workflow(
        self,
        request_id: int,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process the workflow for a request, executing ready tasks.

        Args:
            request_id: PIA request ID
            context: Execution context

        Returns:
            Workflow processing status
        """
        context = context or {}
        executed_tasks = []
        pending_manual = []

        runnable_tasks = await self.get_runnable_tasks(request_id)

        for task in runnable_tasks:
            if task.is_automated:
                result = await self.execute_task(task, context)
                executed_tasks.append({
                    "task_id": task.id,
                    "task_name": task.task_name,
                    "result": result,
                })
            else:
                pending_manual.append({
                    "task_id": task.id,
                    "task_name": task.task_name,
                    "assigned_role": task.assigned_role,
                })

        return {
            "request_id": request_id,
            "executed_tasks": executed_tasks,
            "pending_manual_tasks": pending_manual,
            "workflow_status": self._determine_workflow_status(request_id),
        }

    def _determine_workflow_status(self, request_id: int) -> str:
        """Determine overall workflow status for a request."""
        # Would query DB for task statuses
        return "in_progress"

    async def complete_manual_task(
        self,
        task_id: int,
        user_id: int,
        result_data: Dict[str, Any] = None,
        notes: str = None,
    ) -> Dict[str, Any]:
        """
        Mark a manual task as completed.

        Args:
            task_id: Task ID
            user_id: User completing the task
            result_data: Optional result data
            notes: Optional notes

        Returns:
            Task completion result
        """
        # Would update the task in the database
        return {
            "task_id": task_id,
            "status": "completed",
            "completed_by": user_id,
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def get_workflow_status(
        self,
        request_id: int,
    ) -> Dict[str, Any]:
        """
        Get detailed workflow status for a request.

        Args:
            request_id: PIA request ID

        Returns:
            Workflow status details
        """
        # Would query all tasks and compile status
        return {
            "request_id": request_id,
            "total_tasks": 11,
            "completed_tasks": 0,
            "in_progress_tasks": 0,
            "pending_tasks": 11,
            "failed_tasks": 0,
            "overall_progress": 0,
            "estimated_completion": None,
            "next_action_required": "Start workflow",
        }


class PIAWorkflowOrchestrator:
    """
    High-level orchestrator for PIA request workflows.
    Manages the complete request lifecycle.
    """

    def __init__(self, workflow_engine: WorkflowEngine):
        self.engine = workflow_engine

    async def start_new_request(
        self,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Initialize a new PIA request with workflow.

        Args:
            request_data: Request details

        Returns:
            Created request with workflow
        """
        # 1. Create the PIA request record
        # 2. Create workflow tasks
        # 3. Start automated tasks

        request_id = request_data.get("id", 1)  # Would come from DB

        # Create workflow
        tasks = await self.engine.create_workflow_for_request(request_id)

        # Start initial automated tasks
        result = await self.engine.process_workflow(request_id, request_data)

        return {
            "request_id": request_id,
            "workflow_created": True,
            "tasks_created": len(tasks),
            "initial_processing": result,
        }

    async def check_and_advance_workflow(
        self,
        request_id: int,
    ) -> Dict[str, Any]:
        """
        Check workflow status and advance if possible.

        Args:
            request_id: PIA request ID

        Returns:
            Updated workflow status
        """
        return await self.engine.process_workflow(request_id)


# Singleton instance
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine(db: AsyncSession = None) -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine(db)
    return _engine
