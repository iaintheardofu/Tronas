"""
CRUD service for Audit Logs.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.services.crud.base_service import BaseCRUDService
from app.models.audit_log import AuditLog, AuditAction, AuditCategory


class AuditService(BaseCRUDService[AuditLog]):
    """
    Service for Audit Log CRUD operations.
    Provides comprehensive audit trail for compliance.
    """

    def __init__(self):
        super().__init__(AuditLog)

    async def log_action(
        self,
        db: AsyncSession,
        action: str,
        category: str,
        request_id: Optional[int] = None,
        user_id: Optional[int] = None,
        details: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            db: Database session
            action: Action performed (e.g., CREATE, UPDATE, DELETE)
            category: Category of action (e.g., request, document, workflow)
            request_id: Associated PIA request ID
            user_id: User who performed action
            details: Human-readable description
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created audit log entry
        """
        log_data = {
            "action": action,
            "category": category,
            "pia_request_id": request_id,
            "user_id": user_id,
            "details": details,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        return await self.create(db, log_data)

    async def log_request_created(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: int,
        request_data: Dict,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log PIA request creation."""
        return await self.log_action(
            db=db,
            action=AuditAction.CREATE,
            category=AuditCategory.REQUEST,
            request_id=request_id,
            user_id=user_id,
            details=f"Created PIA request {request_data.get('request_number', '')}",
            new_values=request_data,
            ip_address=ip_address,
        )

    async def log_request_updated(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: int,
        old_values: Dict,
        new_values: Dict,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log PIA request update."""
        return await self.log_action(
            db=db,
            action=AuditAction.UPDATE,
            category=AuditCategory.REQUEST,
            request_id=request_id,
            user_id=user_id,
            details="Updated PIA request",
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )

    async def log_status_change(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: Optional[int],
        old_status: str,
        new_status: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log request status change."""
        return await self.log_action(
            db=db,
            action=AuditAction.STATUS_CHANGE,
            category=AuditCategory.REQUEST,
            request_id=request_id,
            user_id=user_id,
            details=f"Status changed from {old_status} to {new_status}",
            old_values={"status": old_status},
            new_values={"status": new_status},
            ip_address=ip_address,
        )

    async def log_document_uploaded(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: Optional[int],
        document_info: Dict,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log document upload."""
        return await self.log_action(
            db=db,
            action=AuditAction.UPLOAD,
            category=AuditCategory.DOCUMENT,
            request_id=request_id,
            user_id=user_id,
            details=f"Uploaded document: {document_info.get('filename', 'unknown')}",
            new_values=document_info,
            ip_address=ip_address,
        )

    async def log_classification(
        self,
        db: AsyncSession,
        request_id: int,
        document_id: int,
        classification: str,
        confidence: float,
        is_ai: bool = True,
        user_id: Optional[int] = None,
    ) -> AuditLog:
        """Log document classification."""
        source = "AI" if is_ai else "Human"
        return await self.log_action(
            db=db,
            action=AuditAction.CLASSIFY,
            category=AuditCategory.CLASSIFICATION,
            request_id=request_id,
            user_id=user_id,
            details=f"{source} classified document {document_id} as {classification} (confidence: {confidence:.2f})",
            new_values={
                "document_id": document_id,
                "classification": classification,
                "confidence": confidence,
                "is_ai_classification": is_ai,
            },
        )

    async def log_review_submitted(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: int,
        document_id: int,
        decision: str,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log human review submission."""
        return await self.log_action(
            db=db,
            action=AuditAction.REVIEW,
            category=AuditCategory.REVIEW,
            request_id=request_id,
            user_id=user_id,
            details=f"Reviewed document {document_id}: {decision}",
            new_values={
                "document_id": document_id,
                "decision": decision,
                "notes": notes,
            },
            ip_address=ip_address,
        )

    async def log_redaction_applied(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: int,
        document_id: int,
        redaction_count: int,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log redaction application."""
        return await self.log_action(
            db=db,
            action=AuditAction.REDACT,
            category=AuditCategory.DOCUMENT,
            request_id=request_id,
            user_id=user_id,
            details=f"Applied {redaction_count} redactions to document {document_id}",
            new_values={
                "document_id": document_id,
                "redaction_count": redaction_count,
            },
            ip_address=ip_address,
        )

    async def log_document_accessed(
        self,
        db: AsyncSession,
        request_id: int,
        user_id: int,
        document_id: int,
        access_type: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log document access."""
        return await self.log_action(
            db=db,
            action=AuditAction.ACCESS,
            category=AuditCategory.DOCUMENT,
            request_id=request_id,
            user_id=user_id,
            details=f"Accessed document {document_id} ({access_type})",
            new_values={
                "document_id": document_id,
                "access_type": access_type,
            },
            ip_address=ip_address,
        )

    async def log_workflow_event(
        self,
        db: AsyncSession,
        request_id: int,
        task_type: str,
        event: str,
        details: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> AuditLog:
        """Log workflow event."""
        return await self.log_action(
            db=db,
            action=event,
            category=AuditCategory.WORKFLOW,
            request_id=request_id,
            user_id=user_id,
            details=details or f"Workflow task {task_type}: {event}",
            new_values={
                "task_type": task_type,
                "event": event,
            },
        )

    async def log_user_login(
        self,
        db: AsyncSession,
        user_id: int,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log user login attempt."""
        action = AuditAction.LOGIN if success else "LOGIN_FAILED"
        return await self.log_action(
            db=db,
            action=action,
            category=AuditCategory.SYSTEM,
            user_id=user_id,
            details=f"User login {'successful' if success else 'failed'}",
            new_values={"success": success},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_logs_for_request(
        self,
        db: AsyncSession,
        request_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific request.

        Args:
            db: Database session
            request_id: PIA request ID
            skip: Pagination offset
            limit: Page size

        Returns:
            List of audit logs
        """
        query = (
            select(AuditLog)
            .where(AuditLog.pia_request_id == request_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activity(
        self,
        db: AsyncSession,
        limit: int = 20,
        request_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity feed.

        Args:
            db: Database session
            limit: Maximum entries
            request_id: Optional filter by request
            user_id: Optional filter by user

        Returns:
            List of recent activity entries
        """
        query = select(AuditLog)

        if request_id:
            query = query.where(AuditLog.pia_request_id == request_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        query = query.order_by(AuditLog.created_at.desc()).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": log.id,
                "action": log.action,
                "category": log.category,
                "description": log.details,
                "timestamp": log.created_at.isoformat(),
                "request_id": log.pia_request_id,
                "user_id": log.user_id,
            }
            for log in logs
        ]

    async def get_compliance_report(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit purposes.

        Args:
            db: Database session
            start_date: Report start date
            end_date: Report end date

        Returns:
            Compliance report data
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Total actions in period
        total_query = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                )
            )
        )
        total_result = await db.execute(total_query)
        total_actions = total_result.scalar() or 0

        # Actions by category
        category_query = (
            select(AuditLog.category, func.count().label("count"))
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                )
            )
            .group_by(AuditLog.category)
        )
        category_result = await db.execute(category_query)
        by_category = {row[0]: row[1] for row in category_result.all()}

        # Actions by action type
        action_query = (
            select(AuditLog.action, func.count().label("count"))
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                )
            )
            .group_by(AuditLog.action)
        )
        action_result = await db.execute(action_query)
        by_action = {row[0]: row[1] for row in action_result.all()}

        # Unique requests affected
        requests_query = (
            select(func.count(func.distinct(AuditLog.pia_request_id)))
            .select_from(AuditLog)
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                    AuditLog.pia_request_id != None,
                )
            )
        )
        requests_result = await db.execute(requests_query)
        unique_requests = requests_result.scalar() or 0

        # Unique users active
        users_query = (
            select(func.count(func.distinct(AuditLog.user_id)))
            .select_from(AuditLog)
            .where(
                and_(
                    AuditLog.created_at >= start_date,
                    AuditLog.created_at <= end_date,
                    AuditLog.user_id != None,
                )
            )
        )
        users_result = await db.execute(users_query)
        unique_users = users_result.scalar() or 0

        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_actions": total_actions,
            "unique_requests_affected": unique_requests,
            "unique_users_active": unique_users,
            "actions_by_category": by_category,
            "actions_by_type": by_action,
            "generated_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the audit service singleton."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
