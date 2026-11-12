"""Writes finished games to the database, in the background.

The game never waits for the database: a room hands its finished ``GameRecord`` to ``submit``, which only puts
it in a bounded queue. A single worker task writes the records, retrying a few times with a growing pause.
If the database is down for long, the oldest queued records are dropped and counted, and the game carries on.
Failures are logged with the game id and counted in ``hajime_game_records_total{result="failed"}``.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core import metrics
from app.core.logging import get_logger
from app.db.games import store_for
from app.db.models import Base, Game, GamePlayer
from app.games.recording import GameRecord

log = get_logger("recorder")

QUEUE_SIZE = 500
RETRY_PAUSES = (1.0, 5.0, 20.0)  # seconds between attempts: three retries after the first try
STOP_TIMEOUT = 15.0  # at shutdown, how long to keep trying to write what is still queued


def to_rows(record: GameRecord) -> tuple[Game, Sequence[Base]]:
    """The ORM objects for one finished game: the common rows, and the rows only that game has."""
    game = Game(
        id=record.id,
        kind=record.kind,
        mode=record.mode,
        room_code=record.room_code,
        settings=record.settings,
        started_at=record.started_at,
        ended_at=record.ended_at,
        duration_ms=record.duration_ms,
        players_count=sum(1 for p in record.players if not p.is_bot),
        bots_count=sum(1 for p in record.players if p.is_bot),
        players=[
            GamePlayer(
                seat=p.seat,
                display_name=p.name,
                place=p.place,
                score=p.score,
                words=p.words,
                longest_word=p.longest_word,
                guest_id=p.guest_id,
                lang=p.lang,
                is_bot=p.is_bot,
                bot_difficulty=p.bot_difficulty,
                explosions=p.explosions,
                avg_response_ms=p.avg_response_ms,
            )
            for p in record.players
        ],
    )
    return game, store_for(record.kind).detail_rows(record)


class DatabaseRecorder:
    """A ``Recorder`` backed by a database engine."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        queue_size: int = QUEUE_SIZE,
        pauses: tuple[float, ...] = RETRY_PAUSES,
    ) -> None:
        self._sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
        self._queue: deque[GameRecord] = deque(maxlen=queue_size)  # full: the oldest record is dropped
        self._pauses = pauses
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._stopping = False

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.get_running_loop().create_task(self._run(), name="game-recorder")

    def submit(self, record: GameRecord) -> None:
        if len(self._queue) == self._queue.maxlen:
            metrics.GAME_RECORDS.labels("dropped").inc()
            log.error("game_record_dropped", game=str(self._queue[0].id))
        self._queue.append(record)
        metrics.GAME_RECORDS_QUEUED.set(len(self._queue))
        self._wake.set()

    async def stop(self) -> None:
        """Write what is still queued (for a limited time), then stop the worker."""
        self._stopping = True
        self._wake.set()
        task, self._task = self._task, None
        if task is None:
            return
        try:
            await asyncio.wait_for(task, STOP_TIMEOUT)
        except TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            log.error("game_records_lost_at_shutdown", count=len(self._queue))

    async def _run(self) -> None:
        while True:
            if not self._queue:
                if self._stopping:
                    return
                self._wake.clear()
                await self._wake.wait()
                continue
            # Taken out of the queue before writing, so a full queue dropping its oldest entry can never drop
            # (or double-remove) the record being written. A record that cannot be written is given up on and
            # counted: it must not block the ones behind it.
            record = self._queue.popleft()
            metrics.GAME_RECORDS_QUEUED.set(len(self._queue))
            await self._write_with_retries(record)

    async def _write_with_retries(self, record: GameRecord) -> bool:
        attempts = 1 + len(self._pauses)
        for attempt in range(attempts):
            try:
                await self.save(record)
            except Exception:
                log.exception("game_record_failed", game=str(record.id), attempt=attempt + 1)
                if attempt < len(self._pauses) and not self._stopping:
                    await asyncio.sleep(self._pauses[attempt])  # shutting down: retry at once, no pause
            else:
                metrics.GAME_RECORDS.labels("saved").inc()
                return True
        metrics.GAME_RECORDS.labels("failed").inc()
        log.error("game_record_gave_up", game=str(record.id))
        return False

    async def save(self, record: GameRecord) -> None:
        """Write one finished game in a single transaction."""
        game, detail = to_rows(record)
        async with self._sessions() as session, session.begin():
            session.add(game)
            # The common rows go first: a game's own rows refer to them (a foreign key) and are not
            # tied to the common model by a relationship, so the order must be stated. SQLite does not
            # check foreign keys by default and would hide a wrong order; PostgreSQL refuses it.
            await session.flush()
            session.add_all(detail)
