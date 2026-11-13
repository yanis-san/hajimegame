"""Age from a date of birth."""

from __future__ import annotations

from datetime import date

MAX_AGE = 120  # older than this is a typing mistake, not a player


def age_on(born: date, today: date) -> int:
    """Whole years lived on ``today`` (the birthday counts on the day itself)."""
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
