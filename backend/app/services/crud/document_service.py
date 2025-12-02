"""
CRUD service for Documents.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload
import hashlib

from app.services.crud.base_service import BaseCRUDService
from app.models.document import (
    Document, DocumentType, DocumentStatus, DocumentClassification as DocClassEnum,
    DocumentClassification as DocumentClassificationModel
)


class DocumentService(BaseCRUDService[Document]):
    """
    Service for Document CRUD operations.
    """

    def __init__(self):
        super().__init__(Document)

    async def create_document(
        self,
        db: AsyncSession,
        request_id: int,
        filename: str,
        file_path: str,
        document_type: DocumentType,
        source: str,
        source_id: Optional[str] = None,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Document:
        """
        Create a new document record.

        Args:
            db: Database session
            request_id: Associated PIA request ID
            filename: Document filename
            file_path: Storage path
            document_type: Type of document
            source: Source system (sharepoint, onedrive, outlook)
            source_id: ID in source system
            file_size: Size in bytes
            file_hash: SHA-256 hash
            metadata: Additional metadata

        Returns:
            Created document
        """
        doc_data = {
            "pia_request_id": request_id,
            "filename": filename,
            "file_path": file_path,
            "document_type": document_type,
            "source": source,
            "source_id": source_id,
            "file_size": file_size,
            "file_hash": file_hash,
            "source_metadata": metadata or {},
            "status": DocumentStatus.PENDING,
        }

        return await self.create(db, doc_data)

    async def get_documents_for_request(
        self,
        db: AsyncSession,
        request_id: int,
        include_duplicates: bool = False,
        status: Optional[DocumentStatus] = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[Document]:
        """
        Get all documents for a PIA request.

        Args:
            db: Database session
            request_id: PIA request ID
            include_duplicates: Whether to include duplicates
            status: Filter by status
            skip: Pagination offset
            limit: Page size

        Returns:
            List of documents
        """
        query = select(Document).where(Document.pia_request_id == request_id)

        if not include_duplicates:
            query = query.where(Document.is_duplicate == False)

        if status:
            query = query.where(Document.status == status)

        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_unclassified_documents(
        self,
        db: AsyncSession,
        request_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Document]:
        """
        Get documents that haven't been classified yet.

        Args:
            db: Database session
            request_id: Optional filter by request
            limit: Maximum documents to return

        Returns:
            List of unclassified documents
        """
        query = select(Document).where(
            and_(
                Document.ai_classification == None,
                Document.is_duplicate == False,
                Document.extracted_text != None,
            )
        )

        if request_id:
            query = query.where(Document.pia_request_id == request_id)

        query = query.order_by(Document.created_at.asc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_documents_needing_extraction(
        self,
        db: AsyncSession,
        request_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Document]:
        """
        Get documents that need text extraction.

        Args:
            db: Database session
            request_id: Optional filter by request
            limit: Maximum documents to return

        Returns:
            List of documents needing extraction
        """
        query = select(Document).where(
            and_(
                Document.extracted_text == None,
                Document.is_duplicate == False,
            )
        )

        if request_id:
            query = query.where(Document.pia_request_id == request_id)

        query = query.order_by(Document.created_at.asc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_extracted_text(
        self,
        db: AsyncSession,
        document_id: int,
        extracted_text: str,
        page_count: int = 1,
        word_count: Optional[int] = None,
    ) -> Optional[Document]:
        """
        Update document with extracted text.

        Args:
            db: Database session
            document_id: Document ID
            extracted_text: Extracted text content
            page_count: Number of pages
            word_count: Word count

        Returns:
            Updated document or None
        """
        update_data = {
            "extracted_text": extracted_text,
            "page_count": page_count,
        }

        if word_count:
            update_data["word_count"] = word_count

        return await self.update(db, document_id, update_data)

    async def update_classification(
        self,
        db: AsyncSession,
        document_id: int,
        classification: str,
        confidence: float,
        exemptions: Optional[List[Dict]] = None,
        redaction_needed: bool = False,
        redaction_areas: Optional[List[Dict]] = None,
        reasoning: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Update document AI classification.

        Args:
            db: Database session
            document_id: Document ID
            classification: Classification result
            confidence: Confidence score (0-1)
            exemptions: List of exemption details
            redaction_needed: Whether redaction is needed
            redaction_areas: Areas requiring redaction
            reasoning: AI reasoning

        Returns:
            Updated document or None
        """
        update_data = {
            "ai_classification": classification,
            "ai_confidence": confidence,
            "exemptions_detected": exemptions or [],
            "redaction_required": redaction_needed,
            "redaction_areas": redaction_areas or [],
            "classification_reasoning": reasoning,
            "status": DocumentStatus.CLASSIFIED,
        }

        return await self.update(db, document_id, update_data)

    async def submit_human_review(
        self,
        db: AsyncSession,
        document_id: int,
        final_classification: str,
        reviewed_by: int,
        review_notes: Optional[str] = None,
        approved_redactions: Optional[List[Dict]] = None,
    ) -> Optional[Document]:
        """
        Submit human review for a document.

        Args:
            db: Database session
            document_id: Document ID
            final_classification: Final classification decision
            reviewed_by: User ID of reviewer
            review_notes: Review notes
            approved_redactions: Approved redaction areas

        Returns:
            Updated document or None
        """
        update_data = {
            "final_classification": final_classification,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.utcnow(),
            "review_notes": review_notes,
            "status": DocumentStatus.REVIEWED,
        }

        if approved_redactions is not None:
            update_data["redaction_areas"] = approved_redactions

        return await self.update(db, document_id, update_data)

    async def mark_as_duplicate(
        self,
        db: AsyncSession,
        document_id: int,
        duplicate_of_id: int,
    ) -> Optional[Document]:
        """
        Mark a document as a duplicate.

        Args:
            db: Database session
            document_id: Document ID to mark
            duplicate_of_id: ID of the original document

        Returns:
            Updated document or None
        """
        return await self.update(
            db,
            document_id,
            {
                "is_duplicate": True,
                "duplicate_of_id": duplicate_of_id,
            }
        )

    async def find_duplicate_by_hash(
        self,
        db: AsyncSession,
        file_hash: str,
        request_id: int,
        exclude_id: Optional[int] = None,
    ) -> Optional[Document]:
        """
        Find a document by file hash to detect duplicates.

        Args:
            db: Database session
            file_hash: SHA-256 hash
            request_id: PIA request ID
            exclude_id: Document ID to exclude

        Returns:
            Matching document or None
        """
        query = select(Document).where(
            and_(
                Document.file_hash == file_hash,
                Document.pia_request_id == request_id,
                Document.is_duplicate == False,
            )
        )

        if exclude_id:
            query = query.where(Document.id != exclude_id)

        query = query.order_by(Document.created_at.asc()).limit(1)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_document_statistics(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Dict[str, Any]:
        """
        Get document statistics for a request.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            Document statistics
        """
        # Total documents
        total_query = (
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                )
            )
        )
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # Total pages
        pages_query = (
            select(func.sum(Document.page_count))
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                )
            )
        )
        pages_result = await db.execute(pages_query)
        total_pages = pages_result.scalar() or 0

        # Classified count
        classified_query = (
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                    Document.ai_classification != None,
                )
            )
        )
        classified_result = await db.execute(classified_query)
        classified = classified_result.scalar() or 0

        # Reviewed count
        reviewed_query = (
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                    Document.final_classification != None,
                )
            )
        )
        reviewed_result = await db.execute(reviewed_query)
        reviewed = reviewed_result.scalar() or 0

        # Duplicates count
        dupes_query = (
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == True,
                )
            )
        )
        dupes_result = await db.execute(dupes_query)
        duplicates = dupes_result.scalar() or 0

        # Redaction required count
        redaction_query = (
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                    Document.redaction_required == True,
                )
            )
        )
        redaction_result = await db.execute(redaction_query)
        needs_redaction = redaction_result.scalar() or 0

        return {
            "total_documents": total,
            "total_pages": total_pages,
            "classified_documents": classified,
            "reviewed_documents": reviewed,
            "duplicates_found": duplicates,
            "needs_redaction": needs_redaction,
            "classification_progress": round((classified / total * 100) if total > 0 else 0, 1),
            "review_progress": round((reviewed / total * 100) if total > 0 else 0, 1),
        }

    async def get_classification_summary(
        self,
        db: AsyncSession,
        request_id: int,
    ) -> Dict[str, int]:
        """
        Get classification breakdown for a request.

        Args:
            db: Database session
            request_id: PIA request ID

        Returns:
            Classification counts by category
        """
        query = (
            select(
                Document.ai_classification,
                func.count().label("count")
            )
            .where(
                and_(
                    Document.pia_request_id == request_id,
                    Document.is_duplicate == False,
                    Document.ai_classification != None,
                )
            )
            .group_by(Document.ai_classification)
        )

        result = await db.execute(query)
        rows = result.all()

        return {row[0]: row[1] for row in rows}


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create the document service singleton."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
