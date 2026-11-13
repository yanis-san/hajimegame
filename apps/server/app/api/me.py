"""`GET /api/me/stats/{game}`: the statistics of whoever asks, for one game.

A signed-in player (session cookie) gets the games of every browser linked to their account. A guest sends the
random identifier their browser made, in `X-Hajime-Guest`: knowing it is what proves a browser played those
games, so it is never shown to anyone else, and only data tied to it is returned.

The route is the same for every game. What a game's statistics contain comes from its provider
(``app.api.games``)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import msgspec
from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.api.auth import current_me
from app.api.games import PROVIDERS
from app.api.routes import client_ip
from app.core import metrics
from app.core.ratelimit import WindowLimiter
from app.db import accounts
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
    who = await current_me(request)
    if who is not None:
        # Signed in: the player's games are those of every browser linked to the account.
        guests = await accounts.linked_guests(engine, who.player_id)
    elif not x_hajime_guest:
        raise HTTPException(status_code=401, detail="guest_required")
    else:
        try:
            guests = [uuid.UUID(x_hajime_guest)]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="bad_guest") from exc
    if not await limiter.allow(f"stats:{client_ip(request)}", STATS_PER_MINUTE, 60):
        metrics.RATE_LIMITED.labels("stats").inc()
        raise HTTPException(status_code=429, detail="rate_limited")
    dictionary: Dictionary = request.app.state.dictionary
    view = await provider.view(
        engine, guests, mode, dictionary, datetime.now(UTC).date()
    )  # games are stored in UTC
    # Private to the browser that asked: never cached by a proxy or the browser.
    return Response(
        msgspec.json.encode(view), media_type="application/json", headers={"cache-control": "no-store"}
    )
