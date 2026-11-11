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


class WordValidator(Protocol):
    def matches(self, text: str, fragment: str, *, starts_with: bool = ...) -> Sequence[WordHit]:
        """Every dictionary entry spelled ``text`` whose reading contains ``fragment``."""

    def reject_reason(self, text: str, fragment: str, *, starts_with: bool = ...) -> RejectReason:
        """Why ``text`` has no match: ``not_in_dictionary`` or ``missing_fragment``."""

    def start_count(self, kana: str) -> int:
        """How many words start with ``kana``."""


class FragmentPicker(Protocol):
    def pick_text(self, rng: random.Random, tier: int, recent: Sequence[str]) -> str:
        """Return a playable fragment of the given difficulty tier, avoiding ``recent`` ones."""
