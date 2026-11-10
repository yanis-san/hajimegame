"""Common game abstractions: clock, players, events and the GameEngine interface.

Nothing here knows about the network, the database or the system clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Clock(Protocol):
    """Monotonic clock in seconds. Injected so games are deterministic and testable."""

    def now(self) -> float: ...


class ManualClock:
    """Clock advanced by hand. Used in tests and simulations."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("clock cannot go backwards")
        self._now += seconds
        return self._now

    def set(self, value: float) -> None:
        if value < self._now:
            raise ValueError("clock cannot go backwards")
        self._now = value


class Phase(StrEnum):
    PLAYING = "playing"
    FINISHED = "finished"


class PlayerKind(StrEnum):
    HUMAN = "human"
    BOT = "bot"


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    """Identity of a participant. Bots and humans are the same to the engine."""

    id: str
    name: str
    kind: PlayerKind = PlayerKind.HUMAN


@dataclass(frozen=True, slots=True, kw_only=True)
class GameEvent:
    """Base class of every event an engine emits."""


class GameEngine(Protocol):
    """Interface every game engine implements, so rooms stay independent of the game played."""

    @property
    def phase(self) -> Phase: ...

    @property
    def next_deadline(self) -> float | None:
        """Time (engine clock) at which ``timeout`` must be called, or None."""

    def start(self) -> list[GameEvent]: ...

    def submit(self, player_id: str, text: str, at: float | None = None) -> list[GameEvent]: ...

    def timeout(self, at: float | None = None, turn: int | None = None) -> list[GameEvent]: ...

    def leave(self, player_id: str, at: float | None = None) -> list[GameEvent]: ...
