from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core import metrics
from app.db.recorder import DatabaseRecorder
from app.games.bomb.recording import BombDetail, BombTurn
from app.games.recording import GameRecord, PlayerRecord

GUEST = uuid.UUID("11111111-2222-3333-4444-555555555555")


def make_record(room: str = "ABC234") -> GameRecord:
    return GameRecord(
        kind="bomb",
        id=uuid.uuid4(),
        room_code=room,
        mode="classic",
        settings={"lives": 2, "fuse_seconds": 10.0},
        started_at=datetime(2026, 11, 12, 10, 0, 0),
        ended_at=datetime(2026, 11, 12, 10, 1, 0),
        duration_ms=60_000,
        players=(
            PlayerRecord(0, "Aya", GUEST, "fr", False, None, 1, 5, 2, "きもの", 0, 2000),
            PlayerRecord(1, "Momo", None, None, True, "hard", 2, 0, 0, "", 2, None),
        ),
        detail=BombDetail(
            turns=(
                BombTurn(1, 0, "か", "word", "かさ", "かさ", 1000, 10_000, 1),
                BombTurn(2, 1, "き", "explosion", "", "", None, 10_000, 0),
            )
        ),
    )


def counter(result: str) -> float:
    return metrics.GAME_RECORDS.labels(result)._value.get()  # type: ignore[no-any-return]


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


async def rows(engine: AsyncEngine, query: str) -> list[tuple[Any, ...]]:
    async with engine.connect() as connection:
        return [tuple(row) for row in (await connection.execute(sa.text(query))).all()]


async def test_a_finished_game_is_stored_with_its_players_and_turns(engine: AsyncEngine) -> None:
    recorder = DatabaseRecorder(engine)
    record = make_record()
    await recorder.save(record)

    game = (await rows(engine, "select mode, room_code, duration_ms, players_count, bots_count from games"))[
        0
    ]
    assert tuple(game) == ("classic", "ABC234", 60_000, 1, 1)
    players = await rows(
        engine,
        "select seat, display_name, lang, is_bot, bot_difficulty, place, score, explosions, avg_response_ms"
        " from game_players order by seat",
    )
    assert players == [
        (0, "Aya", "fr", False, None, 1, 5, 0, 2000),
        (1, "Momo", None, True, "hard", 2, 0, 2, None),
    ]
    guest = (await rows(engine, "select guest_id from game_players where seat = 0"))[0][0]
    assert uuid.UUID(str(guest)) == GUEST
    turns = await rows(
        engine, "select turn, seat, fragment, outcome, word, response_ms from bomb_turns order by turn"
    )
    assert turns == [
        (1, 0, "か", "word", "かさ", 1000),
        (2, 1, "き", "explosion", "", None),
    ]


async def test_submit_writes_in_the_background_and_stop_flushes(engine: AsyncEngine) -> None:
    recorder = DatabaseRecorder(engine)
    recorder.start()
    for room in ("ROOM01", "ROOM02", "ROOM03"):
        recorder.submit(make_record(room))  # returns at once: nothing is written yet
    await recorder.stop()
    assert {r[0] for r in await rows(engine, "select room_code from games")} == {"ROOM01", "ROOM02", "ROOM03"}


async def test_a_failing_database_is_retried_then_the_record_is_written(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = DatabaseRecorder(engine, pauses=(0.0, 0.0, 0.0))
    real_save = recorder.save
    attempts = 0

    async def flaky(record: GameRecord) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("database restarting")
        await real_save(record)

    monkeypatch.setattr(recorder, "save", flaky)
    saved_before = counter("saved")
    recorder.start()
    recorder.submit(make_record())
    await recorder.stop()
    assert attempts == 3
    assert counter("saved") == saved_before + 1
    assert len(await rows(engine, "select id from games")) == 1


async def test_a_record_that_cannot_be_written_is_given_up_without_blocking_the_next(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    recorder = DatabaseRecorder(engine, pauses=(0.0,))
    real_save = recorder.save

    async def broken_for_the_first(record: GameRecord) -> None:
        if record.room_code == "BAD001":
            raise ConnectionError("always down for this one")
        await real_save(record)

    monkeypatch.setattr(recorder, "save", broken_for_the_first)
    failed_before = counter("failed")
    recorder.start()
    recorder.submit(make_record("BAD001"))
    recorder.submit(make_record("GOOD01"))
    await recorder.stop()
    assert counter("failed") == failed_before + 1
    assert [r[0] for r in await rows(engine, "select room_code from games")] == ["GOOD01"]


async def test_a_full_queue_drops_the_oldest_record_and_counts_it(engine: AsyncEngine) -> None:
    recorder = DatabaseRecorder(engine, queue_size=2)  # the worker is not started: nothing is consumed
    dropped_before = counter("dropped")
    for room in ("ROOM01", "ROOM02", "ROOM03"):
        recorder.submit(make_record(room))
    assert counter("dropped") == dropped_before + 1
    recorder.start()
    await recorder.stop()
    assert {r[0] for r in await rows(engine, "select room_code from games")} == {"ROOM02", "ROOM03"}


async def test_submit_never_waits_for_the_database(engine: AsyncEngine) -> None:
    recorder = DatabaseRecorder(engine)
    started = asyncio.get_running_loop().time()
    for _ in range(100):
        recorder.submit(make_record())
    assert asyncio.get_running_loop().time() - started < 0.2
