"""Bomb game settings with validated bounds."""

from __future__ import annotations

from dataclasses import dataclass

LIVES_MIN, LIVES_DEFAULT, LIVES_MAX = 1, 3, 5
FUSE_MIN, FUSE_DEFAULT, FUSE_MAX = 5.0, 10.0, 20.0
PLAYERS_MIN, PLAYERS_DEFAULT, PLAYERS_MAX = 2, 8, 8
LEVELS = ("n5", "n4", "n3", "n2", "n1")
LIFE_CAP = 5  # bonus lives never raise a player above this
TENSION_FUSE_FLOOR = 3.0


@dataclass(frozen=True, slots=True)
class BombSettings:
    lives: int = LIVES_DEFAULT
    fuse_seconds: float = FUSE_DEFAULT
    level: str = "n1"
    max_players: int = PLAYERS_DEFAULT
    bonus_kana: bool = False
    tension: bool = False

    def __post_init__(self) -> None:
        if not LIVES_MIN <= self.lives <= LIVES_MAX:
            raise ValueError(f"lives must be in [{LIVES_MIN}, {LIVES_MAX}]")
        if not FUSE_MIN <= self.fuse_seconds <= FUSE_MAX:
            raise ValueError(f"fuse_seconds must be in [{FUSE_MIN}, {FUSE_MAX}]")
        if not PLAYERS_MIN <= self.max_players <= PLAYERS_MAX:
            raise ValueError(f"max_players must be in [{PLAYERS_MIN}, {PLAYERS_MAX}]")
        if self.level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")
