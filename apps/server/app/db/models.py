"""Database schema (PostgreSQL; also runs on SQLite for tests).

The database is never touched during a game: results are written after ``game_over`` by a background task.
Tables for later milestones (seasons, groups, challenges) exist from the start so they plug in without a
refactor, but no API or UI exposes them until milestone A is complete.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = sa.JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = sa.MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(tz=None)


class Player(Base):
    """A person who plays. Guests are players without an account row."""

    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(sa.String(20))
    is_guest: Mapped[bool] = mapped_column(default=True)
    rank_points: Mapped[int] = mapped_column(default=0)  # kyu/dan derives from this (milestone B)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)

    account: Mapped[Account | None] = relationship(back_populates="player", uselist=False)


class Account(Base):
    """Optional login attached to a player (Google or email), milestone B."""

    __tablename__ = "accounts"
    __table_args__ = (sa.UniqueConstraint("provider", "subject"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    player_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("players.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(sa.String(16))  # "google" | "email"
    subject: Mapped[str] = mapped_column(sa.String(255))  # google sub or lowercase email
    email: Mapped[str | None] = mapped_column(sa.String(255))
    password_hash: Mapped[str | None] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)

    player: Mapped[Player] = relationship(back_populates="account")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(40))
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime)
    ends_at: Mapped[datetime] = mapped_column(sa.DateTime)


class Group(Base):
    """A dojo (milestone E)."""

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.String(40))
    owner_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("players.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)


class Challenge(Base):
    """Daily challenge or friend challenge (milestones C and E)."""

    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(sa.String(16))  # "daily" | "friend"
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)  # seed, level, mode...
    created_by: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("players.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(sa.DateTime)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (sa.Index("ix_games_ended_at", "ended_at"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(sa.String(16), default="bomb")
    room_code: Mapped[str] = mapped_column(sa.String(8))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime)
    season_id: Mapped[int | None] = mapped_column(sa.ForeignKey("seasons.id", ondelete="SET NULL"))
    challenge_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("challenges.id", ondelete="SET NULL")
    )

    players: Mapped[list[GamePlayer]] = relationship(back_populates="game", cascade="all, delete-orphan")


class GamePlayer(Base):
    """One participant of one game. ``player_id`` is null for anonymous guests."""

    __tablename__ = "game_players"

    game_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    seat: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("players.id", ondelete="SET NULL"))
    display_name: Mapped[str] = mapped_column(sa.String(20))
    place: Mapped[int]
    score: Mapped[int] = mapped_column(default=0)
    words: Mapped[int] = mapped_column(default=0)
    longest_word: Mapped[str] = mapped_column(sa.String(32), default="")

    game: Mapped[Game] = relationship(back_populates="players")
