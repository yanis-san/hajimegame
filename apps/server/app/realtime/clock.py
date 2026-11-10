"""Room clocks. The room clock is monotonic seconds; ``scale`` speeds time up for tests only."""

from __future__ import annotations

import time
from typing import Protocol


class RoomClock(Protocol):
    def now(self) -> float: ...

    def real_delay(self, game_seconds: float) -> float:
        """Convert a game-time delay into real seconds to sleep."""


class SystemClock:
    def now(self) -> float:
        return time.monotonic()

    def real_delay(self, game_seconds: float) -> float:
        return game_seconds


class ScaledClock:
    """Runs ``scale`` times faster than real time (integration tests use it to avoid 5 s fuses)."""

    def __init__(self, scale: float) -> None:
        self._scale = scale
        self._origin = time.monotonic()

    def now(self) -> float:
        return (time.monotonic() - self._origin) * self._scale + 1000.0

    def real_delay(self, game_seconds: float) -> float:
        return game_seconds / self._scale


def to_ms(seconds: float) -> float:
    return round(seconds * 1000.0, 1)
