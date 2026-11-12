"""`GET /api/me/stats/{game}`: the statistics of the browser that asks, for one game.

There are no accounts yet, so "me" is the guest identifier the browser sends in `X-Hajime-Guest`: the same
random value it sent when joining games. Knowing it is what proves a browser played those games, so it is
never shown to anyone else, and this endpoint only returns data tied to the identifier it was given.

The route is the same for every game. What a game's statistics contain comes from its provider
(``app.api.games``)."""

from __future__ import annotations

import uuid
from datetime import date

import msgspec
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.api.games import PROVIDERS
from app.api.routes import client_ip
from app.core import metrics
from app.core.ratelimit import WindowLimiter
from app.japanese.dictionary import Dictionary

router = APIRouter()

STATS_PER_MINUTE = 30


@router.get("/api/me/stats/{game}")
async def my_stats(
    game: str,
    request: Request,
    mode: str = "all",
    x_hajime_guest: str | None = Header(default=None),
) -> Response:
    provider = PROVIDERS.get(game)
    if provider is None:
        raise HTTPException(status_code=404, detail="unknown_game")
    if mode not in provider.modes:
        raise HTTPException(status_code=422, detail="bad_mode")
    limiter: WindowLimiter = request.app.state.limiter
    engine = request.app.state.engine
    if engine is None:
        raise HTTPException(status_code=503, detail="stats_unavailable")  # no database: nothing was stored
    if not x_hajime_guest:
        raise HTTPException(status_code=401, detail="guest_required")
    try:
        guest = uuid.UUID(x_hajime_guest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bad_guest") from exc
    if not await limiter.allow(f"stats:{client_ip(request)}", STATS_PER_MINUTE, 60):
        metrics.RATE_LIMITED.labels("stats").inc()
        raise HTTPException(status_code=429, detail="rate_limited")
    dictionary: Dictionary = request.app.state.dictionary
    view = await provider.view(engine, [guest], mode, dictionary, date.today())
    # Private to the browser that asked: never cached by a proxy or the browser.
    return Response(
        msgspec.json.encode(view), media_type="application/json", headers={"cache-control": "no-store"}
    )
