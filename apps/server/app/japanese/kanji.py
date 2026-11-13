"""The kanji of the kanji game: JLPT level (indicative), readings, and the words written with them.

A word is accepted for a kanji when the dictionary writes that word with the kanji, whatever the player typed:

  * typed in kanji (土曜日): the text contains the kanji;
  * typed in kana (どようび, つき, ひ): an entry with this reading is written with it (土曜日, 月, 日).
    Every reading the kanji really has in words is covered with no list of rules: rendaku, gemination
    and irregular readings are exactly the readings of the words.

Nothing is guessed from the readings of KANJIDIC: a reading alone is only accepted when a word exists for it.
"""

from __future__ import annotations

import gzip
import json
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.japanese.dictionary import Dictionary, WordMatch, WordRejected

DEFAULT_PATH: Final = Path(__file__).parent / "data" / "kanji.json.gz"
LEVELS: Final = (5, 4, 3, 2, 1)
# A kanji needs this many words to be worth a turn (a kanji with two words would be a trap for the players).
MIN_WORDS: Final = 5


@dataclass(frozen=True, slots=True)
class Kanji:
    char: str
    level: int  # 5 (N5, easiest) to 1 (N1)
    on: tuple[str, ...]  # on readings, hiragana
    kun: tuple[str, ...]  # kun readings without okurigana, hiragana
    meaning_en: str
    meaning_fr: str


class KanjiBook:
    """Kanji table plus the index kanji -> dictionary entries. Built once, never mutated."""

    def __init__(self, dictionary: Dictionary, kanji: dict[str, Kanji]) -> None:
        self._dictionary = dictionary
        self._kanji = kanji
        words: dict[str, set[int]] = {char: set() for char in kanji}
        for entry_id in range(len(dictionary)):
            entry = dictionary.entry(entry_id)
            for form in entry.words:
                for char in form:
                    bucket = words.get(char)
                    if bucket is not None:
                        bucket.add(entry_id)
        self._words: dict[str, frozenset[int]] = {char: frozenset(ids) for char, ids in words.items()}
        self._by_level: dict[int, tuple[str, ...]] = {
            level: tuple(
                sorted(c for c, k in kanji.items() if k.level == level and len(self._words[c]) >= MIN_WORDS)
            )
            for level in LEVELS
        }

    @classmethod
    def load(cls, dictionary: Dictionary, path: Path = DEFAULT_PATH) -> KanjiBook:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        kanji = {
            char: Kanji(char, int(v[0]), tuple(v[1]), tuple(v[2]), str(v[3]), str(v[4]))
            for char, v in raw["k"].items()
        }
        return cls(dictionary, kanji)

    def __contains__(self, char: str) -> bool:
        return char in self._kanji

    def get(self, char: str) -> Kanji | None:
        return self._kanji.get(char)

    def pool(self, levels: Iterable[int]) -> tuple[str, ...]:
        """The kanji that can be asked for these levels (those with enough words)."""
        wanted = set(levels)
        return tuple(c for level in LEVELS if level in wanted for c in self._by_level[level])

    def word_count(self, char: str) -> int:
        return len(self._words.get(char, ()))

    def draw(self, levels: Iterable[int], rng: random.Random, recent: Sequence[str] = ()) -> str:
        """A kanji of the chosen levels, not one of the recent ones, favouring kanji that have many words."""
        pool = self.pool(levels)
        if not pool:
            raise ValueError("no kanji for these levels")
        banned = set(recent)
        candidates = [c for c in pool if c not in banned] or list(pool)
        # the weight grows slowly with the number of words: frequent kanji come up more often than rare ones
        weights = [min(self.word_count(c), 400) ** 0.5 for c in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]

    def check(self, raw: str, char: str) -> WordMatch | WordRejected:
        """Is ``raw`` a word written with ``char``? Else ``not_in_dictionary`` or ``missing_fragment``."""
        dictionary = self._dictionary
        text = dictionary.canonical(raw)
        entry_ids = dictionary.entry_ids(text)
        if not text or not entry_ids:
            return WordRejected("not_in_dictionary")
        for entry_id in entry_ids:
            entry = dictionary.entry(entry_id)
            if char in text or any(char in form for form in entry.words):
                reading = text if text in entry.readings else entry.readings[0]
                return dictionary.match(entry_id, reading, text)
        return WordRejected("missing_fragment")

    def matches(self, raw: str, char: str) -> tuple[WordMatch, ...]:
        """Every entry that makes ``raw`` valid for ``char`` (the engine refuses words already played)."""
        dictionary = self._dictionary
        text = dictionary.canonical(raw)
        out = []
        for entry_id in dictionary.entry_ids(text):
            entry = dictionary.entry(entry_id)
            if char in text or any(char in form for form in entry.words):
                reading = text if text in entry.readings else entry.readings[0]
                out.append(dictionary.match(entry_id, reading, text))
        return tuple(out)

    def sample_words(self, char: str, limit: int = 5) -> list[str]:
        """Commonest words written with ``char`` (used by bots and tests), as their first reading."""
        dictionary = self._dictionary
        ids = sorted(self._words.get(char, ()), key=lambda i: dictionary.entry(i).rank)
        return [dictionary.entry(i).readings[0] for i in ids[:limit]]


__all__ = ["DEFAULT_PATH", "LEVELS", "MIN_WORDS", "Kanji", "KanjiBook"]
