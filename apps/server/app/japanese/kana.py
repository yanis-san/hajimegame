"""Kana helpers: normalization, mora units and fragment matching.

Pure functions, no I/O.
"""

from __future__ import annotations

import re
import unicodedata

import jaconv

# Small kana that never separate from the kana that precedes them.
TRAILING_SMALL = "ゃゅょぁぃぅぇぉゎっ"
LONG_MARK = "ー"

_WHITESPACE_RE = re.compile(r"[\s　​-‍﻿]+")
_HIRAGANA_RE = re.compile(r"^[ぁ-ゖー]+$")
_ROMAJI_RE = re.compile(r"^[a-z'\-.āīūēō]+$")

MAX_WORD_LENGTH = 32


def normalize_text(text: str) -> str:
    """NFKC, strip whitespace, fold katakana to hiragana. Keeps the long mark and kanji."""
    folded = unicodedata.normalize("NFKC", text)
    # Removing whitespace can bring combining marks next to a new base, so compose again.
    folded = unicodedata.normalize("NFKC", _WHITESPACE_RE.sub("", folded))
    return unicodedata.normalize("NFKC", jaconv.kata2hira(folded))


def looks_like_romaji(text: str) -> bool:
    return bool(text) and _ROMAJI_RE.match(text.lower()) is not None


def is_hiragana(text: str) -> bool:
    return bool(_HIRAGANA_RE.match(text))


def units(reading: str) -> list[str]:
    """Split a reading into units: a kana plus its trailing small kana; the long mark stands alone."""
    result: list[str] = []
    for char in reading:
        if char in TRAILING_SMALL and result and result[-1] != LONG_MARK:
            result[-1] += char
        else:
            result.append(char)
    return result


def contains_fragment(reading: str, fragment: str) -> bool:
    """True if ``fragment`` occurs in ``reading`` without cutting a unit in half."""
    if not fragment:
        return False
    start = 0
    while True:
        index = reading.find(fragment, start)
        if index < 0:
            return False
        end = index + len(fragment)
        if end >= len(reading) or reading[end] not in TRAILING_SMALL:
            return True
        start = index + 1


def fragment_ngrams(reading: str, max_units: int = 3) -> set[str]:
    """All 1..max_units unit n-grams of ``reading`` that never contain the long mark."""
    parts = units(reading)
    found: set[str] = set()
    for i in range(len(parts)):
        gram = ""
        for j in range(i, min(i + max_units, len(parts))):
            if parts[j] == LONG_MARK:
                break
            gram += parts[j]
            found.add(gram)
    return found
