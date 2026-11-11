"""Integration helpers: a real uvicorn server in-process and real websocket clients."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import uvicorn
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from app.core.config import AppSettings
from app.core.ratelimit import MemoryWindowLimiter, WindowLimiter
from app.japanese.candidates import CandidateIndex
from app.japanese.dictionary import Dictionary
from app.main import create_app
from app.realtime.clock import RoomClock, ScaledClock
from app.realtime.registry import RoomRegistry

ORIGIN = "http://localhost:5173"
CSRF = {"Origin": ORIGIN, "X-Hajime-Client": "web", "Content-Type": "application/json"}


class RunningServer:
    def __init__(self, app_server: uvicorn.Server, task: asyncio.Task[None], port: int, app: Any) -> None:
        self.server = app_server
        self.task = task
        self.port = port
        self.app = app
        self.http = httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}")

    @property
    def manager(self) -> Any:
        return self.app.state.manager

    async def create_room(self) -> str:
        response = await self.http.post("/api/rooms", headers=CSRF)
        assert response.status_code == 201, response.text
        return str(response.json()["code"])

    def client(self, code: str, **kwargs: Any) -> Client:
        return Client(f"ws://127.0.0.1:{self.port}/ws/{code}", **kwargs)

    async def stop(self) -> None:
        await self.http.aclose()
        self.server.should_exit = True
        await self.task


@contextlib.asynccontextmanager
async def running_server(
    dictionary: Dictionary,
    *,
    scale: float = 20.0,
    registry: RoomRegistry | None = None,
    instance_id: str = "A",
    limiter: WindowLimiter | None = None,
    clock: RoomClock | None = None,
    candidates: CandidateIndex | None = None,
    **overrides: Any,
) -> AsyncIterator[RunningServer]:
    settings = AppSettings(
        instance_id=instance_id,
        redis_url=None,
        countdown_seconds=overrides.pop("countdown_seconds", 3.0),
        grace_seconds=overrides.pop("grace_seconds", 30.0),
        min_fragment_words=80,
        preload_bots=False,  # tests that need CPU players pass a shared index instead
        **overrides,
    )
    app = create_app(
        settings,
        registry=registry,
        clock=clock or ScaledClock(scale),
        limiter=limiter or MemoryWindowLimiter(),
        dictionary=dictionary,
        candidates=candidates,
    )
    config = uvicorn.Config(
        app, host="127.0.0.1", port=0, log_level="warning", lifespan="on", ws_ping_interval=None
    )
    server = uvicorn.Server(config)
    task = asyncio.get_running_loop().create_task(server.serve())
    for _ in range(400):
        if server.started:
            break
        await asyncio.sleep(0.01)
    else:
        raise RuntimeError("server did not start")
    port = server.servers[0].sockets[0].getsockname()[1]
    running = RunningServer(server, task, port, app)
    try:
        yield running
    finally:
        await running.stop()


class Client:
    """Websocket client that records every server message."""

    def __init__(self, url: str, origin: str | None = ORIGIN) -> None:
        self.url = url
        self.origin = origin
        self.ws: ClientConnection | None = None
        self.messages: list[dict[str, Any]] = []
        self.player_id = ""
        self.token = ""
        self.close_code: int | None = None
        self._reader: asyncio.Task[None] | None = None
        self._event = asyncio.Event()

    async def __aenter__(self) -> Client:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        self.ws = await connect(self.url, origin=self.origin)  # type: ignore[arg-type]
        self._reader = asyncio.get_running_loop().create_task(self._read())

    async def _read(self) -> None:
        assert self.ws is not None
        try:
            async for raw in self.ws:
                message = json.loads(raw)
                self.messages.append(message)
                if message["t"] == "welcome":
                    self.player_id, self.token = message["player_id"], message["token"]
                self._event.set()
        except ConnectionClosed as exc:
            self.close_code = exc.rcvd.code if exc.rcvd else None
        finally:
            if self.close_code is None and self.ws is not None:
                self.close_code = self.ws.close_code
            self._event.set()

    async def send(self, **message: Any) -> None:
        assert self.ws is not None
        await self.ws.send(json.dumps(message))

    async def send_raw(self, raw: str) -> None:
        assert self.ws is not None
        await self.ws.send(raw)

    async def join(self, room: str, name: str = "Yanis", **extra: Any) -> dict[str, Any]:
        await self.send(t="join", room=room, name=name, **extra)
        return await self.wait("snapshot")

    async def wait(
        self,
        tag: str,
        where: Callable[[dict[str, Any]], bool] | None = None,
        timeout: float = 5.0,
        start: int = 0,
    ) -> dict[str, Any]:
        """Wait for a message with ``tag`` (searching already received ones from index ``start``)."""
        deadline = asyncio.get_running_loop().time() + timeout
        index = start
        while True:
            while index < len(self.messages):
                message = self.messages[index]
                index += 1
                if message["t"] == tag and (where is None or where(message)):
                    return message
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0 or (self.close_code is not None and index >= len(self.messages)):
                raise AssertionError(f"timeout waiting for {tag}; got {[m['t'] for m in self.messages]}")
            self._event.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._event.wait(), timeout=remaining)

    def last(self, tag: str) -> dict[str, Any] | None:
        return next((m for m in reversed(self.messages) if m["t"] == tag), None)

    def count(self, tag: str) -> int:
        return sum(1 for m in self.messages if m["t"] == tag)

    async def wait_closed(self, timeout: float = 5.0) -> int | None:
        assert self._reader is not None
        await asyncio.wait_for(self._reader, timeout=timeout)
        return self.close_code

    async def drop(self) -> None:
        """Simulate a network drop: kill the TCP connection without a closing handshake."""
        assert self.ws is not None
        self.ws.transport.abort()
        if self._reader is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._reader, timeout=2)

    async def close(self) -> None:
        if self.ws is not None:
            with contextlib.suppress(Exception):
                await self.ws.close()
        if self._reader is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self._reader, timeout=2)
