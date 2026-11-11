"""Application settings, read from environment variables prefixed with HAJIME_."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAJIME_", env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://hajime:hajime@localhost:5432/hajime"
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


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
