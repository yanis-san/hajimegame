"""Typed events emitted by the bomb engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.games.base import GameEvent

RejectReason = Literal["not_in_dictionary", "missing_fragment", "already_used", "not_your_turn", "too_late"]


@dataclass(frozen=True, slots=True, kw_only=True)
class GameStarted(GameEvent):
    player_ids: tuple[str, ...]
    lives: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TurnStarted(GameEvent):
    turn: int
    player_id: str
    fragment: str
    deadline: float
    fuse_seconds: float


@dataclass(frozen=True, slots=True, kw_only=True)
class WordAccepted(GameEvent):
    turn: int
    player_id: str
    word: str  # as typed, normalized
    reading: str
    score_gain: int
    score: int
    meaning_fr: str = ""
    meaning_en: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class WordRejected(GameEvent):
    turn: int
    player_id: str
    text: str
    reason: RejectReason


@dataclass(frozen=True, slots=True, kw_only=True)
class BonusProgress(GameEvent):
    player_id: str
    remaining: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class LifeGained(GameEvent):
    player_id: str
    lives: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Explosion(GameEvent):
    turn: int
    player_id: str
    lives: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PlayerEliminated(GameEvent):
    player_id: str
    place: int  # 1 is the winner, so the first eliminated gets the worst place
    reason: Literal["explosion", "left"]


@dataclass(frozen=True, slots=True, kw_only=True)
class GameOver(GameEvent):
    winner_id: str | None
    ranking: tuple[str, ...]  # best first
