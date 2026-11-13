"""Application settings, read from environment variables prefixed with HAJIME_."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAJIME_", env_file=".env", extra="ignore")

    env: str = "dev"
    # PostgreSQL, e.g. postgresql+asyncpg://user:password@host:5432/hajime. Empty: the game runs without a
    # database and finished games are simply not stored (development, tests).
    database_url: str | None = Field(default=None, repr=False)
    db_pool_size: int = 5
    redis_url: str | None = None
    sentry_dsn: str | None = None
    instance_id: str = "local"

    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://localhost:3000",
        ]
    )
    allow_missing_origin: bool = True  # non-browser clients (tests, curl); disable in production
    cookie_secure: bool = False
    trust_proxy_headers: bool = False  # honour Fly-Client-IP / X-Forwarded-For behind a trusted proxy
    # /metrics is hidden in production unless a token is set; then it needs `Authorization: Bearer <token>`
    metrics_token: str | None = Field(default=None, repr=False)

    # Accounts. Signing up needs the captcha: with a Cloudflare Turnstile secret it is checked, without one
    # (development, tests) it is skipped; in production a missing secret closes sign-up instead.
    turnstile_secret: str | None = Field(default=None, repr=False)
    session_days: int = 30

    # Admin interface (SQLAdmin) for the operator, off unless a password hash is set. Make the three
    # values with
    # `uv run python -m app.admin.passwd`. It needs the database; the secret signs the admin's session cookie.
    admin_path: str = "/admin"
    admin_username: str = "admin"
    admin_password_hash: str | None = Field(default=None, repr=False)
    admin_secret: str | None = Field(default=None, repr=False)
    admin_session_hours: int = 8

    # E-mail (confirming an address). Off unless the SMTP server is described; the password is the mailbox's.
    # `public_url` is the address of the site, used in the links inside the messages.
    public_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = Field(default=None, repr=False)
    smtp_from: str | None = None  # defaults to the login
    smtp_security: Literal["ssl", "starttls", "none"] = "ssl"

    # Rooms
    max_players_per_room: int = 8
    max_spectators_per_room: int = 20
    max_rooms_per_ip: int = 5
    max_rooms_total: int = 2_000
    grace_seconds: float = 30.0
    countdown_seconds: float = 3.0
    room_idle_seconds: float = 300.0
    heartbeat_seconds: float = 15.0
    outbound_queue_size: int = 256

    # Rate limits
    messages_per_second: float = 25.0
    message_burst: int = 40
    room_creations_per_minute: int = 10
    join_attempts_per_minute: int = 30
    invalid_messages_before_kick: int = 20

    # CPU players: build the word index at startup (a few seconds in the background)
    preload_bots: bool = True

    # Fragment generation
    min_fragment_words: int = 80

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @field_validator(
        "admin_password_hash",
        "admin_secret",
        "turnstile_secret",
        "database_url",
        "smtp_host",
        "smtp_user",
        "smtp_password",
        "smtp_from",
        "public_url",
        mode="before",
    )
    @classmethod
    def _empty_means_unset(cls, value: object) -> object:
        """Docker compose passes an unset optional value as an empty string."""
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def email_enabled(self) -> bool:
        return self.smtp_host is not None

    @model_validator(mode="after")
    def _check_email(self) -> AppSettings:
        """A mail server is all or nothing: half a description would silently send nothing."""
        if self.smtp_host is None:
            return self
        problems: list[str] = []
        if not self.smtp_user or not self.smtp_password:
            problems.append("HAJIME_SMTP_USER and HAJIME_SMTP_PASSWORD are needed with HAJIME_SMTP_HOST")
        if not self.public_url or not self.public_url.startswith(("https://", "http://")):
            problems.append("HAJIME_PUBLIC_URL (the site's address, for the links in the messages) is needed")
        elif self.is_prod and not self.public_url.startswith("https://"):
            problems.append("HAJIME_PUBLIC_URL must be an https:// address in production")
        if self.is_prod and self.smtp_security == "none":
            problems.append("HAJIME_SMTP_SECURITY=none is not allowed in production")
        if problems:
            raise ValueError("invalid e-mail settings: " + "; ".join(problems))
        return self

    @property
    def admin_enabled(self) -> bool:
        return self.admin_password_hash is not None

    @model_validator(mode="after")
    def _check_admin(self) -> AppSettings:
        """The admin is all or nothing: a password without a database or a strong secret does not start."""
        if self.admin_password_hash is None:
            return self
        problems: list[str] = []
        if not self.database_url:
            problems.append("HAJIME_ADMIN_PASSWORD_HASH needs HAJIME_DATABASE_URL")
        if not self.admin_password_hash.startswith("$argon2"):
            problems.append("HAJIME_ADMIN_PASSWORD_HASH must be an Argon2 hash (see app.admin.passwd)")
        if not self.admin_secret or len(self.admin_secret) < 32:
            problems.append("HAJIME_ADMIN_SECRET must be at least 32 characters")
        if not re.fullmatch(r"/[a-z0-9][a-z0-9_-]*", self.admin_path):
            problems.append("HAJIME_ADMIN_PATH must look like /admin")
        if problems:
            raise ValueError("invalid admin settings: " + "; ".join(problems))
        return self

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> AppSettings:
        """A production server that would accept any origin, or trust placeholder ones, does not start."""
        if not self.is_prod:
            return self
        problems: list[str] = []
        if not self.allowed_origins:
            problems.append("HAJIME_ALLOWED_ORIGINS is empty")
        for origin in self.allowed_origins:
            host = origin.removeprefix("https://")
            if not origin.startswith("https://") or "localhost" in host or "example" in host or "*" in origin:
                problems.append(f"HAJIME_ALLOWED_ORIGINS has a non-production origin: {origin}")
        if self.allow_missing_origin:
            problems.append("HAJIME_ALLOW_MISSING_ORIGIN must be false")
        if not self.cookie_secure:
            problems.append("HAJIME_COOKIE_SECURE must be true (the sign-in cookie only travels over https)")
        if problems:
            raise ValueError("unsafe production settings: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
