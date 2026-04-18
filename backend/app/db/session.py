"""
Async SQLAlchemy engine and session factory.
Import `get_async_session` wherever a DB session is needed.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────

# NullPool is used during testing; production uses QueuePool (default).
_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,  # Detect stale connections
)

# ── Session factory ───────────────────────────────────────────────────────────

_AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context-managed DB session.
    Rolls back automatically on unhandled exceptions.
    """
    async with _AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_engine():
    """Expose engine — used by Alembic env.py and health checks."""
    return _engine
