"""The operator's admin interface (SQLAdmin), mounted on the game server when it is configured.

It is for the person who runs the site: browse and search what is stored, correct an account, remove a
game, end a session. It is off unless ``HAJIME_ADMIN_PASSWORD_HASH`` is set, needs the database, and is
not part of what players see. See docs/ADR/0008-admin-interface.md."""

from __future__ import annotations

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

from app.admin.audit import LogAuditBackend
from app.admin.auth import AdminAuth
from app.admin.games import VIEWS as GAME_VIEWS
from app.admin.views import VIEWS as SHARED_VIEWS
from app.core.config import AppSettings


def mount_admin(app: FastAPI, engine: AsyncEngine, settings: AppSettings) -> Admin:
    admin = Admin(
        app,
        engine,
        base_url=settings.admin_path,
        title="Hajime admin",
        authentication_backend=AdminAuth(app, settings),
        audit_backend=LogAuditBackend(),
    )
    for view in [*SHARED_VIEWS, *GAME_VIEWS]:
        admin.add_view(view)
    return admin
