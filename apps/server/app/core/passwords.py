"""Password hashing (Argon2id). Hashing is deliberately slow, so it runs off the event loop."""

from __future__ import annotations

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # library defaults: Argon2id, parameters from RFC 9106
# Checked when the account does not exist, so that "unknown user" and "wrong password" take the same time.
_DUMMY = _hasher.hash("not-a-real-password")

PASSWORD_MIN = 8
PASSWORD_MAX = 128


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(stored: str | None, password: str) -> bool:
    """True when ``password`` matches ``stored``. A missing hash still costs one verification."""

    def check() -> bool:
        try:
            return _hasher.verify(stored or _DUMMY, password) and stored is not None
        except (VerificationError, InvalidHashError):
            return False

    return await asyncio.to_thread(check)


def needs_rehash(stored: str) -> bool:
    return _hasher.check_needs_rehash(stored)
