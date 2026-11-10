"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.routes import router as api_router
from app.core.config import AppSettings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import MemoryWindowLimiter, RedisWindowLimiter, WindowLimiter
from app.core.security import SecurityHeadersMiddleware
from app.games.bomb.settings import LEVELS
from app.japanese.dictionary import Dictionary
from app.japanese.fragments import FragmentTable, playable_table
from app.realtime.clock import RoomClock, SystemClock
from app.realtime.manager import RoomManager
from app.realtime.registry import MemoryRegistry, RedisRegistry, RoomRegistry
from app.realtime.ws import router as ws_router

log = get_logger("app")


@lru_cache
def load_dictionary() -> Dictionary:
    return Dictionary.load()


def build_tables(dictionary: Dictionary, min_words: int) -> dict[str, FragmentTable]:
    return {level: playable_table(dictionary.fragment_buckets, level, min_words) for level in LEVELS}


def create_app(
    settings: AppSettings | None = None,
    *,
    registry: RoomRegistry | None = None,
    clock: RoomClock | None = None,
    limiter: WindowLimiter | None = None,
    dictionary: Dictionary | None = None,
    redis: Redis | None = None,
) -> FastAPI:
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(cfg.env)
        words: Dictionary = dictionary if dictionary is not None else await asyncio.to_thread(load_dictionary)
        tables = build_tables(words, cfg.min_fragment_words)
        client = redis
        if client is None and cfg.redis_url:
            client = Redis.from_url(cfg.redis_url)
        the_registry = registry or (RedisRegistry(client) if client is not None else MemoryRegistry())
        the_limiter = limiter or (RedisWindowLimiter(client) if client is not None else MemoryWindowLimiter())
        manager = RoomManager(cfg, words, tables, the_registry, clock or SystemClock())
        manager.start()
        app.state.settings = cfg
        app.state.dictionary = words
        app.state.manager = manager
        app.state.limiter = the_limiter
        app.state.redis = client
        log.info("started", instance=manager.instance_id, words=len(words), redis=client is not None)
        try:
            yield
        finally:
            await manager.shutdown()
            if client is not None and redis is None:
                await client.aclose()

    app = FastAPI(
        title="Hajime Game", version="0.1.0", lifespan=lifespan, docs_url=None if cfg.is_prod else "/docs"
    )
    app.state.settings = cfg
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-hajime-client"],
        allow_credentials=False,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=cfg.is_prod)
    app.include_router(api_router)
    app.include_router(ws_router)
    return app
