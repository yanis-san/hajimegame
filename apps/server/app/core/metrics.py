"""Prometheus metrics. One registry per process; tests read values through the helper functions."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REGISTRY = CollectorRegistry()

ROOMS_ACTIVE = Gauge("hajime_rooms_active", "Rooms currently alive on this instance", registry=REGISTRY)
PLAYERS_CONNECTED = Gauge("hajime_players_connected", "Connected websocket clients", registry=REGISTRY)
MESSAGE_LATENCY = Histogram(
    "hajime_message_processing_seconds",
    "Time between websocket receive and room processing completion",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0),
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
GAMES_FINISHED = Counter("hajime_games_finished_total", "Completed games", registry=REGISTRY)


def render() -> bytes:
    return generate_latest(REGISTRY)
