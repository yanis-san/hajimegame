"""CPU players: a pure decision function, no clock, no network.

``plan_turn`` decides what a bot does on its turn: which word it types and after how long, or that
it draws a blank and lets the bomb explode. The room schedules the plan on its own clock, so bots
obey the same fuse as humans.

Difficulty changes three things: how fast the bot answers, how many words it knows (it only picks
among the N commonest words for the fragment) and how often it draws a blank.
"""

from __future__ import annotations

import random
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.japanese.kana import shiritori_end

Difficulty = Literal["easy", "normal", "hard"]
DIFFICULTIES: tuple[Difficulty, ...] = ("easy", "normal", "hard")


@dataclass(frozen=True, slots=True)
class BotLevel:
    vocabulary: int  # how many of the commonest words it knows for a given fragment
    think: tuple[float, float]  # share of the fuse spent before answering (min, max)
    blank: float  # probability of drawing a blank and letting the bomb explode


LEVELS: dict[Difficulty, BotLevel] = {
    "easy": BotLevel(vocabulary=30, think=(0.50, 0.85), blank=0.30),
    "normal": BotLevel(vocabulary=120, think=(0.28, 0.65), blank=0.12),
    "hard": BotLevel(vocabulary=400, think=(0.12, 0.40), blank=0.03),
}

MAX_THINK = 0.92  # a bot never answers in the last 8% of the fuse


class WordLike(Protocol):
    @property
    def entry_id(self) -> int: ...

    @property
    def reading(self) -> str: ...


class CandidateSource(Protocol):
    def candidates(self, fragment: str, starts_with: bool = ...) -> Sequence[WordLike]: ...


@dataclass(frozen=True, slots=True)
class BotPlan:
    word: str | None  # None: the bot draws a blank
    delay: float  # seconds (game time) until the word is sent, or until the bot gives up
    typing_at: float  # seconds until the bot starts "typing" (what other players see)


def plan_turn(
    difficulty: Difficulty,
    fragment: str,
    *,
    shiritori: bool,
    used: Collection[int],
    fuse_seconds: float,
    source: CandidateSource,
    rng: random.Random,
) -> BotPlan:
    level = LEVELS[difficulty]
    delay = fuse_seconds * min(MAX_THINK, rng.uniform(*level.think))
    pool: list[WordLike] = []
    for candidate in source.candidates(fragment, starts_with=shiritori):
        if candidate.entry_id in used or len(candidate.reading) < 2:
            continue
        # A bot never walks into a word ending in ん, even when the penalty option makes it legal.
        if shiritori and shiritori_end(candidate.reading) == "ん":
            continue
        pool.append(candidate)
        if len(pool) >= level.vocabulary:
            break
    if not pool or rng.random() < level.blank:
        return BotPlan(None, delay, delay * 0.6)
    chosen = rng.choice(pool)
    return BotPlan(chosen.reading, delay, delay * 0.55)
