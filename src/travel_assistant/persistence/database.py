"""Async database engine and session management for SQLAlchemy + asyncpg.

Provides a lazily-initialised engine, a session factory, and a ``get_session``
context manager used throughout the application for transactional access.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from travel_assistant.config import get_settings

_engine = None
_session_factory = None


def _get_engine():
    """Return the singleton async engine, creating it on first call."""
    global _engine
    if _engine is None:
        kwargs = {"pool_pre_ping": True}
        # NullPool disables connection pooling so each test gets a fresh
        # connection that is fully closed when the test ends.  A persistent
        # pool would keep transactions open across tests and cause isolation
        # failures when the test database is torn down between runs.
        if os.getenv("RUN_INTEGRATION_TESTS") == "1":
            kwargs["poolclass"] = NullPool
        _engine = create_async_engine(get_settings().db.url, **kwargs)
    return _engine


def _get_session_factory():
    """Return the singleton session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional ``AsyncSession``, committing on exit or rolling back on error."""
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables from metadata. For tests only; use alembic in production."""
    from travel_assistant.persistence.models import Base

    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
