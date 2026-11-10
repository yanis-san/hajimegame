"""RoomRegistry: which instance owns which room code.

A room lives in exactly one process. The registry is the single source of truth for that ownership so several
instances can run behind a load balancer: a client that lands on the wrong instance is redirected
(``fly-replay`` header on Fly.io) to the owner.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import WatchError

ROOM_TTL_SECONDS = 60.0


class RoomRegistry(Protocol):
    async def claim(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        """Atomically become the owner of ``code``. False if somebody else already owns it."""

    async def owner(self, code: str) -> str | None: ...

    async def refresh(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        """Extend ownership. False if we no longer own the code."""

    async def release(self, code: str, instance_id: str) -> None: ...


class MemoryRegistry:
    """Single-process registry (v1 default)."""

    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._owners: dict[str, tuple[str, float]] = {}

    def _live(self, code: str) -> str | None:
        entry = self._owners.get(code)
        if entry is None:
            return None
        owner, expires = entry
        if expires <= self._now():
            del self._owners[code]
            return None
        return owner

    async def claim(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        if self._live(code) is not None:
            return False
        self._owners[code] = (instance_id, self._now() + ttl)
        return True

    async def owner(self, code: str) -> str | None:
        return self._live(code)

    async def refresh(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        if self._live(code) != instance_id:
            return False
        self._owners[code] = (instance_id, self._now() + ttl)
        return True

    async def release(self, code: str, instance_id: str) -> None:
        if self._live(code) == instance_id:
            del self._owners[code]


class RedisRegistry:
    """Redis-backed registry shared by every instance. Ownership is a TTL key the owner refreshes."""

    def __init__(self, redis: Redis, prefix: str = "hajime:room:") -> None:
        self._redis = redis
        self._prefix = prefix

    def _key(self, code: str) -> str:
        return f"{self._prefix}{code}"

    async def claim(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        return bool(await self._redis.set(self._key(code), instance_id, nx=True, px=int(ttl * 1000)))

    async def owner(self, code: str) -> str | None:
        value = await self._redis.get(self._key(code))
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def _if_owner(self, code: str, instance_id: str, ttl: float | None) -> bool:
        key = self._key(code)
        async with self._redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(key)
                current = await pipe.get(key)
                current_str = current.decode() if isinstance(current, bytes) else current
                if current_str != instance_id:
                    await pipe.unwatch()  # type: ignore[no-untyped-call]
                    return False
                pipe.multi()  # type: ignore[no-untyped-call]
                if ttl is None:
                    pipe.delete(key)
                else:
                    pipe.pexpire(key, int(ttl * 1000))
                await pipe.execute()
                return True
            except WatchError:
                return False

    async def refresh(self, code: str, instance_id: str, ttl: float = ROOM_TTL_SECONDS) -> bool:
        return await self._if_owner(code, instance_id, ttl)

    async def release(self, code: str, instance_id: str) -> None:
        await self._if_owner(code, instance_id, None)
