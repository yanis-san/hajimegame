"""Candidate words for CPU players.

A bot needs "some valid word for this fragment" in microseconds, so the dictionary is indexed once.
For every fragment (and every first kana, for shiritori) we keep the commonest entries, commonest first.
Entries are stored by id in compact arrays of 4 bytes. The dictionary file is sorted by frequency
rank, so a lower id is a commoner word.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass

from app.japanese.dictionary import Dictionary
from app.japanese.kana import contains_fragment, fragment_ngrams

PER_KEY = 400


@dataclass(frozen=True, slots=True)
class Candidate:
    entry_id: int
    reading: str


class CandidateIndex:
    def __init__(self, dictionary: Dictionary, per_key: int = PER_KEY) -> None:
        self._dictionary = dictionary
        contains: dict[str, array[int]] = {}
        starts: dict[str, array[int]] = {}
        for entry_id in range(len(dictionary)):
            entry = dictionary.entry(entry_id)
            if entry.short:
                continue
            grams: set[str] = set()
            for reading in entry.readings:
                grams |= fragment_ngrams(reading)
            for gram in grams:
                bucket = contains.setdefault(gram, array("I"))
                if len(bucket) < per_key:
                    bucket.append(entry_id)
            for first in {r[0] for r in entry.readings}:
                bucket = starts.setdefault(first, array("I"))
                if len(bucket) < per_key:
                    bucket.append(entry_id)
        self._contains = contains
        self._starts = starts

    def candidates(self, fragment: str, starts_with: bool = False) -> list[Candidate]:
        """The commonest words for ``fragment``, commonest first (at most ``PER_KEY``)."""
        ids = (self._starts if starts_with else self._contains).get(fragment, array("I"))
        found: list[Candidate] = []
        for entry_id in ids:
            for reading in self._dictionary.entry(entry_id).readings:
                if (reading[:1] == fragment) if starts_with else contains_fragment(reading, fragment):
                    found.append(Candidate(entry_id, reading))
                    break
        return found
