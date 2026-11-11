from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.games.base import ManualClock, PlayerInfo
from app.games.bomb.engine import BombEngine
from app.games.bomb.events import RejectReason
from app.games.bomb.settings import BombSettings


@dataclass(frozen=True)
class FakeHit:
    entry_id: int
    reading: str
    text: str
    meaning_fr: str = ""
    meaning_en: str = "test"
    example_ja: str = ""
    example_en: str = ""
    example_fr: str = ""


class FakeValidator:
    """Tiny word list: text -> list of (entry_id, reading)."""

    def __init__(self, words: dict[str, list[tuple[int, str]]]) -> None:
        self.words = words

    def matches(self, text: str, fragment: str, *, starts_with: bool = False) -> Sequence[FakeHit]:
        ok = (lambda r: r[:1] == fragment) if starts_with else (lambda r: fragment in r)
        return [FakeHit(i, r, text) for i, r in self.words.get(text, []) if ok(r)]

    def start_count(self, kana: str) -> int:
        return 100

    def reject_reason(self, text: str, fragment: str, *, starts_with: bool = False) -> RejectReason:
        return "missing_fragment" if text in self.words else "not_in_dictionary"


class FixedFragments:
    def __init__(self, fragment: str = "く") -> None:
        self.fragment = fragment

    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        rng.random()  # consume randomness like the real picker
        return self.fragment


WORDS = {
    "くるま": [(1, "くるま")],
    "くも": [(2, "くも")],
    "いく": [(3, "いく")],
    "つくえ": [(4, "つくえ")],
    "さくら": [(5, "さくら")],
    "ねこ": [(6, "ねこ")],
    "はし": [(7, "はし"), (8, "はし")],
    "ひく": [(9, "ひく")],
    "まくら": [(10, "まくら")],
    "らーめん": [(11, "らーめん")],
    "らくだ": [(12, "らくだ")],
    "くるん": [(14, "くるん")],
    "だいこん": [(13, "だいこん")],
}


def make_engine(
    n: int = 3,
    settings: BombSettings | None = None,
    seed: int = 1,
    words: dict[str, list[tuple[int, str]]] | None = None,
    fragments: Any = None,
) -> tuple[BombEngine, ManualClock]:
    clock = ManualClock(100.0)
    players = [PlayerInfo(f"p{i}", f"Player {i}") for i in range(n)]
    engine = BombEngine(
        players,
        settings or BombSettings(),
        validator=FakeValidator(words or WORDS),
        fragments=fragments or FixedFragments(),
        clock=clock,
        rng=random.Random(seed),
    )
    return engine, clock


class TierRecorder:
    """Fragment picker that records the difficulty tier it was asked for."""

    def __init__(self) -> None:
        self.tiers: list[int] = []

    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        self.tiers.append(tier)
        return "く"
