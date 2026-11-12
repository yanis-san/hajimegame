from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.test_db_migrations import alembic_config

POSTGRES_URL = os.environ.get("HAJIME_TEST_DATABASE_URL", "")


@pytest.fixture(params=["sqlite", "postgres"])
async def database_url(request: pytest.FixtureRequest, tmp_path: Path) -> AsyncIterator[str]:
    """A fresh database with every migration applied.

    SQLite always runs. PostgreSQL runs only when HAJIME_TEST_DATABASE_URL points at a server, for example
    ``postgresql+asyncpg://hajime:hajime@127.0.0.1:55432/postgres``. Each test then creates its own throw-away
    database there and drops it afterwards.
    """
    if request.param == "sqlite":
        url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
        await asyncio.to_thread(command.upgrade, alembic_config(url), "head")
        yield url
        return

    if not POSTGRES_URL:
        pytest.skip("set HAJIME_TEST_DATABASE_URL to run the tests on PostgreSQL")
    name = f"hajime_test_{uuid.uuid4().hex[:12]}"
    admin = create_async_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
    url = make_url(POSTGRES_URL).set(database=name).render_as_string(hide_password=False)
    try:
        await asyncio.to_thread(command.upgrade, alembic_config(url), "head")
        yield url
    finally:
        async with admin.connect() as connection:
            await connection.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()
