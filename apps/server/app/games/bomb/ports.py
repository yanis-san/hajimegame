"""Interfaces the bomb engine needs from the outside (implemented by app.japanese)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Protocol

from app.games.bomb.events import RejectReason


class WordHit(Protocol):
    @property
    def entry_id(self) -> int: ...

    @property
    def reading(self) -> str: ...

    @property
    def text(self) -> str: ...

    @property
    def meaning_fr(self) -> str: ...

    @property
    def meaning_en(self) -> str: ...

    @property
    def example_ja(self) -> str: ...

    @property
    def example_en(self) -> str: ...

    @property
    def example_fr(self) -> str: ...


class WordValidator(Protocol):
    def matches(self, text: str, fragment: str, *, starts_with: bool = ...) -> Sequence[WordHit]:
        """Every dictionary entry spelled ``text`` whose reading contains ``fragment``."""

    def reject_reason(self, text: str, fragment: str, *, starts_with: bool = ...) -> RejectReason:
        """Why ``text`` has no match: ``not_in_dictionary`` or ``missing_fragment``."""

    def start_count(self, kana: str) -> int:
        """How many words start with ``kana``."""


class KanjiSource(Protocol):
    """The kanji mode: which kanji to ask, and whether a word is written with it."""

    def draw(self, levels: Sequence[int], rng: random.Random, recent: Sequence[str] = ...) -> str:
        """A kanji of one of the JLPT ``levels``, not one of ``recent``."""

    def matches(self, text: str, char: str) -> Sequence[WordHit]:
        """Every dictionary entry spelled ``text`` that is written with the kanji ``char``."""

    def reject_reason(self, text: str, char: str) -> RejectReason:
        """Why ``text`` has no match: ``not_in_dictionary`` or ``missing_fragment``."""


class FragmentPicker(Protocol):
    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        """Return a playable fragment of the given difficulty tier, avoiding ``recent`` ones."""
