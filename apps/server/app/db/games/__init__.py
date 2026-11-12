"""Per-game persistence. One module per game, registered here.

The common tables (``games``, ``game_players`` in ``app.db.models``) are the same for every game. What only
one game has, such as the bomb game's turns, lives in that game's own tables, defined and read by that
game's module. To add a game: write ``app/db/games/<game>.py`` with its tables and a ``GameStore``, and add
it to ``STORES`` below. Nothing in the common part changes, and one game's tables never mention another's."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.db.games import bomb
from app.db.models import Base
from app.games.recording import GameRecord


class GameStore(Protocol):
    """What a game adds to the database when one of its games is stored."""

    kind: str

    def detail_rows(self, record: GameRecord) -> Sequence[Base]:
        """The game's own rows for ``record``, saved in the same transaction as the common ones."""
        ...


STORES: dict[str, GameStore] = {bomb.STORE.kind: bomb.STORE}


def store_for(kind: str) -> GameStore:
    try:
        return STORES[kind]
    except KeyError:
        raise LookupError(f"no persistence is registered for the game {kind!r}") from None
