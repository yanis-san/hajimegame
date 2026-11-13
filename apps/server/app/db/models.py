"""Database schema (PostgreSQL; also runs on SQLite for tests).

The database is never touched during a game: results are written after ``game_over`` by a background task
(``app.db.recorder``). Every game is stored with each player's random guest identifier, so that when accounts
arrive a person's past games can be attached to their account. Tables for later milestones (seasons, groups,
challenges) exist from the start so they plug in without a refactor.

This module is the part every game shares. What only one game has (the bomb game's turns, say) lives in that
game's own module under ``app.db.games``, never here.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.age import age_on

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
    email_verified_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime
    )  # null until the address is confirmed
    birth_date: Mapped[date | None] = mapped_column(sa.Date)  # asked at sign-up; null for older accounts
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)

    player: Mapped[Player] = relationship(back_populates="account")

    @property
    def age(self) -> int | None:
        """Whole years today, or None when no date of birth was given."""
        return age_on(self.birth_date, date.today()) if self.birth_date else None


class PlayerGuest(Base):
    """A browser (its guest identifier) that belongs to an account. Statistics are read through this table, so
    a person who signs in on several devices sees all of their games."""

    __tablename__ = "player_guests"

    guest_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("players.id", ondelete="CASCADE"), index=True)
    linked_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)


class EmailToken(Base):
    """A one-time secret sent by e-mail to confirm an address. Only its hash is stored; it expires, and it
    can be used once. ``email`` is the address it was sent to: if that changes, the token is useless."""

    __tablename__ = "email_tokens"

    token_hash: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("players.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime)
    used_at: Mapped[datetime | None] = mapped_column(sa.DateTime)


class LoginSession(Base):
    """A signed-in browser. Only the hash of the cookie's token is stored, so a copy of the database cannot
    be used to sign in."""

    __tablename__ = "login_sessions"

    token_hash: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    player_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("players.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime)


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
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)  # seed, mode...
    created_by: Mapped[uuid.UUID | None] = mapped_column(sa.ForeignKey("players.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(sa.DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(sa.DateTime)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (sa.Index("ix_games_ended_at", "ended_at"),)

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(sa.String(16), default="bomb")
    mode: Mapped[str] = mapped_column(sa.String(16), default="classic")  # classic | shiritori | kanji
    room_code: Mapped[str] = mapped_column(sa.String(8))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(sa.DateTime)
    season_id: Mapped[int | None] = mapped_column(sa.ForeignKey("seasons.id", ondelete="SET NULL"))
    challenge_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("challenges.id", ondelete="SET NULL")
    )

    duration_ms: Mapped[int] = mapped_column(default=0)
    players_count: Mapped[int] = mapped_column(default=0)
    bots_count: Mapped[int] = mapped_column(default=0)

    players: Mapped[list[GamePlayer]] = relationship(back_populates="game", cascade="all, delete-orphan")


class GamePlayer(Base):
    """One participant of one game.

    ``guest_id`` is the random identifier the player's browser generated. ``player_id`` stays null for a guest
    and is filled in (for every game with that ``guest_id``) when they create an account.
    """

    __tablename__ = "game_players"
    __table_args__ = (sa.Index("ix_game_players_guest_id", "guest_id"),)

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
    guest_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid)
    lang: Mapped[str | None] = mapped_column(sa.String(2))  # interface language: fr | en | ja
    is_bot: Mapped[bool] = mapped_column(default=False)
    bot_difficulty: Mapped[str | None] = mapped_column(sa.String(8))
    explosions: Mapped[int] = mapped_column(default=0)
    avg_response_ms: Mapped[int | None]

    game: Mapped[Game] = relationship(back_populates="players")
