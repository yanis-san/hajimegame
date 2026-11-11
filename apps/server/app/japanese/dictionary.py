"""Immutable in-memory dictionary compiled from JMdict by tools/build_dictionary.py."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from app.japanese.kana import (
    MAX_WORD_LENGTH,
    contains_fragment,
    is_hiragana,
    looks_like_romaji,
    normalize_text,
)
from app.japanese.romaji import romaji_to_hiragana

DEFAULT_PATH: Final = Path(__file__).parent / "data" / "dictionary.json.gz"

Reject = Literal["not_in_dictionary", "missing_fragment"]


@dataclass(frozen=True, slots=True)
class Entry:
    words: tuple[str, ...]
    readings: tuple[str, ...]
    rank: int  # commonness, smaller is more common; only orders suggestions, never filters words
    pos: tuple[str, ...]
    meaning_fr: str = ""  # JMdict has French for a minority of entries
    meaning_en: str = ""
    example: tuple[str, str, str] = ("", "", "")  # Japanese sentence, English, French (Tatoeba)


@dataclass(frozen=True, slots=True)
class WordMatch:
    entry_id: int
    reading: str  # first reading containing the fragment
    text: str  # normalized text as typed (hiragana or kanji form)
    meaning_fr: str = ""
    meaning_en: str = ""
    example_ja: str = ""  # an example sentence using the word, with its translations
    example_en: str = ""
    example_fr: str = ""


@dataclass(frozen=True, slots=True)
class WordRejected:
    reason: Reject


def _match(entry_id: int, entry: Entry, reading: str, text: str) -> WordMatch:
    ja, en, fr = entry.example
    return WordMatch(entry_id, reading, text, entry.meaning_fr, entry.meaning_en, ja, en, fr)


def _matches(reading: str, fragment: str, starts_with: bool) -> bool:
    """Classic: the fragment occurs in the reading. Shiritori: the reading starts with the kana."""
    return reading[:1] == fragment if starts_with else contains_fragment(reading, fragment)


class Dictionary:
    """Word lookup. Built once at startup, never mutated afterwards."""

    def __init__(
        self,
        entries: tuple[Entry, ...],
        fragment_counts: dict[str, int],
        meta: dict[str, object],
    ) -> None:
        index: dict[str, list[int]] = {}
        for entry_id, entry in enumerate(entries):
            for key in (*entry.readings, *(normalize_text(w) for w in entry.words)):
                bucket = index.setdefault(key, [])
                if not bucket or bucket[-1] != entry_id:
                    bucket.append(entry_id)
        self._entries = entries
        starts: dict[str, int] = {}
        for entry in entries:
            for first in {r[0] for r in entry.readings}:
                starts[first] = starts.get(first, 0) + 1
        self._starts = starts
        self._index: dict[str, tuple[int, ...]] = {k: tuple(v) for k, v in index.items()}
        self.fragment_counts = fragment_counts
        self.meta = meta

    def start_count(self, kana: str) -> int:
        """How many entries have a reading starting with ``kana`` (used to keep shiritori chains playable)."""
        return self._starts.get(kana, 0)

    def __len__(self) -> int:
        return len(self._entries)

    def entry(self, entry_id: int) -> Entry:
        return self._entries[entry_id]

    @staticmethod
    def canonical(text: str) -> str:
        """Normalize raw client input to the form used for lookup (hiragana or kanji)."""
        normalized = normalize_text(text)[: MAX_WORD_LENGTH * 2]
        if looks_like_romaji(normalized) and not is_hiragana(normalized):
            normalized = romaji_to_hiragana(normalized)
        return normalized

    def check(self, raw: str, fragment: str, *, starts_with: bool = False) -> WordMatch | WordRejected:
        """Validate ``raw`` against the dictionary and ``fragment``.

        Every word of the dictionary is accepted. Returns the first entry whose reading contains the fragment.
        """
        if len(raw) > MAX_WORD_LENGTH * 2:
            return WordRejected("not_in_dictionary")
        text = self.canonical(raw)
        if not text or len(text) > MAX_WORD_LENGTH:
            return WordRejected("not_in_dictionary")
        found = False
        for entry_id in self._index.get(text, ()):
            entry = self._entries[entry_id]
            found = True
            for reading in entry.readings:
                if _matches(reading, fragment, starts_with):
                    return _match(entry_id, entry, reading, text)
        return WordRejected("missing_fragment" if found else "not_in_dictionary")

    def reject_reason(self, text: str, fragment: str, *, starts_with: bool = False) -> Reject:
        """Why ``text`` cannot be played for ``fragment`` (``not_in_dictionary`` or ``missing_fragment``)."""
        result = self.check(text, fragment, starts_with=starts_with)
        return result.reason if isinstance(result, WordRejected) else "missing_fragment"

    def matches(self, text: str, fragment: str, *, starts_with: bool = False) -> tuple[WordMatch, ...]:
        """All entries matching (used by the engine to reject already played words)."""
        text = self.canonical(text)
        result = []
        for entry_id in self._index.get(text, ()):
            entry = self._entries[entry_id]
            for reading in entry.readings:
                if _matches(reading, fragment, starts_with):
                    result.append(_match(entry_id, entry, reading, text))
                    break
        return tuple(result)

    def sample_words(self, fragment: str, limit: int = 5) -> list[str]:
        """Example words for a fragment, commonest first (used by bots and tests)."""
        out: list[str] = []
        for entry in self._entries:
            for reading in entry.readings:
                if contains_fragment(reading, fragment):
                    out.append(reading)
                    break
            if len(out) >= limit:
                break
        return out

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> Dictionary:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
        entries = tuple(
            Entry(
                tuple(e["w"]),
                tuple(e["r"]),
                int(e["k"]),
                tuple(e["p"]),
                e.get("f", ""),
                e.get("g", ""),
                tuple(e["s"]) if "s" in e else ("", "", ""),
            )
            for e in raw["entries"]
        )
        return cls(entries, {frag: int(n) for frag, n in raw["fragments"].items()}, raw["meta"])


__all__ = ["Dictionary", "Entry", "WordMatch", "WordRejected"]
