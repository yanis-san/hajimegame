"""RoomRegistry: memory and Redis implementations, and two instances sharing one Redis."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import fakeredis
import pytest
from redis.asyncio import Redis
from websockets.exceptions import InvalidStatus

from app.core.ratelimit import RedisWindowLimiter
from app.japanese.dictionary import Dictionary
from app.realtime.registry import MemoryRegistry, RedisRegistry, RoomRegistry
from tests.realtime.helpers import running_server


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = fakeredis.FakeAsyncRedis()
    yield client
    await client.aclose()


@pytest.fixture(params=["memory", "redis"])
async def registry(request: pytest.FixtureRequest, redis: Redis) -> RoomRegistry:
    return MemoryRegistry() if request.param == "memory" else RedisRegistry(redis)


async def test_claim_is_exclusive(registry: RoomRegistry) -> None:
    assert await registry.claim("ABC234", "A") is True
    assert await registry.claim("ABC234", "B") is False
    assert await registry.owner("ABC234") == "A"
    assert await registry.owner("NOPE22") is None


async def test_only_the_owner_can_refresh_or_release(registry: RoomRegistry) -> None:
    await registry.claim("ABC234", "A")
    assert await registry.refresh("ABC234", "B") is False
    assert await registry.refresh("ABC234", "A") is True
    await registry.release("ABC234", "B")
    assert await registry.owner("ABC234") == "A"
    await registry.release("ABC234", "A")
    assert await registry.owner("ABC234") is None
    assert await registry.refresh("ABC234", "A") is False
    assert await registry.claim("ABC234", "B") is True


async def test_ownership_expires(registry: RoomRegistry) -> None:
    assert await registry.claim("ABC234", "A", ttl=0.05)
    await asyncio.sleep(0.12)
    assert await registry.owner("ABC234") is None
    assert await registry.claim("ABC234", "B") is True


async def test_redis_limiter_counts_across_callers(redis: Redis) -> None:
    one, two = RedisWindowLimiter(redis), RedisWindowLimiter(redis)
    results = [await (one if i % 2 else two).allow("ip:1", 3, 60) for i in range(5)]
    assert results == [True, True, True, False, False]
    assert await one.allow("ip:2", 3, 60) is True


async def test_two_instances_route_rooms_by_owner(dictionary: Dictionary, redis: Redis) -> None:
    shared = RedisRegistry(redis)
    async with (
        running_server(dictionary, registry=shared, instance_id="A") as a,
        running_server(dictionary, registry=RedisRegistry(redis), instance_id="B") as b,
    ):
        code = await a.create_room()
        # B does not hold the room but knows who does
        assert b.manager.get_local(code) is None
        assert await b.manager.resolve(code) == "A"
        assert (await b.http.get(f"/api/rooms/{code}")).json() == {"code": code, "remote": True}
        # A resolves it locally
        assert (await a.http.get(f"/api/rooms/{code}")).json()["phase"] == "lobby"

        # A websocket landing on B is denied with a fly-replay header pointing at A
        wrong = b.client(code)
        with pytest.raises(InvalidStatus) as info:
            await wrong.connect()
        headers = info.value.response.headers
        assert headers["fly-replay"] == "instance=A"
        assert info.value.response.status_code == 409

        # Replaying to A works and the game is served there
        async with a.client(code) as right:
            snap = await right.join(code, "Aya")
            assert snap["room"] == code


async def test_codes_never_collide_across_instances(dictionary: Dictionary, redis: Redis) -> None:
    async with (
        running_server(dictionary, registry=RedisRegistry(redis), instance_id="A", max_rooms_per_ip=500) as a,
        running_server(dictionary, registry=RedisRegistry(redis), instance_id="B", max_rooms_per_ip=500) as b,
    ):
        codes = [await a.manager.create("ip1") for _ in range(30)] + [
            await b.manager.create("ip2") for _ in range(30)
        ]
        assert len({room.code for room in codes}) == 60


async def test_a_closed_room_releases_its_code(dictionary: Dictionary, redis: Redis) -> None:
    async with running_server(dictionary, registry=RedisRegistry(redis), instance_id="A") as a:
        code = await a.create_room()
        assert await RedisRegistry(redis).owner(code) == "A"
        room = a.manager.get_local(code)
        assert room is not None
        await room.shutdown()
        await room.wait_closed()
        await asyncio.sleep(0.05)
        assert await RedisRegistry(redis).owner(code) is None
