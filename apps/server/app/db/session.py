"""Database engine creation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _enforce_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    """SQLite ignores foreign keys unless told otherwise; PostgreSQL always enforces them. Turning them on
    makes the test database behave like production: a deleted game takes its turns with it, and a bad
    reference fails."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_engine(url: str, pool_size: int = 5) -> AsyncEngine:
    """An async engine. PostgreSQL gets a small pool that checks connections before use (a restart of the
    database must not poison the pool); SQLite (tests) takes the defaults, with foreign keys enforced."""
    if url.startswith("sqlite"):
        engine = create_async_engine(url)
        event.listen(engine.sync_engine, "connect", _enforce_foreign_keys)
        return engine
    return create_async_engine(url, pool_size=pool_size, max_overflow=5, pool_pre_ping=True)
