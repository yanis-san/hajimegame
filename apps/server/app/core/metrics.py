"""Prometheus metrics. One registry per process; tests read values through the helper functions."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REGISTRY = CollectorRegistry()

ROOMS_ACTIVE = Gauge("hajime_rooms_active", "Rooms currently alive on this instance", registry=REGISTRY)
PLAYERS_CONNECTED = Gauge("hajime_players_connected", "Connected websocket clients", registry=REGISTRY)
MESSAGE_LATENCY = Histogram(
    "hajime_message_processing_seconds",
    "Time between websocket receive and room processing completion",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.25, 1.0),
    registry=REGISTRY,
)
HANDLE_LATENCY = Histogram(
    "hajime_room_handle_seconds",
    "CPU time spent handling one command inside a room (excludes queue wait)",
    buckets=(0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1),
    registry=REGISTRY,
)
LOOP_LAG = Histogram(
    "hajime_event_loop_lag_seconds",
    "How late the event loop wakes a 10 ms timer (saturation indicator)",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY,
)
EXPLOSIONS = Counter("hajime_explosions_total", "Bomb explosions", registry=REGISTRY)
RECONNECTIONS = Counter("hajime_reconnections_total", "Successful rejoin after a drop", registry=REGISTRY)
INVALID_MESSAGES = Counter(
    "hajime_invalid_messages_total", "Messages rejected by validation", registry=REGISTRY
)
RATE_LIMITED = Counter(
    "hajime_rate_limited_total", "Requests refused by a rate limiter", ["kind"], registry=REGISTRY
)
EMAILS = Counter(
    "hajime_emails_total", "E-mails handed to the mail server", ["kind", "result"], registry=REGISTRY
)
GAMES_FINISHED = Counter("hajime_games_finished_total", "Completed games", registry=REGISTRY)
GAME_RECORDS = Counter(
    "hajime_game_records_total", "Finished games written to the database", ["result"], registry=REGISTRY
)
GAME_RECORDS_QUEUED = Gauge(
    "hajime_game_records_queued", "Finished games waiting to be written", registry=REGISTRY
)


def render() -> bytes:
    return generate_latest(REGISTRY)
