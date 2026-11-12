"""REST routes: health, metrics and room creation."""

from __future__ import annotations

import asyncio
import secrets
from typing import Any, Literal

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core import metrics
from app.core.config import AppSettings
from app.core.ratelimit import WindowLimiter
from app.core.security import require_same_site_request
from app.realtime.manager import CapacityError, RoomManager

router = APIRouter()


class CreateRoomBody(BaseModel):
    mode: Literal["classic", "shiritori"] = "classic"


class CreatedRoom(BaseModel):
    code: str
    ws_path: str


def client_ip(request: Request) -> str:
    settings: AppSettings = request.app.state.settings
    return client_ip_for(settings, request)


def client_ip_for(settings: AppSettings, request: Request) -> str:
    """The caller's address. ``request.app`` is not the main app inside a mounted one (the admin), so the
    settings are passed in."""
    if settings.trust_proxy_headers:
        for header in ("fly-client-ip", "x-forwarded-for"):
            value = request.headers.get(header)
            if value:
                return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    checks: dict[str, bool] = {"dictionary": request.app.state.dictionary is not None}
    # CPU players need their word index: it is built in the background at startup (a few seconds)
    manager: RoomManager = request.app.state.manager
    settings: AppSettings = request.app.state.settings
    checks["bots"] = manager.candidates is not None or not settings.preload_bots
    engine = request.app.state.engine
    if engine is not None:
        try:
            async with engine.connect() as connection:
                await asyncio.wait_for(connection.execute(sa.text("SELECT 1")), 3)
            checks["database"] = True
        except Exception:
            checks["database"] = False
    redis = request.app.state.redis
    if redis is not None:
        try:
            checks["redis"] = bool(await redis.ping())
        except Exception:
            checks["redis"] = False
    ok = all(checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503
    )


@router.get("/metrics")
async def prometheus(request: Request) -> Response:
    settings: AppSettings = request.app.state.settings
    token = settings.metrics_token
    if settings.is_prod and not token:
        raise HTTPException(status_code=404)  # no token configured: not exposed at all
    if token:
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not secrets.compare_digest(given.encode(), token.encode()):
            raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
    return Response(metrics.render(), media_type="text/plain; version=0.0.4")


@router.post(
    "/api/rooms",
    response_model=CreatedRoom,
    status_code=201,
    dependencies=[Depends(require_same_site_request)],
)
async def create_room(request: Request, body: CreateRoomBody | None = None) -> CreatedRoom:
    settings: AppSettings = request.app.state.settings
    manager: RoomManager = request.app.state.manager
    limiter: WindowLimiter = request.app.state.limiter
    ip = client_ip(request)
    if not await limiter.allow(f"create:{ip}", settings.room_creations_per_minute, 60):
        metrics.RATE_LIMITED.labels("create_room").inc()
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        room = await manager.create(ip, (body or CreateRoomBody()).mode)
    except CapacityError as exc:
        raise HTTPException(
            status_code=429 if exc.kind == "too_many_rooms" else 503, detail=exc.kind
        ) from exc
    return CreatedRoom(code=room.code, ws_path=f"/ws/{room.code}")


@router.get("/api/rooms/{code}")
async def room_info(code: str, request: Request) -> dict[str, Any]:
    manager: RoomManager = request.app.state.manager
    settings: AppSettings = request.app.state.settings
    limiter: WindowLimiter = request.app.state.limiter
    if not await limiter.allow(f"lookup:{client_ip(request)}", settings.join_attempts_per_minute * 2, 60):
        raise HTTPException(status_code=429, detail="rate_limited")
    resolved = await manager.resolve(code)
    if resolved is None:
        raise HTTPException(status_code=404, detail="room_not_found")
    if isinstance(resolved, str):
        return {"code": code.upper(), "remote": True}
    return resolved.summary()
