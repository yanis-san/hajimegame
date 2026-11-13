"""The bomb game's tables and queries: every turn of every game, and what a player's own turns add up to.

Only this module knows the table ``bomb_turns``. Statistics read a player's own seats only (found through
``game_players``), never another player's, and never the CPU's.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base, Game, GamePlayer
from app.games.bomb.recording import KIND, BombDetail
from app.games.recording import GameRecord

MODES = ("all", "classic", "shiritori", "kanji")
TOP_WORDS = 20
RECENT_WORDS = 10
ACTIVITY_DAYS = 30


class BombTurn(Base):
    """One turn of one bomb game: the prompt, what happened, and how long it took."""

    __tablename__ = "bomb_turns"
    __table_args__ = (sa.Index("ix_bomb_turns_fragment", "fragment"),)

    game_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    turn: Mapped[int] = mapped_column(primary_key=True)
    seat: Mapped[int]
    fragment: Mapped[str] = mapped_column(sa.String(16))
    outcome: Mapped[str] = mapped_column(sa.String(12))  # word | explosion | n_ending
    word: Mapped[str] = mapped_column(sa.String(32), default="")
    reading: Mapped[str] = mapped_column(sa.String(32), default="")
    response_ms: Mapped[int | None]
    fuse_ms: Mapped[int] = mapped_column(default=0)
    rejected_attempts: Mapped[int] = mapped_column(default=0)


class BombStore:
    kind = KIND

    def detail_rows(self, record: GameRecord) -> Sequence[Base]:
        assert isinstance(record.detail, BombDetail)
        return [
            BombTurn(
                game_id=record.id,
                turn=t.turn,
                seat=t.seat,
                fragment=t.fragment,
                outcome=t.outcome,
                word=t.word,
                reading=t.reading,
                response_ms=t.response_ms,
                fuse_ms=t.fuse_ms,
                rejected_attempts=t.rejected_attempts,
            )
            for t in record.detail.turns
        ]


STORE = BombStore()


# ---------------------------------------------------------------- statistics


@dataclass(frozen=True, slots=True)
class Summary:
    games: int
    wins: int
    words: int
    distinct_words: int
    explosions: int
    avg_response_ms: int | None
    fastest_ms: int | None
    longest_word: str


@dataclass(frozen=True, slots=True)
class TopWord:
    word: str
    reading: str
    count: int
    last_played: date


@dataclass(frozen=True, slots=True)
class RecentWord:
    word: str
    reading: str
    played_at: datetime
    mode: str
    response_ms: int | None


@dataclass(frozen=True, slots=True)
class PlayerStats:
    summary: Summary
    top_words: list[TopWord]
    recent_words: list[RecentWord]
    activity: dict[date, int]  # games per day, only the days with a game


def _as_date(value: object) -> date:
    """A date, whether the database gave a date (PostgreSQL) or an ISO string (SQLite)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_datetime(value: object) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


async def player_stats(
    engine: AsyncEngine, guest_ids: Sequence[uuid.UUID], mode: str = "all", *, today: date | None = None
) -> PlayerStats:
    """Everything the bomb statistics page shows, for ``mode`` ("all", "classic" or "shiritori").

    ``guest_ids`` is the player: today one browser, later every browser linked to an account.
    """
    today = today or datetime.now().date()
    where: list[sa.ColumnElement[bool]] = [
        Game.kind == KIND,
        GamePlayer.guest_id.in_(guest_ids),
        GamePlayer.is_bot.is_(False),
    ]
    if mode != "all":
        where.append(Game.mode == mode)
    # The player's own turns that ended with a word (not the ones where the bomb won).
    words = (
        sa.select(
            BombTurn.turn, BombTurn.word, BombTurn.reading, BombTurn.response_ms, Game.ended_at, Game.mode
        )
        .select_from(BombTurn)
        .join(GamePlayer, sa.and_(GamePlayer.game_id == BombTurn.game_id, GamePlayer.seat == BombTurn.seat))
        .join(Game, Game.id == BombTurn.game_id)
        .where(*where, BombTurn.outcome == "word", BombTurn.word != "")
        .subquery()
    )
    day = sa.func.date(Game.ended_at)  # (a CAST to DATE gives SQLite a number, not a date)
    since = datetime.combine(today - timedelta(days=ACTIVITY_DAYS - 1), datetime.min.time())

    async with engine.connect() as connection:
        games_row = (
            await connection.execute(
                sa.select(
                    sa.func.count(sa.distinct(GamePlayer.game_id)),
                    sa.func.coalesce(sa.func.sum(sa.case((GamePlayer.place == 1, 1), else_=0)), 0),
                    sa.func.coalesce(sa.func.sum(GamePlayer.explosions), 0),
                )
                .select_from(GamePlayer)
                .join(Game, Game.id == GamePlayer.game_id)
                .where(*where)
            )
        ).one()
        longest = (
            await connection.execute(
                sa.select(GamePlayer.longest_word)
                .select_from(GamePlayer)
                .join(Game, Game.id == GamePlayer.game_id)
                .where(*where, GamePlayer.longest_word != "")
                .order_by(sa.func.length(GamePlayer.longest_word).desc(), GamePlayer.longest_word)
                .limit(1)
            )
        ).scalar()
        word_row = (
            await connection.execute(
                sa.select(
                    sa.func.count(),
                    sa.func.count(sa.distinct(words.c.word)),
                    sa.func.avg(words.c.response_ms),
                    sa.func.min(words.c.response_ms),
                )
            )
        ).one()
        top = (
            await connection.execute(
                sa.select(
                    words.c.word,
                    sa.func.min(words.c.reading),
                    sa.func.count().label("n"),
                    sa.func.max(words.c.ended_at).label("last"),
                )
                .group_by(words.c.word)
                .order_by(sa.desc("n"), sa.desc("last"), words.c.word)
                .limit(TOP_WORDS)
            )
        ).all()
        recent = (
            await connection.execute(
                sa.select(words.c.word, words.c.reading, words.c.ended_at, words.c.mode, words.c.response_ms)
                .order_by(words.c.ended_at.desc(), words.c.turn.desc())
                .limit(RECENT_WORDS)
            )
        ).all()
        activity = (
            await connection.execute(
                sa.select(day, sa.func.count(sa.distinct(GamePlayer.game_id)))
                .select_from(GamePlayer)
                .join(Game, Game.id == GamePlayer.game_id)
                .where(*where, Game.ended_at >= since)
                .group_by(day)
            )
        ).all()

    avg = word_row[2]
    return PlayerStats(
        summary=Summary(
            games=int(games_row[0]),
            wins=int(games_row[1]),
            words=int(word_row[0]),
            distinct_words=int(word_row[1]),
            explosions=int(games_row[2]),
            avg_response_ms=round(avg) if avg is not None else None,
            fastest_ms=int(word_row[3]) if word_row[3] is not None else None,
            longest_word=longest or "",
        ),
        top_words=[TopWord(r[0], r[1], int(r[2]), _as_date(r[3])) for r in top],
        recent_words=[RecentWord(r[0], r[1], _as_datetime(r[2]), r[3], r[4]) for r in recent],
        activity={_as_date(r[0]): int(r[1]) for r in activity},
    )
