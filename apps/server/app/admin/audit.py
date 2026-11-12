"""Every change made through the admin leaves a line in the server log: who, what, which row, what changed."""

from __future__ import annotations

from sqladmin.audit import AuditBackend, AuditEntry
from sqladmin.authentication import get_current_user_id
from starlette.requests import Request

from app.core.logging import get_logger

log = get_logger("admin.audit")


class LogAuditBackend(AuditBackend):
    async def log(self, entry: AuditEntry, request: Request) -> None:
        log.info(
            "admin_action",
            admin=get_current_user_id(request),
            action=str(entry.action),
            table=str(entry.identity),
            pk=str(entry.pk),
            changes=entry.changes,
        )
