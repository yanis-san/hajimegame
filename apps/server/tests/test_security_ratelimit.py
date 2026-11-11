from __future__ import annotations

import pytest

from app.core.config import AppSettings
from app.core.ratelimit import Counters, MemoryWindowLimiter, TokenBucket
from app.core.security import (
    clean_text,
    contains_profanity,
    is_origin_allowed,
    sanitize_chat,
    sanitize_nickname,
)
from app.realtime.clock import ScaledClock, SystemClock, to_ms


class FakeTime:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_token_bucket_refills_over_time() -> None:
    clock = FakeTime()
    bucket = TokenBucket(rate=2, burst=3, now=clock)
    assert [bucket.allow() for _ in range(4)] == [True, True, True, False]
    clock.t += 1.0  # two tokens back
    assert [bucket.allow() for _ in range(3)] == [True, True, False]
    clock.t += 100
    assert sum(bucket.allow() for _ in range(10)) == 3  # never above burst


async def test_memory_window_limiter_resets() -> None:
    clock = FakeTime()
    limiter = MemoryWindowLimiter(now=clock)
    assert [await limiter.allow("k", 2, 10) for _ in range(3)] == [True, True, False]
    assert await limiter.allow("other", 2, 10) is True
    clock.t += 11
    assert await limiter.allow("k", 2, 10) is True


async def test_memory_window_limiter_garbage_collects() -> None:
    clock = FakeTime()
    limiter = MemoryWindowLimiter(now=clock)
    for i in range(1100):
        await limiter.allow(f"k{i}", 5, 1)
        clock.t += 4
    assert len(limiter._windows) < 1100


def test_counters() -> None:
    c = Counters()
    assert c.incr("a") == 1
    assert c.incr("a") == 2
    assert c.decr("a") == 1
    assert c.decr("b") == 0
    assert c.get("a") == 1


@pytest.mark.parametrize(
    "name",
    [
        "fuck",
        "F.u.c.k",
        "f u c k",
        "FUCK you",
        "m3rde",
        "connard42",
        "Putain",
        "死ね",
        "ちんこ",
        "con",
        "cunt",
    ],
)
def test_profanity_is_caught(name: str) -> None:
    assert contains_profanity(name)
    assert sanitize_nickname(name) is None


@pytest.mark.parametrize("name", ["Yanis", "さくら", "Computer", "Scunthorpe", "Cassandre", "Dick", "Aya"])
def test_clean_names_pass(name: str) -> None:
    assert sanitize_nickname(name) == name


def test_nickname_sanitation() -> None:
    assert sanitize_nickname("   ") is None
    assert sanitize_nickname("​‮") is None
    assert sanitize_nickname("A" * 50) == "A" * 20
    assert sanitize_nickname("  a   b  ") == "a b"
    assert sanitize_nickname("ＡＢＣ") == "ABC"
    assert clean_text("a\x00b‮c", 10) == "abc"


def test_chat_sanitation() -> None:
    assert sanitize_chat("  salut  ") == "salut"
    assert sanitize_chat("tu es un connard") is None
    assert sanitize_chat("") is None


def test_origin_policy() -> None:
    settings = AppSettings(allowed_origins=["https://hajime.example"], allow_missing_origin=False)
    assert is_origin_allowed("https://hajime.example", settings)
    assert is_origin_allowed("https://hajime.example/", settings)
    assert not is_origin_allowed("https://evil.example", settings)
    assert not is_origin_allowed("null", settings)
    assert not is_origin_allowed(None, settings)
    assert is_origin_allowed(None, AppSettings(allow_missing_origin=True))


def test_clocks() -> None:
    assert SystemClock().real_delay(2.5) == 2.5
    fast = ScaledClock(10)
    assert fast.real_delay(5) == 0.5
    first = fast.now()
    assert fast.now() >= first
    assert to_ms(1.23456) == 1234.6


def test_dev_accepts_local_network_origins_on_any_port_but_prod_does_not() -> None:
    dev = AppSettings(env="dev", allowed_origins=[], allow_missing_origin=False)
    for origin in (
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://192.168.100.25:5173",
        "http://100.121.20.68:5173",
    ):
        assert is_origin_allowed(origin, dev), origin
    for origin in (
        "https://evil.example",
        "http://192.169.0.1:5173",
        "http://localhost.evil.example",
        "http://8.8.8.8:5173",
    ):
        assert not is_origin_allowed(origin, dev), origin
    prod = AppSettings(env="prod", allowed_origins=["https://hajime.dev"], allow_missing_origin=False)
    assert is_origin_allowed("https://hajime.dev", prod)
    assert not is_origin_allowed("http://localhost:5174", prod)
