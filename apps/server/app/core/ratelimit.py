"""Rate limiting: a local token bucket per connection, plus windowed counters per IP (memory or Redis)."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis


class TokenBucket:
    """Allows ``rate`` events per second with bursts up to ``burst``. Not thread-safe, one per connection."""

    def __init__(self, rate: float, burst: int, now: Callable[[], float] = time.monotonic) -> None:
        self._rate = rate
        self._burst = float(burst)
        self._tokens = float(burst)
        self._now = now
        self._last = now()

    def allow(self, cost: float = 1.0) -> bool:
        now = self._now()
        self._tokens = min(self._burst, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False


class WindowLimiter(Protocol):
    async def allow(self, key: str, limit: int, window_seconds: int) -> bool: ...


class MemoryWindowLimiter:
    """Fixed-window counter in process memory."""

    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._windows: dict[str, tuple[float, int]] = {}
        self._calls = 0

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = self._now()
        start, count = self._windows.get(key, (now, 0))
        if now - start >= window_seconds:
            start, count = now, 0
        count += 1
        self._windows[key] = (start, count)
        self._calls += 1
        if self._calls % 1024 == 0:
            self._windows = {k: v for k, v in self._windows.items() if now - v[0] < 3600}
        return count <= limit


class RedisWindowLimiter:
    """Fixed-window counter shared by all instances (INCR + EXPIRE)."""

    def __init__(self, redis: Redis, prefix: str = "hajime:rl:") -> None:
        self._redis = redis
        self._prefix = prefix

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        full = f"{self._prefix}{key}"
        count = int(await self._redis.incr(full))
        if count == 1:
            await self._redis.expire(full, window_seconds)
        return count <= limit


class Counters:
    """Tiny helper for per-key counters used by tests and the room cap per IP."""

    def __init__(self) -> None:
        self._values: dict[str, int] = defaultdict(int)

    def incr(self, key: str) -> int:
        self._values[key] += 1
        return self._values[key]

    def decr(self, key: str) -> int:
        self._values[key] = max(0, self._values[key] - 1)
        return self._values[key]

    def get(self, key: str) -> int:
        return self._values[key]
