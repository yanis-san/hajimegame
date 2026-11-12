"""What every game records about a finished game, as plain data, whatever the game.

A game's engine and room feed their events to a ``RunRecording`` (each game has its own, next to its
engine); when the game ends it produces a ``GameRecord``: the common part below, plus a ``detail`` that only
that game understands. A ``Recorder`` stores the record (PostgreSQL in production, nothing in development).
Nothing here touches a database or the network, and a recorder never runs on a game's path: ``submit`` only
queues the record.

Privacy: a record holds the nickname a player chose, a random guest identifier their browser generated
(never shown to other players), the interface language, scores, and what the game itself keeps in
``detail``. It holds no address, no device information and no cookie."""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.games.base import GameEvent


@dataclass(frozen=True, slots=True)
class SeatInfo:
    """Who sits at a seat when a game starts."""

    member_id: str
    name: str
    guest_id: uuid.UUID | None = None
    lang: str | None = None
    bot_difficulty: str | None = None

    @property
    def is_bot(self) -> bool:
        return self.bot_difficulty is not None


@dataclass(frozen=True, slots=True)
class PlayerRecord:
    seat: int
    name: str
    guest_id: uuid.UUID | None
    lang: str | None
    is_bot: bool
    bot_difficulty: str | None
    place: int
    score: int
    words: int  # how much the player produced: words found, drawings guessed... (the game defines it)
    longest_word: str
    explosions: int  # times the player lost a life
    avg_response_ms: int | None


@dataclass(frozen=True, slots=True)
class GameRecord:
    """A finished game: ``kind`` names the game ("bomb"), ``mode`` its variant, ``detail`` is its own data."""

    kind: str
    id: uuid.UUID
    room_code: str
    mode: str
    settings: dict[str, Any]
    started_at: datetime  # UTC, naive (the schema stores naive UTC)
    ended_at: datetime
    duration_ms: int
    players: tuple[PlayerRecord, ...]
    detail: object


class RunRecording(Protocol):
    """Collects the events of one running game and turns them into a record when it ends."""

    def on_event(self, event: GameEvent, now: float) -> None: ...

    def finish(
        self, results: Mapping[str, tuple[int, int, int, str]], *, ended_at: datetime, now: float
    ) -> GameRecord:
        """``results`` maps a member id to (place, score, words, longest word)."""
        ...


class Recorder(Protocol):
    """Where finished games go. ``submit`` must return at once and never raise."""

    def submit(self, record: GameRecord) -> None: ...


class NullRecorder:
    """Development and tests without a database: finished games are simply not stored."""

    def submit(self, record: GameRecord) -> None:
        return None


def settings_as_dict(settings: object) -> dict[str, Any]:
    """A game's settings as plain JSON-friendly values."""
    if dataclasses.is_dataclass(settings) and not isinstance(settings, type):
        return dataclasses.asdict(settings)
    return {}
