"""Fragment table: which 1-3 unit kana sequences are playable, and how hard they are."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.japanese.kana import fragment_ngrams
from app.japanese.levels import LEVELS, level_index

DEFAULT_MIN_WORDS = 80
STORE_MIN_TOTAL = 20  # fragments below this total are not worth storing
_UNPLAYABLE_SINGLES = frozenset({"ん", "を"})


def count_fragments(entries: Iterable[tuple[int, Sequence[str]]]) -> dict[str, list[int]]:
    """Count distinct entries per fragment, bucketed by level index.

    ``entries`` yields (level_bucket, readings). Result: fragment -> counts per bucket (len == len(LEVELS)).
    """
    counts: dict[str, list[int]] = defaultdict(lambda: [0] * len(LEVELS))
    for bucket, readings in entries:
        grams: set[str] = set()
        for reading in readings:
            grams |= fragment_ngrams(reading)
        for gram in grams:
            counts[gram][bucket] += 1
    return {g: c for g, c in counts.items() if sum(c) >= STORE_MIN_TOTAL}


@dataclass(frozen=True, slots=True)
class Fragment:
    text: str
    words: int
    tier: int  # 0 easy, 1 medium, 2 hard


class FragmentTable:
    """Playable fragments for one difficulty level."""

    def __init__(
        self, buckets: Mapping[str, Sequence[int]], level: str, min_words: int = DEFAULT_MIN_WORDS
    ) -> None:
        upto = level_index(level)
        playable = []
        for text, counts in buckets.items():
            if text in _UNPLAYABLE_SINGLES:
                continue
            total = sum(counts[: upto + 1])
            if total >= min_words:
                playable.append((text, total))
        if not playable:
            raise ValueError(f"no fragment reaches {min_words} words for level {level}")
        playable.sort(key=lambda item: (-item[1], item[0]))
        third = max(1, len(playable) // 3)
        self._fragments = tuple(
            Fragment(text, total, min(2, index // third)) for index, (text, total) in enumerate(playable)
        )
        self.level = level
        self.min_words = min_words

    def __len__(self) -> int:
        return len(self._fragments)

    @property
    def fragments(self) -> tuple[Fragment, ...]:
        return self._fragments

    def pick(self, rng: random.Random, tier: int = 0, recent: Sequence[str] = ()) -> Fragment:
        """Pick a fragment of ``tier`` (clamped), avoiding ``recent`` ones when possible."""
        tier = max(0, min(2, tier))
        pool = [f for f in self._fragments if f.tier == tier and f.text not in recent]
        if not pool:
            pool = [f for f in self._fragments if f.text not in recent] or list(self._fragments)
        return pool[rng.randrange(len(pool))]

    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        """FragmentPicker port used by the game engine."""
        return self.pick(rng, tier, recent).text


MIN_FRAGMENTS = 30


def playable_table(
    buckets: Mapping[str, Sequence[int]], level: str, min_words: int = DEFAULT_MIN_WORDS
) -> FragmentTable:
    """Table for ``level`` with at least ``min_words`` words per fragment.

    Small levels (N5 has under 2000 words) cannot reach the default threshold, so the threshold is halved
    until at least ``MIN_FRAGMENTS`` fragments exist. The effective value is exposed as ``table.min_words``.
    """
    threshold = min_words
    while True:
        try:
            table = FragmentTable(buckets, level, threshold)
        except ValueError:
            table = None
        if table is not None and len(table) >= MIN_FRAGMENTS:
            return table
        if threshold <= 3:
            raise ValueError(f"cannot build a playable fragment table for {level}")
        threshold = max(3, threshold // 2)


__all__ = ["DEFAULT_MIN_WORDS", "Fragment", "FragmentTable", "count_fragments", "playable_table"]
