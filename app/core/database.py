"""
Async SQLAlchemy database setup.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "debug",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Celery-specific engine: No pooling to avoid event loop conflicts
# Each task gets its own connection, preventing "Future attached to different loop" errors
celery_async_engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "debug",
    poolclass=NullPool,
    pool_pre_ping=True,
)

# Async session factory for FastAPI
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Celery-specific session factory: No pooling
celery_async_session_maker = async_sessionmaker(
    celery_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for Celery tasks."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_celery_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for Celery tasks using no-pool connection.
    This prevents "Future attached to a different loop" errors.
    """
    async with celery_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables and extensions."""
    from sqlalchemy import text

    async with async_engine.begin() as conn:
        # Enable extensions
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))

        # Import all models to register them
        from app.models import article, source, publish_log, setting, price_history, prediction, prediction_models, token_usage, distribution  # noqa: F401

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
    logger.info("Database connections closed")
