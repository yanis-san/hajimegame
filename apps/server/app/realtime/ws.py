"""WebSocket endpoint: /ws/{code}.

The handler only parses, rate limits and forwards frames. All game decisions are made inside the Room.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket
from fastapi.responses import Response
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.core import metrics
from app.core.config import AppSettings
from app.core.logging import get_logger
from app.core.ratelimit import TokenBucket, WindowLimiter
from app.core.security import is_origin_allowed
from app.realtime import protocol as pr
from app.realtime.clock import to_ms
from app.realtime.connection import CloseRequest, Connection
from app.realtime.manager import RoomManager

if TYPE_CHECKING:
    from app.realtime.room import Room

log = get_logger("ws")
router = APIRouter()

MAX_FRAME = 2048
FIRST_MESSAGE_TIMEOUT = 15.0


def client_ip(websocket: WebSocket, settings: AppSettings) -> str:
    if settings.trust_proxy_headers:
        for header in ("fly-client-ip", "x-forwarded-for"):
            value = websocket.headers.get(header)
            if value:
                return value.split(",")[0].strip()
    return websocket.client.host if websocket.client else "unknown"


def _error_frame(code: pr.ErrorCode, message: str = "") -> str:
    return pr.encode(pr.Error(code=code, message=message or code)).decode()


async def _writer(websocket: WebSocket, conn: Connection) -> None:
    try:
        while True:
            item = await conn.queue.get()
            if isinstance(item, CloseRequest):
                with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                    await websocket.close(code=item.code, reason=item.reason)
                return
            await websocket.send_text(item)
    except (WebSocketDisconnect, RuntimeError):
        return


@router.websocket("/ws/{code}")
async def ws_endpoint(websocket: WebSocket, code: str) -> None:
    settings: AppSettings = websocket.app.state.settings
    manager: RoomManager = websocket.app.state.manager
    limiter: WindowLimiter = websocket.app.state.limiter
    ip = client_ip(websocket, settings)

    if not is_origin_allowed(websocket.headers.get("origin"), settings):
        await websocket.close(code=4403)
        return
    if not await limiter.allow(f"join:{ip}", settings.join_attempts_per_minute, 60):
        metrics.RATE_LIMITED.labels("join").inc()
        await websocket.close(code=4429)
        return

    resolved = await manager.resolve(code)
    if isinstance(resolved, str):
        # The room lives on another instance: Fly.io replays the request there via the fly-replay header.
        if "websocket.http.response" in websocket.scope.get("extensions", {}):
            await websocket.send_denial_response(
                Response(
                    status_code=409,
                    headers={"fly-replay": f"instance={resolved}", "x-hajime-owner": resolved},
                )
            )
            return
        await websocket.accept()
        await websocket.send_text(_error_frame("wrong_instance", resolved))
        await websocket.close(code=4301, reason=resolved)
        return

    await websocket.accept()
    if resolved is None:
        await websocket.send_text(_error_frame("room_not_found", "Partie introuvable"))
        await websocket.close(code=4404, reason="room_not_found")
        return

    room: Room = resolved
    conn = Connection(ip=ip, queue_size=settings.outbound_queue_size)
    writer = asyncio.get_running_loop().create_task(_writer(websocket, conn))
    bucket = TokenBucket(settings.messages_per_second, settings.message_burst)
    invalid = 0
    dropped = 0
    metrics.PLAYERS_CONNECTED.inc()
    try:
        first = True
        while websocket.application_state == WebSocketState.CONNECTED and not writer.done():
            try:
                frame = await asyncio.wait_for(
                    websocket.receive(), timeout=FIRST_MESSAGE_TIMEOUT if first else None
                )
            except TimeoutError:
                conn.close(4408, "join_timeout")
                break
            if frame["type"] == "websocket.disconnect":
                break
            raw = frame.get("text")
            if raw is None:
                raw = (frame.get("bytes") or b"").decode("utf-8", errors="replace")
            if len(raw) > MAX_FRAME:
                metrics.INVALID_MESSAGES.inc()
                conn.close(1009, "frame_too_large")
                break
            if not bucket.allow():
                metrics.RATE_LIMITED.labels("message").inc()
                dropped += 1
                if dropped == 1 or dropped % 50 == 0:
                    conn.offer(_error_frame("rate_limited"))
                if dropped > 500:
                    conn.close(4429, "rate_limited")
                    break
                continue
            dropped = 0
            try:
                msg = pr.decode_client(raw)
            except pr.ProtocolError:
                metrics.INVALID_MESSAGES.inc()
                invalid += 1
                conn.offer(_error_frame("bad_message", "Message invalide"))
                if invalid > settings.invalid_messages_before_kick:
                    conn.close(1008, "too_many_invalid_messages")
                    break
                continue
            if msg.v != pr.PROTOCOL_VERSION:
                conn.offer(_error_frame("bad_version", f"expected v{pr.PROTOCOL_VERSION}"))
                continue
            if isinstance(msg, pr.Ping):
                # Answered immediately, outside the room queue, so latency estimates stay clean.
                conn.last_seen = asyncio.get_running_loop().time()
                conn.offer(
                    pr.encode(pr.Pong(n=msg.n, t0=msg.t0, server_time=to_ms(room.clock.now()))).decode()
                )
                continue
            if isinstance(msg, pr.Join | pr.Rejoin) and msg.room.upper() != room.code:
                conn.offer(_error_frame("room_not_found"))
                continue
            first = False
            if room.closed:
                conn.offer(_error_frame("room_not_found", "Partie terminée"))
                conn.close(4404, "room_closed")
                break
            room.message(conn, msg)
    except WebSocketDisconnect:
        pass
    finally:
        metrics.PLAYERS_CONNECTED.dec()
        room.disconnected(conn)
        if conn.closed and not writer.done():
            # We asked to close (kick, rate limit, ...): let the writer flush the close frame first.
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(asyncio.shield(writer), timeout=2.0)
        conn.closed = True
        writer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writer
        if websocket.application_state != WebSocketState.DISCONNECTED:
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await websocket.close()
