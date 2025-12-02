"""
Base CRUD service with common database operations.
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseCRUDService(Generic[ModelType]):
    """
    Base class for CRUD operations on database models.

    Provides async database operations with proper error handling
    and transaction management.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize the service with a specific model.

        Args:
            model: SQLAlchemy model class
        """
        self.model = model

    async def create(
        self,
        db: AsyncSession,
        obj_in: Dict[str, Any],
    ) -> ModelType:
        """
        Create a new record.

        Args:
            db: Database session
            obj_in: Dictionary of field values

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get(
        self,
        db: AsyncSession,
        id: int,
        options: Optional[List[Any]] = None,
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            db: Database session
            id: Record ID
            options: SQLAlchemy load options (e.g., selectinload)

        Returns:
            Model instance or None
        """
        query = select(self.model).where(self.model.id == id)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        field_value: Any,
        options: Optional[List[Any]] = None,
    ) -> Optional[ModelType]:
        """
        Get a record by a specific field value.

        Args:
            db: Database session
            field_name: Name of the field to filter on
            field_value: Value to match
            options: SQLAlchemy load options

        Returns:
            Model instance or None
        """
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == field_value)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Any] = None,
        options: Optional[List[Any]] = None,
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering and pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum records to return
            filters: Dictionary of field filters
            order_by: SQLAlchemy ordering expression
            options: SQLAlchemy load options

        Returns:
            List of model instances
        """
        query = select(self.model)

        if filters:
            for field_name, value in filters.items():
                if value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        query = query.where(field == value)

        if options:
            for opt in options:
                query = query.options(opt)

        if order_by is not None:
            query = query.order_by(order_by)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        db: AsyncSession,
        id: int,
        obj_in: Dict[str, Any],
    ) -> Optional[ModelType]:
        """
        Update a record.

        Args:
            db: Database session
            id: Record ID
            obj_in: Dictionary of field values to update

        Returns:
            Updated model instance or None
        """
        # Filter out None values and id
        update_data = {k: v for k, v in obj_in.items() if v is not None and k != "id"}

        if not update_data:
            return await self.get(db, id)

        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.flush()

        return await self.get(db, id)

    async def delete(
        self,
        db: AsyncSession,
        id: int,
    ) -> bool:
        """
        Delete a record.

        Args:
            db: Database session
            id: Record ID

        Returns:
            True if deleted, False if not found
        """
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.flush()
            return True
        return False

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            db: Database session
            filters: Dictionary of field filters

        Returns:
            Count of matching records
        """
        query = select(func.count()).select_from(self.model)

        if filters:
            for field_name, value in filters.items():
                if value is not None:
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        query = query.where(field == value)

        result = await db.execute(query)
        return result.scalar() or 0

    async def exists(
        self,
        db: AsyncSession,
        id: int,
    ) -> bool:
        """
        Check if a record exists.

        Args:
            db: Database session
            id: Record ID

        Returns:
            True if exists
        """
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return (result.scalar() or 0) > 0
