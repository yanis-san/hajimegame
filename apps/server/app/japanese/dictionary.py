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
from app.japanese.levels import LEVEL_MAX_RANK, bucket_for_rank
from app.japanese.romaji import romaji_to_hiragana

DEFAULT_PATH: Final = Path(__file__).parent / "data" / "dictionary.json.gz"

Reject = Literal["not_in_dictionary", "missing_fragment"]


@dataclass(frozen=True, slots=True)
class Entry:
    words: tuple[str, ...]
    readings: tuple[str, ...]
    rank: int
    pos: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WordMatch:
    entry_id: int
    reading: str  # first reading containing the fragment
    text: str  # normalized text as typed (hiragana or kanji form)


@dataclass(frozen=True, slots=True)
class WordRejected:
    reason: Reject


class Dictionary:
    """Word lookup. Built once at startup, never mutated afterwards."""

    def __init__(
        self,
        entries: tuple[Entry, ...],
        fragment_buckets: dict[str, tuple[int, ...]],
        meta: dict[str, object],
    ) -> None:
        index: dict[str, list[int]] = {}
        for entry_id, entry in enumerate(entries):
            for key in (*entry.readings, *(normalize_text(w) for w in entry.words)):
                bucket = index.setdefault(key, [])
                if not bucket or bucket[-1] != entry_id:
                    bucket.append(entry_id)
        self._entries = entries
        self._index: dict[str, tuple[int, ...]] = {k: tuple(v) for k, v in index.items()}
        self.fragment_buckets = fragment_buckets
        self.meta = meta

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

    def check(self, raw: str, fragment: str, level: str = "n1") -> WordMatch | WordRejected:
        """Validate ``raw`` against the dictionary for ``level`` and ``fragment``.

        Returns the first matching entry (lowest rank first) whose reading contains the fragment.
        """
        if len(raw) > MAX_WORD_LENGTH * 2:
            return WordRejected("not_in_dictionary")
        text = self.canonical(raw)
        if not text or len(text) > MAX_WORD_LENGTH:
            return WordRejected("not_in_dictionary")
        max_rank = LEVEL_MAX_RANK[level]
        found = False
        for entry_id in self._index.get(text, ()):
            entry = self._entries[entry_id]
            if entry.rank > max_rank:
                continue
            found = True
            for reading in entry.readings:
                if contains_fragment(reading, fragment):
                    return WordMatch(entry_id, reading, text)
        return WordRejected("missing_fragment" if found else "not_in_dictionary")

    def reject_reason(self, text: str, fragment: str, level: str = "n1") -> Reject:
        """Why ``text`` cannot be played for ``fragment`` (``not_in_dictionary`` or ``missing_fragment``)."""
        result = self.check(text, fragment, level)
        return result.reason if isinstance(result, WordRejected) else "missing_fragment"

    def matches(self, text: str, fragment: str, level: str = "n1") -> tuple[WordMatch, ...]:
        """All entries matching (used by the engine to reject already played words)."""
        text = self.canonical(text)
        max_rank = LEVEL_MAX_RANK[level]
        result = []
        for entry_id in self._index.get(text, ()):
            entry = self._entries[entry_id]
            if entry.rank > max_rank:
                continue
            for reading in entry.readings:
                if contains_fragment(reading, fragment):
                    result.append(WordMatch(entry_id, reading, text))
                    break
        return tuple(result)

    def sample_words(self, fragment: str, level: str, limit: int = 5) -> list[str]:
        """Example words for a fragment (used by bots and tests)."""
        max_rank = LEVEL_MAX_RANK[level]
        out: list[str] = []
        for entry in self._entries:
            if entry.rank > max_rank:
                break
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
            Entry(tuple(e["w"]), tuple(e["r"]), int(e["k"]), tuple(e["p"])) for e in raw["entries"]
        )
        buckets = {frag: tuple(counts) for frag, counts in raw["fragments"].items()}
        return cls(entries, buckets, raw["meta"])


__all__ = ["Dictionary", "Entry", "WordMatch", "WordRejected", "bucket_for_rank"]
