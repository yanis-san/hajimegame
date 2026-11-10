"""Room actor: one asyncio task owns all state of one room and processes a single command queue.

Everything that can change the room (client messages, disconnects, timers) goes through
``_handle`` so there are
no races. The room never touches the database. The game itself is delegated to a ``GameEngine``.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from msgspec import UNSET

from app.core import metrics
from app.core.config import AppSettings
from app.core.logging import get_logger
from app.core.ratelimit import TokenBucket
from app.core.security import sanitize_chat, sanitize_nickname
from app.games.base import GameEvent, Phase, PlayerInfo
from app.games.bomb import events as ev
from app.games.bomb.engine import BombEngine
from app.games.bomb.settings import BombSettings
from app.japanese.dictionary import Dictionary
from app.japanese.fragments import FragmentTable
from app.realtime import protocol as pr
from app.realtime.clock import RoomClock, to_ms
from app.realtime.connection import Connection

log = get_logger("room")

WORD_HISTORY = 40
TYPING_INTERVAL = 0.1  # at most 10 relayed typing updates per second
ZOMBIE_FACTOR = 3.0


@dataclass(eq=False)
class Member:
    id: str
    name: str
    avatar: int
    token: str
    spectator: bool
    order: int
    conn: Connection | None = None
    ready: bool = False
    chat_bucket: TokenBucket = field(default_factory=lambda: TokenBucket(1.0, 3))


@dataclass(slots=True)
class Command:
    kind: str  # "msg" | "disconnect" | "shutdown"
    conn: Connection | None = None
    msg: pr.ClientMessage | None = None
    at: float = 0.0
    received: float = 0.0


@dataclass(slots=True)
class RoomDeps:
    settings: AppSettings
    dictionary: Dictionary
    tables: dict[str, FragmentTable]
    clock: RoomClock
    rng_factory: Callable[[], random.Random] = lambda: random.Random(secrets.randbits(64))  # noqa: S311
    on_close: Callable[[Room], None] | None = None


class Room:
    def __init__(self, code: str, deps: RoomDeps, host_ip: str = "") -> None:
        self.code = code
        self.host_ip = host_ip
        self._deps = deps
        self._cfg = deps.settings
        self.clock = deps.clock
        self._queue: asyncio.Queue[Command] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._timers: dict[str, float] = {}
        self._members: dict[str, Member] = {}
        self._join_counter = 0
        self._host: str = ""
        self._phase: pr.RoomPhase = "lobby"
        self._settings = BombSettings(max_players=self._cfg.max_players_per_room)
        self._engine: BombEngine | None = None
        self._seq = 0
        self._turn: pr.TurnView | None = None
        self._typing = ""
        self._typing_sent_at = 0.0
        self._words: list[pr.WordView] = []
        self._results: list[pr.ResultRow] | None = None
        self._countdown_ends: float | None = None
        self._closed = False
        self._empty_since: float | None = self.clock.now()
        self._arm("idle", self._cfg.room_idle_seconds)
        self._arm("heartbeat", self._cfg.heartbeat_seconds)

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run(), name=f"room-{self.code}")

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def phase(self) -> pr.RoomPhase:
        return self._phase

    def player_count(self) -> int:
        return sum(1 for m in self._members.values() if not m.spectator)

    def summary(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "phase": self._phase,
            "players": self.player_count(),
            "max_players": self._settings.max_players,
            "level": self._settings.level,
        }

    def submit(self, cmd: Command) -> None:
        if not self._closed:
            self._queue.put_nowait(cmd)

    def message(self, conn: Connection, msg: pr.ClientMessage) -> None:
        now = time.monotonic()
        self.submit(Command("msg", conn, msg, at=self.clock.now(), received=now))

    def disconnected(self, conn: Connection) -> None:
        self.submit(Command("disconnect", conn))

    async def shutdown(self, code: int = 1012, reason: str = "server_restarting") -> None:
        if self._closed:
            return
        for member in self._members.values():
            if member.conn is not None:
                self._send(
                    member.conn, pr.Error, code="server_restarting", message="Server restarting, reconnect"
                )
                member.conn.close(code, reason)
        self._finalize()
        if self._task is not None:
            self._task.cancel()

    async def wait_closed(self) -> None:
        if self._task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def _finalize(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._deps.on_close is not None:
            self._deps.on_close(self)

    # ------------------------------------------------------------------ main loop

    async def _run(self) -> None:
        try:
            while not self._closed:
                delay = self._next_delay()
                try:
                    cmd: Command | None = await asyncio.wait_for(self._queue.get(), timeout=delay)
                except TimeoutError:
                    cmd = None
                if cmd is not None:
                    began = time.monotonic()
                    try:
                        self._handle(cmd)
                    except Exception:
                        log.exception("room_command_failed", room=self.code, kind=cmd.kind)
                    finished = time.monotonic()
                    metrics.HANDLE_LATENCY.observe(finished - began)
                    if cmd.received:
                        metrics.MESSAGE_LATENCY.observe(finished - cmd.received)
                self._fire_timers()
        finally:
            self._finalize()

    def _arm(self, name: str, delay_game_seconds: float) -> None:
        self._timers[name] = self.clock.now() + delay_game_seconds

    def _arm_at(self, name: str, due: float) -> None:
        self._timers[name] = due

    def _disarm(self, name: str) -> None:
        self._timers.pop(name, None)

    def _next_delay(self) -> float | None:
        if not self._timers:
            return None
        nearest = min(self._timers.values()) - self.clock.now()
        return max(0.0, self.clock.real_delay(nearest))

    def _fire_timers(self) -> None:
        now = self.clock.now()
        # Timeouts may wake a hair early; a timer within 2 ms of its due time counts as due.
        for name, due in sorted(self._timers.items(), key=lambda item: item[1]):
            if due > now + 0.002 or name not in self._timers:
                continue
            del self._timers[name]
            try:
                self._on_timer(name, due)
            except Exception:
                log.exception("room_timer_failed", room=self.code, timer=name)

    def _on_timer(self, name: str, due: float) -> None:
        if name == "turn":
            self._on_turn_timeout(due)
        elif name == "countdown":
            self._on_countdown_done()
        elif name == "typing":
            self._flush_typing()
        elif name == "idle":
            self._on_idle()
        elif name == "heartbeat":
            self._on_heartbeat()
        elif name.startswith("grace:"):
            self._on_grace_expired(name.removeprefix("grace:"))

    # ------------------------------------------------------------------ output helpers

    def _encode(self, cls: Any, bump: bool, **fields: Any) -> str:
        if bump:
            self._seq += 1
        return pr.encode(cls(seq=self._seq, **fields)).decode()

    def _emit(self, cls: Any, **fields: Any) -> None:
        """Sequenced broadcast to every connected member."""
        data = self._encode(cls, True, **fields)
        for member in self._members.values():
            if member.conn is not None:
                member.conn.offer(data)

    def _emit_ephemeral(self, cls: Any, exclude: str | None = None, **fields: Any) -> None:
        """Broadcast that does not advance ``seq`` (typing), so clients never see a gap."""
        data = self._encode(cls, False, **fields)
        for member in self._members.values():
            if member.conn is not None and member.id != exclude:
                member.conn.offer(data)

    def _send(self, conn: Connection, cls: Any, **fields: Any) -> None:
        conn.offer(self._encode(cls, False, **fields))

    def _error(self, conn: Connection, code: pr.ErrorCode, message: str = "") -> None:
        self._send(conn, pr.Error, code=code, message=message or code)

    # ------------------------------------------------------------------ views

    def _settings_view(self) -> pr.SettingsView:
        s = self._settings
        return pr.SettingsView(
            lives=s.lives,
            fuse_seconds=s.fuse_seconds,
            level=s.level,  # type: ignore[arg-type]
            max_players=s.max_players,
            bonus_kana=s.bonus_kana,
            tension=s.tension,
        )

    def _player_view(self, m: Member) -> pr.PlayerView:
        lives = self._settings.lives
        score = 0
        alive = True
        bonus: list[str] = []
        if self._engine is not None:
            state = next((p for p in self._engine.players if p.info.id == m.id), None)
            if state is not None:
                lives, score, alive = state.lives, state.score, state.alive
                bonus = sorted(state.bonus_left)
        return pr.PlayerView(
            id=m.id,
            name=m.name,
            avatar=m.avatar,
            ready=m.ready,
            connected=m.conn is not None,
            host=m.id == self._host,
            alive=alive,
            lives=lives,
            score=score,
            bonus=bonus,
        )

    def _players(self) -> list[Member]:
        return sorted((m for m in self._members.values() if not m.spectator), key=lambda m: m.order)

    def _spectator_count(self) -> int:
        return sum(1 for m in self._members.values() if m.spectator)

    def _snapshot(self, member: Member) -> str:
        data = pr.Snapshot(
            room=self.code,
            phase=self._phase,
            host=self._host,
            you=member.id,
            spectator=member.spectator,
            settings=self._settings_view(),
            players=[self._player_view(m) for m in self._players()],
            spectators=self._spectator_count(),
            turn=self._turn,
            typing=self._typing,
            words=self._words[-WORD_HISTORY:],
            countdown_ends=to_ms(self._countdown_ends) if self._countdown_ends is not None else None,
            results=self._results,
            server_time=to_ms(self.clock.now()),
            seq=self._seq,
        )
        return pr.encode(data).decode()

    def _patch(self, **fields: Any) -> None:
        self._emit(pr.Patch, **fields)

    def _patch_players(self, *members: Member, **extra: Any) -> None:
        self._patch(players={m.id: self._player_view(m) for m in members}, **extra)

    def _patch_all_players(self, **extra: Any) -> None:
        self._patch_players(*self._players(), **extra)

    # ------------------------------------------------------------------ dispatch

    def _handle(self, cmd: Command) -> None:
        if cmd.kind == "disconnect" and cmd.conn is not None:
            self._on_disconnect(cmd.conn)
            return
        if cmd.kind != "msg" or cmd.conn is None or cmd.msg is None:
            return
        conn, msg = cmd.conn, cmd.msg
        conn.last_seen = time.monotonic()
        if isinstance(msg, pr.Join):
            self._on_join(conn, msg)
            return
        if isinstance(msg, pr.Rejoin):
            self._on_rejoin(conn, msg)
            return
        member = self._members.get(conn.member_id or "")
        if member is None or member.conn is not conn:
            self._error(conn, "not_allowed", "join first")
            return
        if isinstance(msg, pr.Ready):
            self._on_ready(conn, member, msg)
        elif isinstance(msg, pr.Start):
            self._on_start(conn, member)
        elif isinstance(msg, pr.SetSettings):
            self._on_settings(conn, member, msg)
        elif isinstance(msg, pr.Typing):
            self._on_typing(member, msg, cmd.at)
        elif isinstance(msg, pr.Submit):
            self._on_submit(conn, member, msg, cmd.at)
        elif isinstance(msg, pr.Kick):
            self._on_kick(conn, member, msg)
        elif isinstance(msg, pr.Chat):
            self._on_chat(conn, member, msg)
        elif isinstance(msg, pr.Rematch):
            self._on_rematch(conn, member)
        elif isinstance(msg, pr.Leave):
            self._remove_member(member, notify_conn=True)

    # ------------------------------------------------------------------ join / leave

    def _unique_name(self, name: str) -> str:
        taken = {m.name.casefold() for m in self._members.values()}
        if name.casefold() not in taken:
            return name
        for n in range(2, 100):
            suffix = f" {n}"
            candidate = f"{name[: 20 - len(suffix)]}{suffix}"
            if candidate.casefold() not in taken:
                return candidate
        return name

    def _on_join(self, conn: Connection, msg: pr.Join) -> None:
        if conn.member_id is not None:
            self._error(conn, "not_allowed", "already joined")
            return
        name = sanitize_nickname(msg.name)
        if name is None:
            self._error(conn, "name_invalid", "Pseudo invalide")
            return
        spectator = msg.spectator
        if not spectator:
            if self._phase != "lobby":
                self._error(conn, "wrong_phase", "Partie en cours")
                return
            if self.player_count() >= self._settings.max_players:
                self._error(conn, "room_full", "Partie pleine")
                return
        elif self._spectator_count() >= self._cfg.max_spectators_per_room:
            self._error(conn, "room_full", "Trop de spectateurs")
            return
        self._join_counter += 1
        member = Member(
            id=secrets.token_hex(6),
            name=self._unique_name(name),
            avatar=msg.avatar,
            token=secrets.token_urlsafe(16),  # 128 bits
            spectator=spectator,
            order=self._join_counter,
            conn=conn,
        )
        self._members[member.id] = member
        conn.member_id = member.id
        if not spectator and (not self._host or self._host not in self._members):
            self._host = member.id
        self._empty_since = None
        self._disarm("idle")
        self._send(conn, pr.Welcome, player_id=member.id, token=member.token, spectator=spectator)
        conn.offer(self._snapshot(member))
        if spectator:
            self._patch(spectators=self._spectator_count())
        else:
            self._patch_players(member, spectators=self._spectator_count(), host=self._host)
        log.info("player_joined", room=self.code, spectator=spectator)

    def _on_rejoin(self, conn: Connection, msg: pr.Rejoin) -> None:
        member = next(
            (m for m in self._members.values() if secrets.compare_digest(m.token, msg.token)),
            None,
        )
        if member is None:
            self._error(conn, "bad_token", "Session expirée")
            conn.close(4401, "bad_token")
            return
        old = member.conn
        if old is not None and old is not conn:
            self._error(old, "replaced", "Connexion remplacée")
            old.member_id = None
            old.close(4000, "replaced")
        member.conn = conn
        conn.member_id = member.id
        self._disarm(f"grace:{member.id}")
        self._empty_since = None
        self._disarm("idle")
        metrics.RECONNECTIONS.inc()
        self._send(conn, pr.Welcome, player_id=member.id, token=member.token, spectator=member.spectator)
        conn.offer(self._snapshot(member))
        if not member.spectator:
            self._patch_players(member)

    def _on_disconnect(self, conn: Connection) -> None:
        member = self._members.get(conn.member_id or "")
        conn.closed = True
        if member is None or member.conn is not conn:
            return
        member.conn = None
        if member.spectator:
            self._remove_member(member)
            return
        self._patch_players(member)
        self._arm(f"grace:{member.id}", self._cfg.grace_seconds)
        self._check_empty()

    def _on_grace_expired(self, member_id: str) -> None:
        member = self._members.get(member_id)
        if member is not None and member.conn is None:
            log.info("grace_expired", room=self.code)
            self._remove_member(member)

    def _remove_member(self, member: Member, notify_conn: bool = False) -> None:
        if member.id not in self._members:
            return
        conn = member.conn
        if conn is not None:
            conn.member_id = None
            if notify_conn:
                conn.close(1000, "left")
        self._disarm(f"grace:{member.id}")
        events: list[GameEvent] = []
        if self._engine is not None and self._phase == "playing" and not member.spectator:
            events = self._engine.leave(member.id, at=self.clock.now())
        del self._members[member.id]
        extra: dict[str, Any] = {}
        if member.id == self._host:
            self._host = self._pick_host()
            extra["host"] = self._host
        if member.spectator:
            self._patch(spectators=self._spectator_count())
        else:
            self._patch(players={member.id: None}, spectators=self._spectator_count(), **extra)
        if events:
            self._apply(events)
        if self._phase == "countdown" and self._connected_players() < 2:
            self._abort_countdown()
        self._check_empty()

    def _pick_host(self) -> str:
        players = self._players()
        connected = [m for m in players if m.conn is not None]
        pool = connected or players
        return pool[0].id if pool else ""

    def _connected_players(self) -> int:
        return sum(1 for m in self._members.values() if not m.spectator and m.conn is not None)

    def _check_empty(self) -> None:
        if not any(m.conn is not None for m in self._members.values()):
            if self._empty_since is None:
                self._empty_since = self.clock.now()
            self._arm("idle", self._cfg.room_idle_seconds)
        else:
            self._empty_since = None
            self._disarm("idle")

    def _on_idle(self) -> None:
        if any(m.conn is not None for m in self._members.values()):
            return
        log.info("room_idle_closed", room=self.code)
        for member in list(self._members.values()):
            if member.conn is not None:
                member.conn.close(1000, "idle")
        self._finalize()
        if self._task is not None and self._task is not asyncio.current_task():
            self._task.cancel()

    def _on_heartbeat(self) -> None:
        limit = self._cfg.heartbeat_seconds * ZOMBIE_FACTOR
        now = time.monotonic()
        for member in self._members.values():
            conn = member.conn
            if conn is not None and now - conn.last_seen > limit:
                log.info("zombie_connection", room=self.code)
                conn.close(1001, "heartbeat_timeout")
        self._arm("heartbeat", self._cfg.heartbeat_seconds)

    # ------------------------------------------------------------------ lobby actions

    def _on_ready(self, conn: Connection, member: Member, msg: pr.Ready) -> None:
        if member.spectator or self._phase != "lobby":
            self._error(conn, "wrong_phase")
            return
        member.ready = msg.ready
        self._patch_players(member)

    def _on_settings(self, conn: Connection, member: Member, msg: pr.SetSettings) -> None:
        if member.id != self._host:
            self._error(conn, "not_host")
            return
        if self._phase != "lobby":
            self._error(conn, "wrong_phase")
            return
        current = self._settings
        try:
            new = BombSettings(
                lives=current.lives if msg.lives is UNSET else msg.lives,
                fuse_seconds=current.fuse_seconds if msg.fuse_seconds is UNSET else msg.fuse_seconds,
                level=current.level if msg.level is UNSET else msg.level,
                max_players=current.max_players if msg.max_players is UNSET else msg.max_players,
                bonus_kana=current.bonus_kana if msg.bonus_kana is UNSET else msg.bonus_kana,
                tension=current.tension if msg.tension is UNSET else msg.tension,
            )
        except ValueError as exc:
            self._error(conn, "bad_message", str(exc))
            return
        if new.max_players > self._cfg.max_players_per_room or new.max_players < self.player_count():
            self._error(conn, "not_allowed", "max_players")
            return
        self._settings = new
        self._patch(settings=self._settings_view())

    def _on_kick(self, conn: Connection, member: Member, msg: pr.Kick) -> None:
        if member.id != self._host:
            self._error(conn, "not_host")
            return
        target = self._members.get(msg.player_id)
        if target is None or target.id == member.id:
            self._error(conn, "not_allowed")
            return
        if target.conn is not None:
            self._error(target.conn, "kicked", "Expulsé par l'hôte")
            target.conn.close(4403, "kicked")
        self._remove_member(target)

    def _on_chat(self, conn: Connection, member: Member, msg: pr.Chat) -> None:
        if self._phase == "playing" and not member.spectator:
            self._error(conn, "wrong_phase")
            return
        if not member.chat_bucket.allow():
            metrics.RATE_LIMITED.labels("chat").inc()
            self._error(conn, "rate_limited")
            return
        text = sanitize_chat(msg.text)
        if text is None:
            return
        self._emit(pr.ChatEvent, player_id=member.id, name=member.name, text=text)

    def _on_rematch(self, conn: Connection, member: Member) -> None:
        if member.id != self._host:
            self._error(conn, "not_host")
            return
        if self._phase != "finished":
            self._error(conn, "wrong_phase")
            return
        self._reset_to_lobby()

    def _reset_to_lobby(self) -> None:
        self._engine = None
        self._turn = None
        self._typing = ""
        self._results = None
        self._countdown_ends = None
        self._words.clear()
        self._phase = "lobby"
        self._disarm("turn")
        self._disarm("countdown")
        for m in self._members.values():
            m.ready = False
        self._patch_all_players(phase="lobby", countdown_ends=None)

    # ------------------------------------------------------------------ game flow

    def _on_start(self, conn: Connection, member: Member) -> None:
        if member.id != self._host:
            self._error(conn, "not_host")
            return
        if self._phase != "lobby":
            self._error(conn, "wrong_phase")
            return
        if self._connected_players() < 2:
            self._error(conn, "need_more_players", "Il faut au moins 2 joueurs")
            return
        if any(not m.ready for m in self._players() if m.id != self._host and m.conn is not None):
            self._error(conn, "players_not_ready", "Tout le monde doit être prêt")
            return
        self._phase = "countdown"
        ends = self.clock.now() + self._cfg.countdown_seconds
        self._countdown_ends = ends
        self._arm_at("countdown", ends)
        self._emit(pr.Countdown, ends_at=to_ms(ends))
        self._patch(phase="countdown", countdown_ends=to_ms(ends))

    def _abort_countdown(self) -> None:
        self._disarm("countdown")
        self._phase = "lobby"
        self._countdown_ends = None
        self._patch(phase="lobby", countdown_ends=None)

    def _on_countdown_done(self) -> None:
        if self._phase != "countdown":
            return
        players = [m for m in self._players() if m.conn is not None]
        # Players who dropped during the countdown simply do not play this game.
        for m in self._players():
            if m.conn is None:
                self._members.pop(m.id, None)
                self._disarm(f"grace:{m.id}")
                self._patch(players={m.id: None})
        if len(players) < 2:
            self._abort_countdown()
            return
        settings = self._settings
        engine = BombEngine(
            [PlayerInfo(m.id, m.name) for m in players],
            settings,
            validator=self._deps.dictionary,
            fragments=self._deps.tables[settings.level],
            clock=self.clock,
            rng=self._deps.rng_factory(),
        )
        self._engine = engine
        self._words.clear()
        self._results = None
        self._countdown_ends = None
        self._phase = "playing"
        self._patch_all_players(phase="playing", countdown_ends=None)
        self._apply(engine.start())

    def _on_turn_timeout(self, due: float) -> None:
        engine = self._engine
        if engine is None or self._phase != "playing":
            return
        self._apply(engine.timeout(at=max(due, engine.next_deadline or due), turn=engine.turn))

    def _on_typing(self, member: Member, msg: pr.Typing, at: float) -> None:
        engine = self._engine
        if engine is None or self._phase != "playing" or engine.current_player != member.id:
            return
        self._typing = msg.text
        if at - self._typing_sent_at >= TYPING_INTERVAL:
            self._flush_typing()
        else:
            self._arm_at("typing", self._typing_sent_at + TYPING_INTERVAL)

    def _flush_typing(self) -> None:
        engine = self._engine
        if engine is None or engine.current_player is None:
            return
        self._typing_sent_at = self.clock.now()
        self._emit_ephemeral(
            pr.TypingEvent, exclude=engine.current_player, player_id=engine.current_player, text=self._typing
        )

    def _on_submit(self, conn: Connection, member: Member, msg: pr.Submit, at: float) -> None:
        engine = self._engine
        if engine is None or self._phase != "playing" or member.spectator:
            self._error(conn, "wrong_phase")
            return
        self._apply(engine.submit(member.id, msg.text, at=at))

    # ------------------------------------------------------------------ engine events -> protocol

    def _apply(self, events: list[GameEvent]) -> None:
        for event in events:
            if isinstance(event, ev.TurnStarted):
                self._typing = ""
                self._turn = pr.TurnView(
                    turn=event.turn,
                    player_id=event.player_id,
                    fragment=event.fragment,
                    deadline=to_ms(event.deadline),
                    fuse_ms=to_ms(event.fuse_seconds),
                )
                self._arm_at("turn", event.deadline)
                self._emit(
                    pr.Turn,
                    turn=event.turn,
                    player_id=event.player_id,
                    fragment=event.fragment,
                    deadline=self._turn.deadline,
                    fuse_ms=self._turn.fuse_ms,
                )
            elif isinstance(event, ev.WordAccepted):
                self._words.append(
                    pr.WordView(
                        event.player_id,
                        event.word,
                        event.reading,
                        event.turn,
                        event.meaning_fr,
                        event.meaning_en,
                    )
                )
                del self._words[:-WORD_HISTORY]
                self._emit(
                    pr.Accepted,
                    turn=event.turn,
                    player_id=event.player_id,
                    word=event.word,
                    reading=event.reading,
                    score_gain=event.score_gain,
                    score=event.score,
                    meaning_fr=event.meaning_fr,
                    meaning_en=event.meaning_en,
                )
            elif isinstance(event, ev.WordRejected):
                member = self._members.get(event.player_id)
                if member is not None and member.conn is not None:
                    self._send(member.conn, pr.Rejected, reason=event.reason, text=event.text[:32])
            elif isinstance(event, ev.Explosion):
                metrics.EXPLOSIONS.inc()
                self._emit(pr.Explosion, turn=event.turn, player_id=event.player_id, lives=event.lives)
            elif isinstance(event, ev.PlayerEliminated):
                self._emit(pr.Elimination, player_id=event.player_id, place=event.place, reason=event.reason)
            elif isinstance(event, ev.LifeGained):
                self._emit(pr.LifeGained, player_id=event.player_id, lives=event.lives)
            elif isinstance(event, ev.BonusProgress):
                self._emit(pr.BonusProgress, player_id=event.player_id, remaining=list(event.remaining))
            elif isinstance(event, ev.GameOver):
                self._on_game_over(event)

    def _on_game_over(self, event: ev.GameOver) -> None:
        engine = self._engine
        assert engine is not None
        self._disarm("turn")
        self._disarm("typing")
        self._turn = None
        self._typing = ""
        self._phase = "finished"
        rows: list[pr.ResultRow] = []
        stats = {p.info.id: p for p in engine.players}
        for place, player_id in enumerate(event.ranking, start=1):
            state = stats[player_id]
            words = [h for h in engine.history if h.player_id == player_id]
            longest = max((h.word for h in words), key=len, default="")
            rows.append(pr.ResultRow(player_id, place, state.score, state.words, longest))
        self._results = rows
        metrics.GAMES_FINISHED.inc()
        self._emit(pr.GameOver, winner_id=event.winner_id, results=rows)
        self._patch(phase="finished")
        assert engine.phase is Phase.FINISHED
