"""What happened in a finished game, as plain data.

The room feeds the engine's events to a ``GameRecording``; at ``game_over`` it becomes a ``GameRecord`` that a
``Recorder`` stores (PostgreSQL in production, nothing in development). Nothing here touches a database or the
network, and a recorder never runs on the game's path: ``submit`` only queues the record.

Privacy: a record holds the nickname a player chose, a random guest identifier their browser generated (never
shown to other players), the interface language, scores, and the words played. It holds no address, no device
information and no cookie.
"""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from app.games.base import GameEvent
from app.games.bomb import events as ev

Outcome = Literal["word", "explosion", "n_ending"]


@dataclass(frozen=True, slots=True)
class SeatInfo:
    """Who sits at a seat when the game starts."""

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
    words: int
    longest_word: str
    explosions: int
    avg_response_ms: int | None


@dataclass(frozen=True, slots=True)
class TurnRecord:
    turn: int
    seat: int
    fragment: str
    outcome: Outcome
    word: str  # empty when the bomb exploded
    reading: str
    response_ms: int | None  # time taken to find the word; None when the bomb exploded
    fuse_ms: int
    rejected_attempts: int  # words refused during this turn


@dataclass(frozen=True, slots=True)
class GameRecord:
    id: uuid.UUID
    room_code: str
    mode: str
    settings: dict[str, Any]
    started_at: datetime  # UTC, naive (the schema stores naive UTC)
    ended_at: datetime
    duration_ms: int
    players: tuple[PlayerRecord, ...]
    turns: tuple[TurnRecord, ...]


class Recorder(Protocol):
    """Where finished games go. ``submit`` must return at once and never raise."""

    def submit(self, record: GameRecord) -> None: ...


class NullRecorder:
    """Development and tests without a database: finished games are simply not stored."""

    def submit(self, record: GameRecord) -> None:
        return None


@dataclass(slots=True)
class _OpenTurn:
    turn: int
    member_id: str
    fragment: str
    started: float
    fuse_ms: int
    rejected: int = 0


class GameRecording:
    """Collects the events of one running game."""

    def __init__(
        self,
        room_code: str,
        mode: str,
        settings: Mapping[str, Any],
        seats: Sequence[SeatInfo],
        *,
        started_at: datetime,
        started: float,
    ) -> None:
        self._room_code = room_code
        self._mode = mode
        self._settings = dict(settings)
        self._seats = list(seats)
        self._seat_of = {seat.member_id: index for index, seat in enumerate(seats)}
        self._started_at = started_at
        self._started = started
        self._open: _OpenTurn | None = None
        self._turns: list[TurnRecord] = []
        self._explosions = [0] * len(seats)
        self._responses: list[list[int]] = [[] for _ in seats]

    def on_event(self, event: GameEvent, now: float) -> None:
        if isinstance(event, ev.TurnStarted):
            self._open = _OpenTurn(
                turn=event.turn,
                member_id=event.player_id,
                fragment=event.fragment,
                started=event.deadline - event.fuse_seconds,
                fuse_ms=round(event.fuse_seconds * 1000),
            )
        elif isinstance(event, ev.WordRejected):
            if self._open is not None and self._open.turn == event.turn:
                self._open.rejected += 1
        elif isinstance(event, ev.WordAccepted):
            current = self._open
            if current is not None and current.turn == event.turn:
                response = max(0, round((now - current.started) * 1000))
                seat = self._seat_of.get(event.player_id)
                if seat is not None:
                    self._responses[seat].append(response)
                self._close(current, "word", word=event.word, reading=event.reading, response_ms=response)
        elif isinstance(event, ev.Explosion):
            current = self._open
            seat = self._seat_of.get(event.player_id)
            if seat is not None:
                self._explosions[seat] += 1
            if current is not None and current.turn == event.turn:
                self._close(current, "n_ending" if event.cause == "n_ending" else "explosion")

    def _close(
        self,
        current: _OpenTurn,
        outcome: Outcome,
        *,
        word: str = "",
        reading: str = "",
        response_ms: int | None = None,
    ) -> None:
        self._turns.append(
            TurnRecord(
                turn=current.turn,
                seat=self._seat_of.get(current.member_id, -1),
                fragment=current.fragment,
                outcome=outcome,
                word=word,
                reading=reading,
                response_ms=response_ms,
                fuse_ms=current.fuse_ms,
                rejected_attempts=current.rejected,
            )
        )
        self._open = None

    def finish(
        self,
        results: Mapping[str, tuple[int, int, int, str]],
        *,
        ended_at: datetime,
        now: float,
    ) -> GameRecord:
        """``results`` maps a member id to (place, score, words, longest word)."""
        players = []
        for index, seat in enumerate(self._seats):
            place, score, words, longest = results.get(seat.member_id, (len(self._seats), 0, 0, ""))
            times = self._responses[index]
            players.append(
                PlayerRecord(
                    seat=index,
                    name=seat.name,
                    guest_id=seat.guest_id,
                    lang=seat.lang,
                    is_bot=seat.is_bot,
                    bot_difficulty=seat.bot_difficulty,
                    place=place,
                    score=score,
                    words=words,
                    longest_word=longest,
                    explosions=self._explosions[index],
                    avg_response_ms=round(sum(times) / len(times)) if times else None,
                )
            )
        return GameRecord(
            id=uuid.uuid4(),
            room_code=self._room_code,
            mode=self._mode,
            settings=self._settings,
            started_at=self._started_at,
            ended_at=ended_at,
            duration_ms=max(0, round((now - self._started) * 1000)),
            players=tuple(players),
            turns=tuple(self._turns),
        )


def settings_as_dict(settings: object) -> dict[str, Any]:
    """The game settings as plain JSON-friendly values."""
    if dataclasses.is_dataclass(settings) and not isinstance(settings, type):
        return dataclasses.asdict(settings)
    return {}
