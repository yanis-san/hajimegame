"""Database engine creation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(url: str, pool_size: int = 5) -> AsyncEngine:
    """An async engine. PostgreSQL gets a small pool that checks connections before use (a restart of the
    database must not poison the pool); SQLite (tests) takes the defaults."""
    if url.startswith("sqlite"):
        return create_async_engine(url)
    return create_async_engine(url, pool_size=pool_size, max_overflow=5, pool_pre_ping=True)
