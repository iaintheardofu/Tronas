"""
CRUD service for Users.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.services.crud.base_service import BaseCRUDService
from app.models.user import User, UserRole
from app.core.security import get_password_hash, verify_password


class UserService(BaseCRUDService[User]):
    """
    Service for User CRUD operations.
    """

    def __init__(self):
        super().__init__(User)

    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.VIEWER,
        department: Optional[str] = None,
        azure_id: Optional[str] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            db: Database session
            email: User email
            password: Plain text password
            full_name: User's full name
            role: User role
            department: User's department
            azure_id: Azure AD object ID

        Returns:
            Created user
        """
        hashed_password = get_password_hash(password)

        user_data = {
            "email": email.lower(),
            "hashed_password": hashed_password,
            "full_name": full_name,
            "role": role,
            "department": department,
            "azure_id": azure_id,
            "is_active": True,
        }

        return await self.create(db, user_data)

    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> Optional[User]:
        """
        Get user by email address.

        Args:
            db: Database session
            email: User email

        Returns:
            User or None
        """
        return await self.get_by_field(db, "email", email.lower())

    async def get_by_azure_id(
        self,
        db: AsyncSession,
        azure_id: str,
    ) -> Optional[User]:
        """
        Get user by Azure AD object ID.

        Args:
            db: Database session
            azure_id: Azure AD object ID

        Returns:
            User or None
        """
        return await self.get_by_field(db, "azure_id", azure_id)

    async def authenticate(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Args:
            db: Database session
            email: User email
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = await self.get_by_email(db, email)

        if not user:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        # Update last login
        await self.update(
            db,
            user.id,
            {"last_login": datetime.utcnow()}
        )

        return user

    async def update_password(
        self,
        db: AsyncSession,
        user_id: int,
        new_password: str,
    ) -> Optional[User]:
        """
        Update user password.

        Args:
            db: Database session
            user_id: User ID
            new_password: New plain text password

        Returns:
            Updated user or None
        """
        hashed_password = get_password_hash(new_password)

        return await self.update(
            db,
            user_id,
            {"hashed_password": hashed_password}
        )

    async def update_role(
        self,
        db: AsyncSession,
        user_id: int,
        new_role: UserRole,
    ) -> Optional[User]:
        """
        Update user role.

        Args:
            db: Database session
            user_id: User ID
            new_role: New role

        Returns:
            Updated user or None
        """
        return await self.update(db, user_id, {"role": new_role})

    async def deactivate_user(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Updated user or None
        """
        return await self.update(db, user_id, {"is_active": False})

    async def activate_user(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[User]:
        """
        Activate a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Updated user or None
        """
        return await self.update(db, user_id, {"is_active": True})

    async def get_users_by_role(
        self,
        db: AsyncSession,
        role: UserRole,
        active_only: bool = True,
    ) -> List[User]:
        """
        Get users by role.

        Args:
            db: Database session
            role: User role
            active_only: Only return active users

        Returns:
            List of users
        """
        filters = {"role": role}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(db, filters=filters)

    async def get_users_by_department(
        self,
        db: AsyncSession,
        department: str,
        active_only: bool = True,
    ) -> List[User]:
        """
        Get users by department.

        Args:
            db: Database session
            department: Department name
            active_only: Only return active users

        Returns:
            List of users
        """
        filters = {"department": department}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(db, filters=filters)

    async def get_active_users(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Get all active users.

        Args:
            db: Database session
            skip: Pagination offset
            limit: Page size

        Returns:
            List of active users
        """
        return await self.get_multi(
            db,
            skip=skip,
            limit=limit,
            filters={"is_active": True},
            order_by=User.full_name,
        )

    async def search_users(
        self,
        db: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[User]:
        """
        Search users by name or email.

        Args:
            db: Database session
            query: Search query
            skip: Pagination offset
            limit: Page size

        Returns:
            List of matching users
        """
        search_pattern = f"%{query}%"

        stmt = (
            select(User)
            .where(
                and_(
                    User.is_active == True,
                    or_(
                        User.full_name.ilike(search_pattern),
                        User.email.ilike(search_pattern),
                    )
                )
            )
            .order_by(User.full_name)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_from_azure(
        self,
        db: AsyncSession,
        azure_id: str,
        email: str,
        full_name: str,
        department: Optional[str] = None,
    ) -> User:
        """
        Get existing user by Azure ID or create new one.

        Args:
            db: Database session
            azure_id: Azure AD object ID
            email: User email
            full_name: User's full name
            department: User's department

        Returns:
            User (existing or newly created)
        """
        # Try to find by Azure ID first
        user = await self.get_by_azure_id(db, azure_id)
        if user:
            # Update any changed fields
            update_data = {}
            if user.email.lower() != email.lower():
                update_data["email"] = email.lower()
            if user.full_name != full_name:
                update_data["full_name"] = full_name
            if department and user.department != department:
                update_data["department"] = department

            if update_data:
                update_data["last_login"] = datetime.utcnow()
                await self.update(db, user.id, update_data)

            return user

        # Try to find by email (might exist from before Azure integration)
        user = await self.get_by_email(db, email)
        if user:
            # Link existing user to Azure ID
            await self.update(
                db,
                user.id,
                {
                    "azure_id": azure_id,
                    "last_login": datetime.utcnow(),
                }
            )
            return user

        # Create new user
        import secrets
        random_password = secrets.token_urlsafe(32)

        return await self.create_user(
            db=db,
            email=email,
            password=random_password,
            full_name=full_name,
            role=UserRole.VIEWER,
            department=department,
            azure_id=azure_id,
        )

    async def get_user_statistics(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Get user statistics.

        Args:
            db: Database session

        Returns:
            User statistics
        """
        # Total users
        total_query = select(func.count()).select_from(User)
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # Active users
        active_query = (
            select(func.count())
            .select_from(User)
            .where(User.is_active == True)
        )
        active_result = await db.execute(active_query)
        active = active_result.scalar() or 0

        # Users by role
        role_query = (
            select(User.role, func.count().label("count"))
            .where(User.is_active == True)
            .group_by(User.role)
        )
        role_result = await db.execute(role_query)
        by_role = {row[0].value: row[1] for row in role_result.all()}

        return {
            "total_users": total,
            "active_users": active,
            "inactive_users": total - active,
            "users_by_role": by_role,
        }


# Singleton instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get or create the user service singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
