"""The bomb game's recording: every turn, with its prompt, how it ended and how long it took."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.games.base import GameEvent
from app.games.bomb import events as ev
from app.games.recording import GameRecord, PlayerRecord, SeatInfo

KIND = "bomb"

Outcome = Literal["word", "explosion", "n_ending"]


@dataclass(frozen=True, slots=True)
class BombTurn:
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
class BombDetail:
    """The part of a bomb game's record that only this game has."""

    turns: tuple[BombTurn, ...]


@dataclass(slots=True)
class _OpenTurn:
    turn: int
    member_id: str
    fragment: str
    started: float
    fuse_ms: int
    rejected: int = 0


class BombRecording:
    """Collects the events of one running bomb game."""

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
        self._turns: list[BombTurn] = []
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
            BombTurn(
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
            kind=KIND,
            id=uuid.uuid4(),
            room_code=self._room_code,
            mode=self._mode,
            settings=self._settings,
            started_at=self._started_at,
            ended_at=ended_at,
            duration_ms=max(0, round((now - self._started) * 1000)),
            players=tuple(players),
            detail=BombDetail(turns=tuple(self._turns)),
        )
