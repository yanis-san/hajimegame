"""Per-process room manager: creates rooms, resolves codes and keeps registry ownership fresh."""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from collections import defaultdict

from app.core import metrics
from app.core.config import AppSettings
from app.core.logging import get_logger
from app.japanese.candidates import CandidateIndex
from app.japanese.dictionary import Dictionary
from app.japanese.fragments import FragmentTable
from app.realtime.clock import RoomClock
from app.realtime.registry import ROOM_TTL_SECONDS, RoomRegistry
from app.realtime.room import Room, RoomDeps

log = get_logger("manager")

# No 0/O, 1/I/L: unambiguous when read aloud or typed on a phone.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_LENGTH = 6


class CapacityError(Exception):
    """Raised when this instance or an IP has reached its room limit."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(raw: str) -> str:
    return raw.strip().upper()


class RoomManager:
    def __init__(
        self,
        settings: AppSettings,
        dictionary: Dictionary,
        fragments: FragmentTable,
        registry: RoomRegistry,
        clock: RoomClock,
        instance_id: str | None = None,
    ) -> None:
        self._settings = settings
        self._dictionary = dictionary
        self._fragments = fragments
        self._registry = registry
        self._clock = clock
        self.instance_id = instance_id or settings.instance_id
        self._rooms: dict[str, Room] = {}
        self._by_ip: dict[str, set[str]] = defaultdict(set)
        self._refresher: asyncio.Task[None] | None = None
        self.candidates: CandidateIndex | None = None  # CPU word index, filled in the background
        self._release_tasks: set[asyncio.Task[None]] = set()

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> None:
        self._refresher = asyncio.get_running_loop().create_task(
            self._refresh_loop(), name="registry-refresh"
        )

    async def shutdown(self) -> None:
        if self._refresher is not None:
            self._refresher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._refresher
        for room in list(self._rooms.values()):
            await room.shutdown()
        for room in list(self._rooms.values()):
            await room.wait_closed()
        if self._release_tasks:
            await asyncio.gather(*self._release_tasks, return_exceptions=True)

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(ROOM_TTL_SECONDS / 3)
            for code in list(self._rooms):
                try:
                    await self._registry.refresh(code, self.instance_id)
                except Exception:
                    log.exception("registry_refresh_failed", room=code)

    # ------------------------------------------------------------------ rooms

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    async def create(self, ip: str, mode: str = "classic") -> Room:
        if len(self._rooms) >= self._settings.max_rooms_total:
            raise CapacityError("server_full")
        if len(self._by_ip[ip]) >= self._settings.max_rooms_per_ip:
            raise CapacityError("too_many_rooms")
        for _ in range(20):
            code = generate_code()
            if await self._registry.claim(code, self.instance_id):
                break
        else:
            raise CapacityError("no_code_available")
        deps = RoomDeps(
            settings=self._settings,
            dictionary=self._dictionary,
            fragments=self._fragments,
            get_candidates=lambda: self.candidates,
            clock=self._clock,
            on_close=self._on_room_closed,
        )
        room = Room(code, deps, host_ip=ip, mode=mode)
        self._rooms[code] = room
        self._by_ip[ip].add(code)
        metrics.ROOMS_ACTIVE.set(len(self._rooms))
        room.start()
        log.info("room_created", room=code)
        return room

    def get_local(self, code: str) -> Room | None:
        return self._rooms.get(normalize_code(code))

    async def resolve(self, code: str) -> Room | str | None:
        """Local room, the owning instance id if the room lives elsewhere, or None if it does not exist."""
        code = normalize_code(code)
        room = self._rooms.get(code)
        if room is not None:
            return room
        owner = await self._registry.owner(code)
        if owner is not None and owner != self.instance_id:
            return owner
        return None

    def _on_room_closed(self, room: Room) -> None:
        self._rooms.pop(room.code, None)
        ip_rooms = self._by_ip.get(room.host_ip)
        if ip_rooms is not None:
            ip_rooms.discard(room.code)
            if not ip_rooms:
                del self._by_ip[room.host_ip]
        metrics.ROOMS_ACTIVE.set(len(self._rooms))
        task = asyncio.get_running_loop().create_task(self._registry.release(room.code, self.instance_id))
        self._release_tasks.add(task)
        task.add_done_callback(self._release_tasks.discard)
        log.info("room_closed", room=room.code)
