"""Difficulty levels.

JLPT no longer publishes official word lists, so levels are derived from JMdict frequency ranks
(see docs/DICTIONARY.md). Thresholds are plain data so a community JLPT list can replace them.
"""

from __future__ import annotations

from typing import Final

LEVELS: Final[tuple[str, ...]] = ("n5", "n4", "n3", "n2", "n1")

# Highest dictionary rank (smaller = more common) accepted at each level.
LEVEL_MAX_RANK: Final[dict[str, int]] = {"n5": 6, "n4": 12, "n3": 24, "n2": 40, "n1": 99}


def level_index(level: str) -> int:
    try:
        return LEVELS.index(level)
    except ValueError as exc:
        raise ValueError(f"unknown level {level!r}") from exc


def bucket_for_rank(rank: int) -> int:
    """Index of the easiest level that accepts a word of this rank."""
    for index, level in enumerate(LEVELS):
        if rank <= LEVEL_MAX_RANK[level]:
            return index
    return len(LEVELS) - 1
