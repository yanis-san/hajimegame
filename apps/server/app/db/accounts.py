"""Accounts, browsers linked to them and login sessions.

Everything here is the shared part of the schema (no game is mentioned): a game's statistics find a player's
games through ``player_guests``, which is how a person who signs in on a second device sees every game.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import Account, GamePlayer, LoginSession, Player, PlayerGuest

PROVIDER = "password"


class UsernameTaken(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Me:
    player_id: uuid.UUID
    username: str
    email: str | None
    email_verified: bool


@dataclass(frozen=True, slots=True)
class Credentials:
    player_id: uuid.UUID
    username: str
    password_hash: str | None


def username_key(username: str) -> str:
    """What makes two usernames "the same": case does not matter ("Aya" and "aya" are one person)."""
    return username.casefold()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now()


async def create_account(
    engine: AsyncEngine, username: str, password_hash: str, email: str, birth_date: date
) -> uuid.UUID:
    """A new player with a password login. Raises ``UsernameTaken`` when the name is already used."""
    player_id = uuid.uuid4()
    try:
        async with engine.begin() as connection:
            await connection.execute(
                sa.insert(Player).values(id=player_id, display_name=username, is_guest=False, rank_points=0)
            )
            await connection.execute(
                sa.insert(Account).values(
                    id=uuid.uuid4(),
                    player_id=player_id,
                    provider=PROVIDER,
                    subject=username_key(username),
                    email=email,
                    birth_date=birth_date,
                    password_hash=password_hash,
                )
            )
    except IntegrityError as exc:  # the unique (provider, subject): someone registered that name first
        raise UsernameTaken from exc
    return player_id


async def credentials(engine: AsyncEngine, username: str) -> Credentials | None:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                sa.select(Account.player_id, Player.display_name, Account.password_hash)
                .join(Player, Player.id == Account.player_id)
                .where(Account.provider == PROVIDER, Account.subject == username_key(username))
            )
        ).first()
    return Credentials(row[0], row[1], row[2]) if row else None


async def set_password_hash(engine: AsyncEngine, player_id: uuid.UUID, password_hash: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            sa.update(Account).where(Account.player_id == player_id).values(password_hash=password_hash)
        )


async def link_guest(engine: AsyncEngine, player_id: uuid.UUID, guest_id: uuid.UUID) -> None:
    """Attach a browser's games to the account. A browser already linked to someone else stays theirs."""
    async with engine.begin() as connection:
        owner = (
            await connection.execute(sa.select(PlayerGuest.player_id).where(PlayerGuest.guest_id == guest_id))
        ).scalar()
        if owner is None:
            await connection.execute(sa.insert(PlayerGuest).values(guest_id=guest_id, player_id=player_id))
        elif owner != player_id:
            return
        await connection.execute(
            sa.update(GamePlayer)
            .where(GamePlayer.guest_id == guest_id, GamePlayer.player_id.is_(None))
            .values(player_id=player_id)
        )


async def linked_guests(engine: AsyncEngine, player_id: uuid.UUID) -> list[uuid.UUID]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            sa.select(PlayerGuest.guest_id).where(PlayerGuest.player_id == player_id)
        )
        return [r[0] for r in rows]


async def open_session(engine: AsyncEngine, player_id: uuid.UUID, days: int) -> str:
    """A new login for the player; returns the secret to put in the cookie (only its hash is stored)."""
    token = secrets.token_urlsafe(32)
    now = _now()
    async with engine.begin() as connection:
        await connection.execute(sa.delete(LoginSession).where(LoginSession.expires_at < now))
        await connection.execute(
            sa.insert(LoginSession).values(
                token_hash=_token_hash(token),
                player_id=player_id,
                created_at=now,
                expires_at=now + timedelta(days=days),
            )
        )
    return token


async def session_owner(engine: AsyncEngine, token: str) -> Me | None:
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                sa.select(Player.id, Player.display_name, Account.email, Account.email_verified_at)
                .select_from(LoginSession)
                .join(Player, Player.id == LoginSession.player_id)
                .join(Account, Account.player_id == Player.id)
                .where(LoginSession.token_hash == _token_hash(token), LoginSession.expires_at > _now())
            )
        ).first()
    return Me(row[0], row[1], row[2], row[3] is not None) if row else None


async def close_session(engine: AsyncEngine, token: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(sa.delete(LoginSession).where(LoginSession.token_hash == _token_hash(token)))


async def delete_account(engine: AsyncEngine, player_id: uuid.UUID) -> None:
    """Remove the account and everything that signs it in. Its past games stay, with nobody attached to them
    (the rows are explicit: SQLite does not enforce foreign keys unless told to)."""
    async with engine.begin() as connection:
        await connection.execute(
            sa.update(GamePlayer).where(GamePlayer.player_id == player_id).values(player_id=None)
        )
        await connection.execute(sa.delete(LoginSession).where(LoginSession.player_id == player_id))
        await connection.execute(sa.delete(PlayerGuest).where(PlayerGuest.player_id == player_id))
        await connection.execute(sa.delete(Account).where(Account.player_id == player_id))
        await connection.execute(sa.delete(Player).where(Player.id == player_id))
