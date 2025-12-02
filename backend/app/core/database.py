from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from loguru import logger

from app.core.config import settings

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    metadata = metadata


# Lazy-loaded engine and session
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        import os
        # Try environment variable directly first
        db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL

        if not db_url or len(db_url) < 10:
            logger.error(f"DATABASE_URL is not set or invalid. Value: '{db_url}'")
            logger.info(f"Available env vars: {list(os.environ.keys())}")
            raise ValueError("DATABASE_URL environment variable must be set")

        # Clean up URL if needed
        db_url = db_url.strip()
        if db_url.startswith("="):
            db_url = db_url[1:]

        logger.info(f"Creating database engine for: {db_url[:60]}...")
        _engine = create_async_engine(
            db_url,
            echo=settings.DATABASE_ECHO,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_async_session_maker() -> async_sessionmaker:
    """Get or create the async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize the database (create tables if they don't exist)."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
        # Don't fail startup if DB isn't ready - tables may already exist


# For backwards compatibility
engine = property(lambda self: get_engine())
AsyncSessionLocal = property(lambda self: get_async_session_maker())
