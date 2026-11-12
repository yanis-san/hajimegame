"""Accounts: sign up, sign in, sign out, who am I, delete my account.

A player is a guest until they choose to sign up; playing as a guest stays complete. Signing up (or in)
also hands over the browser's guest identifier, which attaches that browser's past games to the account.

The session is an httpOnly cookie holding a random secret; the database keeps only its hash. Every mutation
checks the origin and the client header like room creation does (``require_same_site_request``)."""

from __future__ import annotations

import re
import uuid

import msgspec
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.routes import client_ip
from app.core import metrics
from app.core.captcha import verify_turnstile
from app.core.config import AppSettings
from app.core.passwords import PASSWORD_MAX, PASSWORD_MIN, hash_password, needs_rehash, verify_password
from app.core.ratelimit import WindowLimiter
from app.core.security import clean_text, contains_profanity, require_same_site_request
from app.db import accounts

router = APIRouter()

COOKIE = "hajime_session"
USERNAME_RE = re.compile(r"^[\w.\-]{3,20}$")  # letters (any script), digits, underscore, dot, dash
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,189}\.[^@\s]{2,}$")

REGISTER_PER_HOUR = 5
LOGIN_PER_IP = 20  # per 10 minutes
LOGIN_PER_NAME = 10  # per 15 minutes


class Registration(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=PASSWORD_MAX)
    email: str | None = Field(default=None, max_length=254)
    guest_id: uuid.UUID | None = None
    captcha: str = Field(default="", max_length=4096)


class Login(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=PASSWORD_MAX)
    guest_id: uuid.UUID | None = None


class Confirmation(BaseModel):
    password: str = Field(max_length=PASSWORD_MAX)


def _engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine | None = request.app.state.engine
    if engine is None:
        raise HTTPException(
            status_code=503, detail="accounts_unavailable"
        )  # nothing is stored without a database
    return engine


def _settings(request: Request) -> AppSettings:
    settings: AppSettings = request.app.state.settings
    return settings


def _view(me: accounts.Me) -> dict[str, object]:
    return {"username": me.username, "email": me.email, "email_verified": me.email_verified}


def _reply(body: dict[str, object], status: int = 200) -> Response:
    return Response(
        msgspec.json.encode(body),
        status_code=status,
        media_type="application/json",
        headers={"cache-control": "no-store"},
    )


def _set_cookie(response: Response, request: Request, token: str) -> None:
    settings = _settings(request)
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


async def current_me(request: Request) -> accounts.Me | None:
    """The signed-in player, or None for a guest (no cookie, an unknown or expired one)."""
    token = request.cookies.get(COOKIE)
    engine: AsyncEngine | None = request.app.state.engine
    if not token or engine is None:
        return None
    return await accounts.session_owner(engine, token)


async def _limit(request: Request, key: str, limit: int, window: int, name: str) -> None:
    limiter: WindowLimiter = request.app.state.limiter
    if not await limiter.allow(key, limit, window):
        metrics.RATE_LIMITED.labels(name).inc()
        raise HTTPException(status_code=429, detail="rate_limited")


def clean_username(raw: str) -> str:
    name = clean_text(raw, 64)
    if not USERNAME_RE.match(name) or contains_profanity(name):
        raise HTTPException(status_code=400, detail="bad_username")
    return name


def clean_password(raw: str, username: str) -> str:
    if len(raw) < PASSWORD_MIN or raw.casefold() == username.casefold():
        raise HTTPException(status_code=400, detail="bad_password")
    return raw


def clean_email(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    email = raw.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="bad_email")
    return email


async def _sign_in(
    request: Request, response: Response, engine: AsyncEngine, player_id: uuid.UUID, guest: uuid.UUID | None
) -> None:
    if guest is not None:
        await accounts.link_guest(engine, player_id, guest)
    token = await accounts.open_session(engine, player_id, _settings(request).session_days)
    _set_cookie(response, request, token)


@router.post("/api/auth/register", status_code=201, dependencies=[Depends(require_same_site_request)])
async def register(body: Registration, request: Request) -> Response:
    engine = _engine(request)
    settings = _settings(request)
    # Checking the fields costs nothing, so mistakes do not use up the limit; the captcha and hashing do.
    username = clean_username(body.username)
    password = clean_password(body.password, username)
    email = clean_email(body.email)
    ip = client_ip(request)
    await _limit(request, f"register:{ip}", REGISTER_PER_HOUR, 3600, "register")
    if settings.turnstile_secret:
        if not await verify_turnstile(settings.turnstile_secret, body.captcha, ip):
            raise HTTPException(status_code=403, detail="captcha_failed")
    elif settings.is_prod:
        raise HTTPException(
            status_code=503, detail="accounts_unavailable"
        )  # production never skips the captcha
    try:
        player_id = await accounts.create_account(engine, username, await hash_password(password), email)
    except accounts.UsernameTaken as exc:
        raise HTTPException(status_code=409, detail="username_taken") from exc
    response = _reply({"username": username, "email": email, "email_verified": False}, 201)
    await _sign_in(request, response, engine, player_id, body.guest_id)
    return response


@router.post("/api/auth/login", dependencies=[Depends(require_same_site_request)])
async def login(body: Login, request: Request) -> Response:
    engine = _engine(request)
    username = clean_text(body.username, 64)
    await _limit(request, f"login:{client_ip(request)}", LOGIN_PER_IP, 600, "login")
    await _limit(request, f"login-name:{accounts.username_key(username)}", LOGIN_PER_NAME, 900, "login")
    found = await accounts.credentials(engine, username)
    if not await verify_password(found.password_hash if found else None, body.password) or found is None:
        raise HTTPException(status_code=401, detail="bad_credentials")  # the same answer for both causes
    if found.password_hash and needs_rehash(found.password_hash):
        await accounts.set_password_hash(engine, found.player_id, await hash_password(body.password))
    response = _reply({"username": found.username})
    await _sign_in(request, response, engine, found.player_id, body.guest_id)
    return response


@router.post("/api/auth/logout", dependencies=[Depends(require_same_site_request)])
async def logout(request: Request) -> Response:
    token = request.cookies.get(COOKIE)
    engine: AsyncEngine | None = request.app.state.engine
    if token and engine is not None:
        await accounts.close_session(engine, token)
    response = _reply({"ok": True})
    response.delete_cookie(COOKIE, path="/")
    return response


@router.get("/api/auth/me")
async def me(request: Request) -> Response:
    who = await current_me(request)
    return _reply({"user": _view(who) if who else None})


@router.post("/api/auth/delete", dependencies=[Depends(require_same_site_request)])
async def delete_my_account(body: Confirmation, request: Request) -> Response:
    engine = _engine(request)
    who = await current_me(request)
    if who is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    await _limit(request, f"login-name:{accounts.username_key(who.username)}", LOGIN_PER_NAME, 900, "login")
    found = await accounts.credentials(engine, who.username)
    if found is None or not await verify_password(found.password_hash, body.password):
        raise HTTPException(status_code=401, detail="bad_credentials")
    await accounts.delete_account(engine, who.player_id)
    response = _reply({"ok": True})
    response.delete_cookie(COOKIE, path="/")
    return response
