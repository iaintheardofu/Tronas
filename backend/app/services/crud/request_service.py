"""
CRUD service for PIA Requests.
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.services.crud.base_service import BaseCRUDService
from app.models.pia_request import PIARequest, PIARequestStatus, PIARequestPriority
from app.services.workflow.deadline_manager import get_deadline_manager


class RequestService(BaseCRUDService[PIARequest]):
    """
    Service for PIA Request CRUD operations.
    """

    def __init__(self):
        super().__init__(PIARequest)
        self.deadline_manager = get_deadline_manager()

    async def create_request(
        self,
        db: AsyncSession,
        request_data: Dict[str, Any],
    ) -> PIARequest:
        """
        Create a new PIA request with automatic deadline calculation.

        Args:
            db: Database session
            request_data: Request data dictionary

        Returns:
            Created PIA request
        """
        # Calculate response deadline (10 business days)
        date_received = request_data.get("date_received")
        if isinstance(date_received, str):
            date_received = datetime.fromisoformat(date_received).date()
        elif isinstance(date_received, datetime):
            date_received = date_received.date()

        response_deadline = self.deadline_manager.calculate_response_deadline(date_received)

        # Ensure date_received is datetime
        if isinstance(request_data.get("date_received"), date) and not isinstance(request_data.get("date_received"), datetime):
            request_data["date_received"] = datetime.combine(
                request_data["date_received"],
                datetime.min.time()
            )

        request_data["response_deadline"] = response_deadline
        request_data["status"] = PIARequestStatus.RECEIVED

        return await self.create(db, request_data)

    async def get_request_with_relations(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Optional[PIARequest]:
        """
        Get a request with all related data loaded.

        Args:
            db: Database session
            request_id: Request ID

        Returns:
            PIA request with relations or None
        """
        query = (
            select(PIARequest)
            .where(PIARequest.id == request_id)
            .options(
                selectinload(PIARequest.documents),
                selectinload(PIARequest.email_records),
                selectinload(PIARequest.workflow_tasks),
                selectinload(PIARequest.assigned_to_user),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_requests_by_status(
        self,
        db: AsyncSession,
        status: PIARequestStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PIARequest]:
        """
        Get requests filtered by status.

        Args:
            db: Database session
            status: Request status
            skip: Pagination offset
            limit: Page size

        Returns:
            List of requests
        """
        return await self.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters={"status": status},
            order_by=PIARequest.date_received.desc(),
        )

    async def get_overdue_requests(
        self,
        db: AsyncSession,
    ) -> List[PIARequest]:
        """
        Get all requests past their deadline.

        Args:
            db: Database session

        Returns:
            List of overdue requests
        """
        today = date.today()
        terminal_statuses = [
            PIARequestStatus.RELEASED,
            PIARequestStatus.CLOSED_NO_RECORDS,
            PIARequestStatus.WITHDRAWN,
        ]

        query = (
            select(PIARequest)
            .where(
                and_(
                    PIARequest.response_deadline < today,
                    PIARequest.status.notin_(terminal_statuses),
                )
            )
            .order_by(PIARequest.response_deadline.asc())
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_urgent_requests(
        self,
        db: AsyncSession,
        days_threshold: int = 3,
    ) -> List[PIARequest]:
        """
        Get requests approaching or past deadline.

        Args:
            db: Database session
            days_threshold: Number of days to consider urgent

        Returns:
            List of urgent requests
        """
        today = date.today()
        threshold_date = self.deadline_manager.add_business_days(today, days_threshold)
        terminal_statuses = [
            PIARequestStatus.RELEASED,
            PIARequestStatus.CLOSED_NO_RECORDS,
            PIARequestStatus.WITHDRAWN,
        ]

        query = (
            select(PIARequest)
            .where(
                and_(
                    PIARequest.response_deadline <= threshold_date,
                    PIARequest.status.notin_(terminal_statuses),
                )
            )
            .order_by(PIARequest.response_deadline.asc())
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_requests_needing_processing(
        self,
        db: AsyncSession,
    ) -> List[PIARequest]:
        """
        Get requests in received status ready for processing.

        Args:
            db: Database session

        Returns:
            List of requests needing processing
        """
        query = (
            select(PIARequest)
            .where(PIARequest.status == PIARequestStatus.RECEIVED)
            .order_by(PIARequest.date_received.asc())
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_requests_needing_classification(
        self,
        db: AsyncSession,
    ) -> List[PIARequest]:
        """
        Get requests with documents that need classification.

        Args:
            db: Database session

        Returns:
            List of requests needing classification
        """
        query = (
            select(PIARequest)
            .where(
                and_(
                    PIARequest.documents_retrieved == True,
                    PIARequest.classification_complete == False,
                    PIARequest.status.in_([
                        PIARequestStatus.RECEIVED,
                        PIARequestStatus.IN_PROGRESS,
                    ])
                )
            )
            .order_by(PIARequest.response_deadline.asc())
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_request_status(
        self,
        db: AsyncSession,
        request_id: int,
        new_status: PIARequestStatus,
    ) -> Optional[PIARequest]:
        """
        Update request status.

        Args:
            db: Database session
            request_id: Request ID
            new_status: New status

        Returns:
            Updated request or None
        """
        update_data = {"status": new_status}

        # Set completion date if moving to terminal status
        if new_status in [
            PIARequestStatus.RELEASED,
            PIARequestStatus.CLOSED_NO_RECORDS,
            PIARequestStatus.WITHDRAWN,
        ]:
            update_data["date_completed"] = datetime.utcnow()

        return await self.update(db, request_id, update_data)

    async def request_extension(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Optional[PIARequest]:
        """
        Request a 10-business-day extension.

        Args:
            db: Database session
            request_id: Request ID

        Returns:
            Updated request or None
        """
        request = await self.get(db, request_id)
        if not request:
            return None

        new_deadline = self.deadline_manager.calculate_extension_deadline(
            request.response_deadline
        )

        return await self.update(
            db,
            request_id,
            {
                "extension_deadline": new_deadline,
                "response_deadline": new_deadline,
            }
        )

    async def initiate_ag_ruling(
        self,
        db: AsyncSession,
        request_id: int,
        exemptions: List[str],
    ) -> Optional[PIARequest]:
        """
        Initiate AG ruling request.

        Args:
            db: Database session
            request_id: Request ID
            exemptions: List of exemption codes cited

        Returns:
            Updated request or None
        """
        request = await self.get(db, request_id)
        if not request:
            return None

        today = date.today()
        ag_ruling_deadline = self.deadline_manager.calculate_ag_ruling_deadline(today)

        return await self.update(
            db,
            request_id,
            {
                "status": PIARequestStatus.PENDING_AG_RULING,
                "ag_submission_date": today,
                "ag_ruling_deadline": ag_ruling_deadline,
            }
        )

    async def update_document_stats(
        self,
        db: AsyncSession,
        request_id: int,
        total_documents: int,
        total_pages: int,
        responsive_documents: int = 0,
        redacted_documents: int = 0,
        withheld_documents: int = 0,
    ) -> Optional[PIARequest]:
        """
        Update document statistics for a request.

        Args:
            db: Database session
            request_id: Request ID
            total_documents: Total documents retrieved
            total_pages: Total pages
            responsive_documents: Responsive document count
            redacted_documents: Redacted document count
            withheld_documents: Withheld document count

        Returns:
            Updated request or None
        """
        return await self.update(
            db,
            request_id,
            {
                "total_documents": total_documents,
                "total_pages": total_pages,
                "responsive_documents": responsive_documents,
                "redacted_documents": redacted_documents,
                "withheld_documents": withheld_documents,
            }
        )

    async def mark_documents_retrieved(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Optional[PIARequest]:
        """
        Mark documents as retrieved for a request.

        Args:
            db: Database session
            request_id: Request ID

        Returns:
            Updated request or None
        """
        return await self.update(
            db,
            request_id,
            {
                "documents_retrieved": True,
                "status": PIARequestStatus.IN_PROGRESS,
            }
        )

    async def mark_classification_complete(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Optional[PIARequest]:
        """
        Mark classification as complete for a request.

        Args:
            db: Database session
            request_id: Request ID

        Returns:
            Updated request or None
        """
        return await self.update(
            db,
            request_id,
            {
                "classification_complete": True,
                "status": PIARequestStatus.PENDING_DEPARTMENT_REVIEW,
            }
        )

    async def get_dashboard_overview(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Get dashboard overview statistics.

        Args:
            db: Database session

        Returns:
            Dashboard overview data
        """
        today = date.today()

        # Get counts by status
        total_query = select(func.count()).select_from(PIARequest)
        total_result = await db.execute(total_query)
        total_requests = total_result.scalar() or 0

        # In progress count
        in_progress_query = (
            select(func.count())
            .select_from(PIARequest)
            .where(PIARequest.status == PIARequestStatus.IN_PROGRESS)
        )
        in_progress_result = await db.execute(in_progress_query)
        in_progress = in_progress_result.scalar() or 0

        # Completed count
        completed_query = (
            select(func.count())
            .select_from(PIARequest)
            .where(PIARequest.status.in_([
                PIARequestStatus.RELEASED,
                PIARequestStatus.CLOSED_NO_RECORDS,
            ]))
        )
        completed_result = await db.execute(completed_query)
        completed = completed_result.scalar() or 0

        # Pending review count
        pending_query = (
            select(func.count())
            .select_from(PIARequest)
            .where(PIARequest.status.in_([
                PIARequestStatus.PENDING_DEPARTMENT_REVIEW,
                PIARequestStatus.PENDING_LEADERSHIP_APPROVAL,
            ]))
        )
        pending_result = await db.execute(pending_query)
        pending = pending_result.scalar() or 0

        # Urgent/overdue count
        urgent_query = (
            select(func.count())
            .select_from(PIARequest)
            .where(
                and_(
                    PIARequest.response_deadline <= self.deadline_manager.add_business_days(today, 3),
                    PIARequest.status.notin_([
                        PIARequestStatus.RELEASED,
                        PIARequestStatus.CLOSED_NO_RECORDS,
                        PIARequestStatus.WITHDRAWN,
                    ])
                )
            )
        )
        urgent_result = await db.execute(urgent_query)
        urgent = urgent_result.scalar() or 0

        # Total documents processed
        docs_query = select(func.sum(PIARequest.total_documents)).select_from(PIARequest)
        docs_result = await db.execute(docs_query)
        total_docs = docs_result.scalar() or 0

        return {
            "total_requests": total_requests,
            "in_progress_requests": in_progress,
            "completed_requests": completed,
            "pending_requests": pending,
            "urgent_requests": urgent,
            "documents_processed": total_docs,
            "avg_processing_time": 5,  # Would calculate from historical data
        }

    async def search_requests(
        self,
        db: AsyncSession,
        query_string: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PIARequest]:
        """
        Search requests by text query.

        Args:
            db: Database session
            query_string: Search query
            skip: Pagination offset
            limit: Page size

        Returns:
            List of matching requests
        """
        search_pattern = f"%{query_string}%"

        query = (
            select(PIARequest)
            .where(
                or_(
                    PIARequest.request_number.ilike(search_pattern),
                    PIARequest.requester_name.ilike(search_pattern),
                    PIARequest.description.ilike(search_pattern),
                    PIARequest.requester_organization.ilike(search_pattern),
                )
            )
            .order_by(PIARequest.date_received.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton instance
_request_service: Optional[RequestService] = None


def get_request_service() -> RequestService:
    """Get or create the request service singleton."""
    global _request_service
    if _request_service is None:
        _request_service = RequestService()
    return _request_service
