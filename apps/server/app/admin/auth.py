"""Who may open the admin: one operator, with a password that only exists on the server as an Argon2 hash.

Wrong guesses are limited per address and overall; a wrong username costs as much time as a wrong
password. The session is a signed cookie (SameSite=Strict, Secure in production) that expires after a
few hours."""

from __future__ import annotations

import secrets
import time

from fastapi import FastAPI
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.api.routes import client_ip_for
from app.core import metrics
from app.core.config import AppSettings
from app.core.passwords import verify_password
from app.core.ratelimit import WindowLimiter

LOGIN_PER_ADDRESS = 5  # per 15 minutes
LOGIN_OVERALL = 30  # per hour, whoever asks: a slow guess spread over many addresses is still stopped


class AdminAuth(AuthenticationBackend):
    def __init__(self, app: FastAPI, settings: AppSettings) -> None:
        assert settings.admin_secret is not None and settings.admin_password_hash is not None
        super().__init__(
            secret_key=settings.admin_secret,
            session_cookie="hajime_admin",
            max_age=settings.admin_session_hours * 3600,
            same_site="strict",
            https_only=settings.cookie_secure,
        )
        self._app = app  # the main app: this one runs mounted, so its own state is not the game's
        self._settings = settings
        self._password_hash: str = settings.admin_password_hash

    async def login(self, request: Request) -> bool:
        limiter: WindowLimiter = self._app.state.limiter
        ip = client_ip_for(self._settings, request)
        if not (
            await limiter.allow(f"admin-login:{ip}", LOGIN_PER_ADDRESS, 900)
            and await limiter.allow("admin-login:all", LOGIN_OVERALL, 3600)
        ):
            metrics.RATE_LIMITED.labels("admin_login").inc()
            return False
        form = await request.form()
        username, password = str(form.get("username", "")), str(form.get("password", ""))
        known = secrets.compare_digest(username.encode(), self._settings.admin_username.encode())
        # The password is always verified (against the real hash even for a wrong username), so both mistakes
        # take the same time; the answer is the same too.
        valid = await verify_password(self._password_hash, password)
        if not (known and valid):
            return False
        request.session.update({"admin": self._settings.admin_username, "at": int(time.time())})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        admin = request.session.get("admin")
        issued = request.session.get("at")
        if admin != self._settings.admin_username or not isinstance(issued, int):
            return False
        # The signed cookie already expires (max_age); this also covers a changed setting.
        return time.time() - issued < self._settings.admin_session_hours * 3600

    async def get_user_id(self, request: Request) -> str | None:
        admin = request.session.get("admin")
        return str(admin) if admin else None
