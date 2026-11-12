"""The bomb game's statistics view: the player's numbers, plus the meaning and an example of each word."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import cast

import msgspec
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.games import bomb as db
from app.japanese.dictionary import Dictionary
from app.realtime import protocol as pr


def _meaning(dictionary: Dictionary, word: str) -> dict[str, str]:
    """Meanings and an example sentence for a word, empty when the dictionary does not know it."""
    found = dictionary.lookup(word)
    if found is None:
        return {}
    return {
        "meaning_fr": found.meaning_fr,
        "meaning_en": found.meaning_en,
        "example_ja": found.example_ja,
        "example_en": found.example_en,
        "example_fr": found.example_fr,
    }


def build_view(raw: db.PlayerStats, mode: str, dictionary: Dictionary, today: date) -> pr.BombStatsView:
    s = raw.summary
    days = [today - timedelta(days=offset) for offset in range(db.ACTIVITY_DAYS - 1, -1, -1)]
    return pr.BombStatsView(
        mode=cast(pr.BombStatsMode, mode),
        summary=pr.BombStatsSummary(
            games=s.games,
            wins=s.wins,
            words=s.words,
            distinct_words=s.distinct_words,
            explosions=s.explosions,
            avg_response_ms=s.avg_response_ms,
            fastest_ms=s.fastest_ms,
            longest_word=s.longest_word,
        ),
        top_words=[
            pr.BombWordStat(
                word=w.word,
                reading=w.reading,
                count=w.count,
                last_played=w.last_played.isoformat(),
                **_meaning(dictionary, w.word),
            )
            for w in raw.top_words
        ],
        recent_words=[
            pr.BombRecentWord(
                word=w.word,
                reading=w.reading,
                played_at=w.played_at.isoformat(),
                mode="shiritori" if w.mode == "shiritori" else "classic",
                response_ms=w.response_ms,
                **_meaning(dictionary, w.word),
            )
            for w in raw.recent_words
        ],
        activity=[pr.DayStat(day=d.isoformat(), games=raw.activity.get(d, 0)) for d in days],
    )


class BombStatsProvider:
    @property
    def modes(self) -> tuple[str, ...]:
        return db.MODES

    async def view(
        self,
        engine: AsyncEngine,
        guest_ids: Sequence[uuid.UUID],
        mode: str,
        dictionary: Dictionary,
        today: date,
    ) -> msgspec.Struct:
        raw = await db.player_stats(engine, guest_ids, mode, today=today)
        return build_view(raw, mode, dictionary, today)


PROVIDER = BombStatsProvider()
