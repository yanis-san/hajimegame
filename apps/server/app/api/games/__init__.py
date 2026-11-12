"""The statistics each game offers, registered by the game's name.

``GET /api/me/stats/{game}`` is the same for every game: it finds the player's identity, applies the rate
limit, and asks the game's ``StatsProvider`` for its view. What a game's statistics contain, and how they
are computed, stays in that game's module (``app/api/games/<game>.py``, with its queries in
``app/db/games/<game>.py``). To add a game, write its provider and add it to ``PROVIDERS``: the route, the
rate limit and the checks are already there."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Protocol

import msgspec
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.games import bomb
from app.japanese.dictionary import Dictionary


class StatsProvider(Protocol):
    """One game's statistics."""

    @property
    def modes(self) -> tuple[str, ...]:
        """The variants a player can filter by; "all" is the default."""
        ...

    async def view(
        self,
        engine: AsyncEngine,
        guest_ids: Sequence[uuid.UUID],
        mode: str,
        dictionary: Dictionary,
        today: date,
    ) -> msgspec.Struct:
        """The game's own statistics view for these guest identifiers."""
        ...


PROVIDERS: dict[str, StatsProvider] = {"bomb": bomb.PROVIDER}
