"""A client connection as seen by a room: a bounded outbound queue and a few flags.

The websocket handler owns the real socket and drains ``queue``. If a client cannot keep up the queue fills
and the connection is closed (backpressure) instead of growing memory without bound.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field

_ids = itertools.count(1)


@dataclass(slots=True)
class CloseRequest:
    code: int
    reason: str


@dataclass(eq=False)
class Connection:
    ip: str
    queue_size: int = 256
    id: int = field(default_factory=lambda: next(_ids))
    member_id: str | None = None
    last_seen: float = field(default_factory=time.monotonic)
    closed: bool = False
    latency: float = 0.0  # round trip in seconds, as the client measured it: credited to its answers' speed
    queue: asyncio.Queue[str | CloseRequest] = field(init=False)

    def __post_init__(self) -> None:
        self.queue = asyncio.Queue(maxsize=self.queue_size)

    def offer(self, data: str) -> bool:
        """Queue a frame. Returns False (and schedules a close) if the client is too slow."""
        if self.closed:
            return False
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull:
            self.close(1013, "slow_consumer")
            return False
        return True

    def close(self, code: int = 1000, reason: str = "") -> None:
        """Ask the websocket handler to close the socket after flushing what is queued."""
        if self.closed:
            return
        self.closed = True
        try:
            self.queue.put_nowait(CloseRequest(code, reason))
        except asyncio.QueueFull:
            # Drop pending frames so the close request always gets through.
            while not self.queue.empty():
                self.queue.get_nowait()
            self.queue.put_nowait(CloseRequest(code, reason))
