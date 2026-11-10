"""Input sanitation, origin checks and security headers."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import HTTPException, Request

from app.core.config import AppSettings

NICKNAME_MAX = 20
CHAT_MAX = 200

_CONTROL_RE = re.compile(r"[\u0000-\u001f\u007f-\u009f​-‏‪-‮⁠-⁯﻿]")
_SPACES_RE = re.compile(r"\s+")
_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}
)

# Minimal blocklist (FR, EN, JA). "strong" entries are matched anywhere, "words" only as whole words.
_STRONG = (
    "fuck",
    "shit",
    "bitch",
    "nigger",
    "nigga",
    "faggot",
    "asshole",
    "merde",
    "putain",
    "connard",
    "connasse",
    "salope",
    "encule",
    "nique",
    "batard",
    "pedophile",
    "hitler",
    "死ね",
    "しね",
    "ちんこ",
    "まんこ",
    "ちんぽ",
)
_WORDS = ("pute", "con", "cul", "cock", "whore", "nazi", "cunt")


def clean_text(text: str, max_length: int) -> str:
    """NFKC, strip control/bidi/zero-width characters, collapse spaces, cut to ``max_length``."""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_RE.sub("", text)
    text = _SPACES_RE.sub(" ", text).strip()
    return text[:max_length]


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def contains_profanity(text: str) -> bool:
    folded = _fold(text).translate(_LEET)
    squashed = re.sub(r"[^a-z0-9぀-ヿ一-鿿]", "", folded)
    if any(bad in squashed for bad in _STRONG):
        return True
    tokens = re.split(r"[^a-z0-9぀-ヿ一-鿿]+", folded)
    return any(token in _WORDS for token in tokens)


def sanitize_nickname(raw: str) -> str | None:
    """Return a safe nickname, or None if it is empty or not acceptable."""
    name = clean_text(raw, NICKNAME_MAX)
    if not name or contains_profanity(name):
        return None
    return name


def sanitize_chat(raw: str) -> str | None:
    text = clean_text(raw, CHAT_MAX)
    if not text or contains_profanity(text):
        return None
    return text


# Development only: the web app may run on any port (Vite moves to 5174 when 5173 is busy) and be opened
# from a phone on the LAN. Private ranges: 10/8, 172.16/12, 192.168/16, Tailscale 100.64/10.
_LOCAL_ORIGIN = re.compile(
    r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
    r"|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+)(:\d+)?$"
)


def is_origin_allowed(origin: str | None, settings: AppSettings) -> bool:
    if origin is None:
        return settings.allow_missing_origin
    clean = origin.rstrip("/")
    if clean in settings.allowed_origins:
        return True
    return settings.env == "dev" and _LOCAL_ORIGIN.match(clean) is not None


async def require_same_site_request(request: Request) -> None:
    """CSRF guard for REST mutations.

    Browsers cannot send a JSON body with a custom header cross-site without a CORS preflight, and our CORS
    policy
    only allows known origins. On top of that we check Origin and the custom header explicitly.
    """
    settings: AppSettings = request.app.state.settings
    if not is_origin_allowed(request.headers.get("origin"), settings):
        raise HTTPException(status_code=403, detail="origin_not_allowed")
    if request.headers.get("x-hajime-client") != "web":
        raise HTTPException(status_code=403, detail="missing_client_header")


Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class SecurityHeadersMiddleware:
    """Adds hardening headers to every HTTP response of the API."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]], hsts: bool = False) -> None:
        self.app = app
        headers = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"no-referrer"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
            (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
            (b"cross-origin-resource-policy", b"same-site"),
        ]
        if hsts:
            headers.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains"))
        self._headers = headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = [
                    *message.get("headers", []),
                    *[(k, v) for k, v in self._headers if k not in existing],
                ]
            await send(message)

        await self.app(scope, receive, send_with_headers)
