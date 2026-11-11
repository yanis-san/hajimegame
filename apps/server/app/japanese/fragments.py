"""Fragment table: which 1-3 unit kana sequences are playable, and how hard they are."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.japanese.kana import fragment_ngrams

DEFAULT_MIN_WORDS = 80
STORE_MIN_TOTAL = 20  # fragments below this total are not worth storing
_UNPLAYABLE_SINGLES = frozenset({"ん", "を", "ゔ"})
# Share of each fragment length: mostly 1-2 kana (fast and fun), 3 now and then, 4+ almost never.
LENGTH_WEIGHTS = {1: 0.30, 2: 0.56, 3: 0.135, 4: 0.005}
RECENT_FIRSTS = 4  # the first kana of the last prompts is avoided, so prompts do not feel repetitive
N_WEIGHT = 0.2  # ん-initial fragments are legal but awkward; keep them uncommon


def count_fragments(entries: Iterable[Sequence[str]]) -> dict[str, int]:
    """Count the distinct entries containing each fragment.

    ``entries`` yields the readings of each entry; an entry counts once per fragment even if several of its
    readings contain it. Fragments with too few words are not stored.
    """
    counts: dict[str, int] = defaultdict(int)
    for readings in entries:
        grams: set[str] = set()
        for reading in readings:
            grams |= fragment_ngrams(reading)
        for gram in grams:
            counts[gram] += 1
    return {g: n for g, n in counts.items() if n >= STORE_MIN_TOTAL}


@dataclass(frozen=True, slots=True)
class Fragment:
    text: str
    words: int
    tier: int  # 0 easy, 1 medium, 2 hard


class FragmentTable:
    """Playable fragments, split in three tiers by how many words contain them (fewer words, harder)."""

    def __init__(self, counts: Mapping[str, int], min_words: int = DEFAULT_MIN_WORDS) -> None:
        playable = [
            (text, total)
            for text, total in counts.items()
            if text not in _UNPLAYABLE_SINGLES and total >= min_words
        ]
        if not playable:
            raise ValueError(f"no fragment reaches {min_words} words")
        playable.sort(key=lambda item: (-item[1], item[0]))
        third = max(1, len(playable) // 3)
        self._fragments = tuple(
            Fragment(text, total, min(2, index // third)) for index, (text, total) in enumerate(playable)
        )
        self.min_words = min_words

    def __len__(self) -> int:
        return len(self._fragments)

    @property
    def fragments(self) -> tuple[Fragment, ...]:
        return self._fragments

    def pick(self, rng: random.Random, tier: int = 0, recent: Sequence[str] = ()) -> Fragment:
        """Pick a fragment of ``tier`` (clamped), avoiding ``recent`` ones when possible.

        Choosing uniformly among fragments would give mostly long, rare-looking ones and many starting with
        the same kana. So the length is drawn first (``LENGTH_WEIGHTS``), then the first kana (flattened by a
        square root so common kana stay common, with ん damped,
        and not one of the last few), and only then the fragment itself.
        """
        tier = max(0, min(2, tier))
        pool = [f for f in self._fragments if f.text not in recent] or list(self._fragments)
        by_length: dict[int, list[Fragment]] = defaultdict(list)
        for fragment in pool:
            by_length[len(fragment.text)].append(fragment)
        lengths = list(by_length)
        length = rng.choices(lengths, [LENGTH_WEIGHTS.get(n, 0.01) for n in lengths])[0]
        # The tier only matters inside a length: single kana are all "easy" by frequency but must appear.
        candidates = [f for f in by_length[length] if f.tier == tier] or by_length[length]
        recent_firsts = {text[0] for text in recent[-RECENT_FIRSTS:]}
        fresh = [f for f in candidates if f.text[0] not in recent_firsts]
        candidates = fresh or candidates
        firsts: dict[str, list[Fragment]] = defaultdict(list)
        for fragment in candidates:
            firsts[fragment.text[0]].append(fragment)
        keys = list(firsts)
        weights = [
            math.sqrt(sum(f.words for f in firsts[key])) * (N_WEIGHT if key == "ん" else 1.0) for key in keys
        ]
        first = rng.choices(keys, weights)[0]
        group = firsts[first]
        return group[rng.randrange(len(group))]

    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        """FragmentPicker port used by the game engine."""
        return self.pick(rng, tier, recent).text


__all__ = ["DEFAULT_MIN_WORDS", "Fragment", "FragmentTable", "count_fragments"]
