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
import zlib
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.japanese.dictionary import Dictionary, Reject, WordMatch, WordRejected

DEFAULT_PATH: Final = Path(__file__).parent / "data" / "kanji.json.gz"
NAMES_PATH: Final = Path(__file__).parent / "data" / "names.json.gz"
NAME_ID_BASE: Final = 1 << 30  # ids of proper names (they have no dictionary entry), above any entry id
NAME_MEANING_EN: Final = "Proper name (place or family name)"
NAME_MEANING_FR: Final = "Nom propre (lieu ou nom de famille)"
LEVELS: Final = (5, 4, 3, 2, 1)
# A kanji needs this many words to be worth a turn (a kanji with two words would be a trap for the players).
MIN_WORDS: Final = 5
DIFFICULTY: Final = {5: 0, 4: 0, 3: 1, 2: 2, 1: 2}
WEIGHT_CAP: Final = 40  # a kanji with more words than this is not drawn more often for it
CANDIDATES_PER_KANJI: Final = 600  # the words a CPU player can pick from, commonest first


@dataclass(frozen=True, slots=True)
class Candidate:
    entry_id: int
    reading: str


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

    def __init__(
        self,
        dictionary: Dictionary,
        kanji: dict[str, Kanji],
        names: dict[str, list[str]] | None = None,
    ) -> None:
        self._dictionary = dictionary
        self._kanji = kanji
        # proper names (places, stations, family names): reading -> written forms, and form -> readings
        self._names: dict[str, tuple[str, ...]] = {r: tuple(f) for r, f in (names or {}).items()}
        by_form: dict[str, list[str]] = {}
        for reading, forms in self._names.items():
            for form in forms:
                by_form.setdefault(form, []).append(reading)
        self._names_by_form: dict[str, tuple[str, ...]] = {f: tuple(r) for f, r in by_form.items()}
        self._candidates: dict[str, tuple[Candidate, ...]] = {}
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
    def load(
        cls, dictionary: Dictionary, path: Path = DEFAULT_PATH, names_path: Path = NAMES_PATH
    ) -> KanjiBook:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        kanji = {
            char: Kanji(char, int(v[0]), tuple(v[1]), tuple(v[2]), str(v[3]), str(v[4]))
            for char, v in raw["k"].items()
        }
        names: dict[str, list[str]] = {}
        if names_path.exists():
            with gzip.open(names_path, "rt", encoding="utf-8") as fh:
                names = json.load(fh)["n"]
        return cls(dictionary, kanji, names)

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

    def draw(self, levels: Iterable[int], rng: random.Random, recent: Collection[str] = ()) -> str:
        """A kanji of the chosen levels that is not in ``recent``.

        The level comes first, drawn evenly among the chosen ones (otherwise N1, which has the most kanji,
        would be almost all of a game that asks for every level). Then the kanji inside the level, with a
        weight that grows only slowly with its number of words, so the very common kanji do not come up much
        more than the others. When every kanji of the levels is in ``recent``, any of them may come again.
        """
        wanted = [level for level in LEVELS if level in set(levels)]
        banned = set(recent)
        tiers = [
            [c for c in self._by_level[level] if c not in banned] for level in wanted if self._by_level[level]
        ]
        tiers = [t for t in tiers if t]
        if not tiers:
            pool = self.pool(levels)
            if not pool:
                raise ValueError("no kanji for these levels")
            return rng.choice(pool)
        candidates = rng.choice(tiers)
        weights = [min(self.word_count(c), WEIGHT_CAP) ** 0.5 for c in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]

    def _name_matches(self, text: str, char: str) -> list[WordMatch]:
        """The proper name that makes ``text`` valid for ``char``, typed in kana (ueno) or in kanji (上野).

        One match at most, so a name cannot be played twice under two spellings. Typed in kana it is the
        most ordinary spelling that has the kanji (上野, not 上乃 or 上の), identified by the reading; typed
        in kanji, it is identified by the form.
        """
        if char in text:
            readings = self._names_by_form.get(text, ())
            if readings:
                return [self._name(text, readings[0], f"form:{text}")]
        forms = sorted((f for f in self._names.get(text, ()) if char in f), key=lambda f: self._name_rank(f))
        if forms:
            return [self._name(forms[0], text, f"reading:{text}")]
        return []

    def _name_rank(self, form: str) -> tuple[bool, int, int, str]:
        """Which spelling of a name to show: kanji only, then the easiest kanji, then the shortest."""
        levels = [k.level for c in form if (k := self._kanji.get(c)) is not None]
        return (len(levels) != len(form), -min(levels, default=0), len(form), form)

    @staticmethod
    def _name(form: str, reading: str, key: str) -> WordMatch:
        return WordMatch(
            NAME_ID_BASE + zlib.crc32(key.encode()), reading, form, NAME_MEANING_FR, NAME_MEANING_EN
        )

    def check(self, raw: str, char: str) -> WordMatch | WordRejected:
        """Is ``raw`` a word written with ``char``? Else ``not_in_dictionary`` or ``missing_fragment``."""
        text = self._dictionary.canonical(raw)
        found = self.matches(raw, char)
        if found:
            return found[0]
        known = text in self._names or text in self._names_by_form or self._dictionary.entry_ids(text)
        return WordRejected("missing_fragment" if text and known else "not_in_dictionary")

    def matches(self, raw: str, char: str) -> tuple[WordMatch, ...]:
        """Every word that makes ``raw`` valid for ``char`` (the engine refuses words already played):
        dictionary entries, or the proper names when there is none."""
        dictionary = self._dictionary
        text = dictionary.canonical(raw)
        out = []
        for entry_id in dictionary.entry_ids(text):
            entry = dictionary.entry(entry_id)
            if char in text or any(char in form for form in entry.words):
                reading = text if text in entry.readings else entry.readings[0]
                out.append(dictionary.match(entry_id, reading, text))
        if not out:  # a name counts only when no ordinary word does, so a word cannot be played twice as both
            out.extend(self._name_matches(text, char))
        return tuple(out)

    def difficulty(self, char: str) -> int:
        """0 for N5 and N4, 1 for N3, 2 for N2 and N1 (a kanji that is not in the table counts as easy)."""
        kanji = self._kanji.get(char)
        return 0 if kanji is None else DIFFICULTY[kanji.level]

    def reject_reason(self, raw: str, char: str) -> Reject:
        result = self.check(raw, char)
        return result.reason if isinstance(result, WordRejected) else "missing_fragment"

    def candidates(self, char: str, starts_with: bool = False) -> Sequence[Candidate]:
        """Words written with ``char``, commonest first, for the CPU players (``starts_with`` is unused)."""
        found = self._candidates.get(char)
        if found is None:
            dictionary = self._dictionary
            ids = sorted(self._words.get(char, ()), key=lambda i: (dictionary.entry(i).rank, i))
            found = tuple(Candidate(i, dictionary.entry(i).readings[0]) for i in ids[:CANDIDATES_PER_KANJI])
            self._candidates[char] = found
        return found

    def sample_words(self, char: str, limit: int = 5) -> list[str]:
        """Commonest words written with ``char`` (used by bots and tests), as their first reading."""
        dictionary = self._dictionary
        ids = sorted(self._words.get(char, ()), key=lambda i: dictionary.entry(i).rank)
        return [dictionary.entry(i).readings[0] for i in ids[:limit]]


_BOOKS: dict[int, KanjiBook] = {}


def shared_book(dictionary: Dictionary) -> KanjiBook:
    """The kanji book of this dictionary, built once (about 3 seconds of work) and shared by everybody."""
    book = _BOOKS.get(id(dictionary))
    if book is None or book._dictionary is not dictionary:
        book = _BOOKS[id(dictionary)] = KanjiBook.load(dictionary)
    return book


__all__ = ["DEFAULT_PATH", "LEVELS", "MIN_WORDS", "Kanji", "KanjiBook", "shared_book"]
