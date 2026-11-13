"""Bomb game settings with validated bounds."""

from __future__ import annotations

from dataclasses import dataclass

LIVES_MIN, LIVES_DEFAULT, LIVES_MAX = 1, 3, 5
FUSE_MIN, FUSE_DEFAULT, FUSE_MAX = 5.0, 10.0, 20.0
PLAYERS_MIN, PLAYERS_DEFAULT, PLAYERS_MAX = 2, 8, 8
MODES = ("classic", "shiritori", "kanji")
LEVELS_DEFAULT = (5, 4)  # kanji mode: the JLPT levels asked, N5 (easiest) to N1
LIFE_CAP = 5  # bonus lives never raise a player above this


@dataclass(frozen=True, slots=True)
class BombSettings:
    lives: int = LIVES_DEFAULT
    fuse_seconds: float = FUSE_DEFAULT
    mode: str = "classic"
    max_players: int = PLAYERS_DEFAULT
    bonus_kana: bool = False
    n_penalty: bool = False  # shiritori: a word ending in ん costs a life instead of being refused
    levels: tuple[int, ...] = LEVELS_DEFAULT  # kanji mode: which JLPT levels (5 to 1) a kanji may come from

    def __post_init__(self) -> None:
        if not LIVES_MIN <= self.lives <= LIVES_MAX:
            raise ValueError(f"lives must be in [{LIVES_MIN}, {LIVES_MAX}]")
        if not FUSE_MIN <= self.fuse_seconds <= FUSE_MAX:
            raise ValueError(f"fuse_seconds must be in [{FUSE_MIN}, {FUSE_MAX}]")
        if not PLAYERS_MIN <= self.max_players <= PLAYERS_MAX:
            raise ValueError(f"max_players must be in [{PLAYERS_MIN}, {PLAYERS_MAX}]")
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if not self.levels or not set(self.levels) <= {1, 2, 3, 4, 5}:
            raise ValueError("levels must be a non-empty subset of 1 to 5")
