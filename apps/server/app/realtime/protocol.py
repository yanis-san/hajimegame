"""Wire protocol. Source of truth for docs/PROTOCOL.md and the generated TypeScript types.

Every message is a JSON object with a ``t`` tag and a protocol version ``v``.
Server events also carry ``seq``.
All times are milliseconds on the server monotonic clock (``server_time`` in ``pong`` and ``snapshot``).
"""

from __future__ import annotations

from typing import Annotated, Literal

import msgspec
from msgspec import UNSET, Meta, Struct, UnsetType

PROTOCOL_VERSION = 1

Mode = Literal["classic", "shiritori"]
RoomPhase = Literal["lobby", "countdown", "playing", "finished"]
RejectCode = Literal[
    "not_in_dictionary", "missing_fragment", "already_used", "not_your_turn", "too_late", "ends_with_n"
]
ErrorCode = Literal[
    "bad_version",
    "bad_message",
    "room_not_found",
    "room_full",
    "bad_token",
    "name_invalid",
    "rate_limited",
    "not_host",
    "not_allowed",
    "wrong_phase",
    "need_more_players",
    "players_not_ready",
    "kicked",
    "replaced",
    "server_restarting",
    "wrong_instance",
]

Code = Annotated[str, Meta(min_length=4, max_length=8)]
Name = Annotated[str, Meta(min_length=1, max_length=40)]  # sanitized to 20 chars server side
Word = Annotated[str, Meta(max_length=32)]
ChatText = Annotated[str, Meta(min_length=1, max_length=200)]
Token = Annotated[str, Meta(min_length=16, max_length=64)]
PlayerId = Annotated[str, Meta(min_length=1, max_length=32)]
Avatar = Annotated[int, Meta(ge=0, le=11)]


class _Msg(Struct, frozen=True, forbid_unknown_fields=True, omit_defaults=True):
    pass


# ---------------------------------------------------------------- client -> server


class Join(_Msg, tag_field="t", tag="join"):
    room: Code
    name: Name
    avatar: Avatar = 0
    spectator: bool = False
    v: int = PROTOCOL_VERSION


class Rejoin(_Msg, tag_field="t", tag="rejoin"):
    room: Code
    token: Token
    v: int = PROTOCOL_VERSION


class Ready(_Msg, tag_field="t", tag="ready"):
    ready: bool
    v: int = PROTOCOL_VERSION


class Start(_Msg, tag_field="t", tag="start"):
    v: int = PROTOCOL_VERSION


class SetSettings(_Msg, tag_field="t", tag="settings"):
    lives: Annotated[int, Meta(ge=1, le=5)] | UnsetType = UNSET
    fuse_seconds: Annotated[float, Meta(ge=5, le=20)] | UnsetType = UNSET
    mode: Mode | UnsetType = UNSET
    max_players: Annotated[int, Meta(ge=2, le=8)] | UnsetType = UNSET
    n_penalty: bool | UnsetType = UNSET
    bonus_kana: bool | UnsetType = UNSET
    v: int = PROTOCOL_VERSION


class Typing(_Msg, tag_field="t", tag="typing"):
    text: Word
    v: int = PROTOCOL_VERSION


class Submit(_Msg, tag_field="t", tag="submit"):
    text: Word
    v: int = PROTOCOL_VERSION


class Ping(_Msg, tag_field="t", tag="ping"):
    n: int
    t0: float  # client time, echoed back untouched
    v: int = PROTOCOL_VERSION


class Kick(_Msg, tag_field="t", tag="kick"):
    player_id: PlayerId
    v: int = PROTOCOL_VERSION


class Chat(_Msg, tag_field="t", tag="chat"):
    text: ChatText
    v: int = PROTOCOL_VERSION


class Rematch(_Msg, tag_field="t", tag="rematch"):
    v: int = PROTOCOL_VERSION


class Leave(_Msg, tag_field="t", tag="leave"):
    v: int = PROTOCOL_VERSION


ClientMessage = (
    Join | Rejoin | Ready | Start | SetSettings | Typing | Submit | Ping | Kick | Chat | Rematch | Leave
)


# ---------------------------------------------------------------- shared views


class SettingsView(Struct, frozen=True, omit_defaults=False):
    lives: int
    fuse_seconds: float
    mode: Mode
    max_players: int
    bonus_kana: bool
    n_penalty: bool


class PlayerView(Struct, frozen=True, omit_defaults=False):
    id: str
    name: str
    avatar: int
    ready: bool
    connected: bool
    host: bool
    alive: bool
    lives: int
    score: int
    bonus: list[str] = []


class TurnView(Struct, frozen=True, omit_defaults=False):
    turn: int
    player_id: str
    fragment: str
    deadline: float
    fuse_ms: float


class WordView(Struct, frozen=True, omit_defaults=False):
    player_id: str
    word: str
    reading: str
    turn: int
    meaning_fr: str = ""
    meaning_en: str = ""


class ResultRow(Struct, frozen=True, omit_defaults=False):
    player_id: str
    place: int
    score: int
    words: int
    longest: str


# ---------------------------------------------------------------- server -> client


class _Event(Struct, frozen=True, omit_defaults=False):
    pass


class Welcome(_Event, tag_field="t", tag="welcome"):
    player_id: str
    token: str
    spectator: bool
    seq: int
    v: int = PROTOCOL_VERSION


class Snapshot(_Event, tag_field="t", tag="snapshot"):
    room: str
    phase: RoomPhase
    host: str
    you: str
    spectator: bool
    settings: SettingsView
    players: list[PlayerView]
    spectators: int
    turn: TurnView | None
    typing: str
    words: list[WordView]
    countdown_ends: float | None
    results: list[ResultRow] | None
    server_time: float
    seq: int
    v: int = PROTOCOL_VERSION


class Patch(_Event, tag_field="t", tag="patch"):
    """Partial lobby state. Absent fields are unchanged. A player mapped to null has been removed."""

    players: dict[str, PlayerView | None] | UnsetType = UNSET
    host: str | UnsetType = UNSET
    phase: RoomPhase | UnsetType = UNSET
    settings: SettingsView | UnsetType = UNSET
    spectators: int | UnsetType = UNSET
    countdown_ends: float | UnsetType | None = UNSET
    seq: int = 0
    v: int = PROTOCOL_VERSION


class Countdown(_Event, tag_field="t", tag="countdown"):
    ends_at: float
    seq: int
    v: int = PROTOCOL_VERSION


class Turn(_Event, tag_field="t", tag="turn"):
    turn: int
    player_id: str
    fragment: str
    deadline: float
    fuse_ms: float
    seq: int
    v: int = PROTOCOL_VERSION


class TypingEvent(_Event, tag_field="t", tag="typing"):
    player_id: str
    text: str
    seq: int
    v: int = PROTOCOL_VERSION


class Accepted(_Event, tag_field="t", tag="accepted"):
    turn: int
    player_id: str
    word: str
    reading: str
    score_gain: int
    score: int
    meaning_fr: str
    meaning_en: str
    seq: int
    v: int = PROTOCOL_VERSION


class Rejected(_Event, tag_field="t", tag="rejected"):
    reason: RejectCode
    text: str
    seq: int
    v: int = PROTOCOL_VERSION


class Explosion(_Event, tag_field="t", tag="explosion"):
    turn: int
    player_id: str
    lives: int
    cause: Literal["timeout", "n_ending"]
    seq: int
    v: int = PROTOCOL_VERSION


class Elimination(_Event, tag_field="t", tag="elimination"):
    player_id: str
    place: int
    reason: Literal["explosion", "left"]
    seq: int
    v: int = PROTOCOL_VERSION


class LifeGained(_Event, tag_field="t", tag="life"):
    player_id: str
    lives: int
    seq: int
    v: int = PROTOCOL_VERSION


class BonusProgress(_Event, tag_field="t", tag="bonus"):
    player_id: str
    remaining: list[str]
    seq: int
    v: int = PROTOCOL_VERSION


class GameOver(_Event, tag_field="t", tag="game_over"):
    winner_id: str | None
    results: list[ResultRow]
    seq: int
    v: int = PROTOCOL_VERSION


class ChatEvent(_Event, tag_field="t", tag="chat"):
    player_id: str
    name: str
    text: str
    seq: int
    v: int = PROTOCOL_VERSION


class Error(_Event, tag_field="t", tag="error"):
    code: ErrorCode
    message: str
    seq: int = 0
    v: int = PROTOCOL_VERSION


class Pong(_Event, tag_field="t", tag="pong"):
    n: int
    t0: float
    server_time: float
    seq: int = 0
    v: int = PROTOCOL_VERSION


ServerMessage = (
    Welcome
    | Snapshot
    | Patch
    | Countdown
    | Turn
    | TypingEvent
    | Accepted
    | Rejected
    | Explosion
    | Elimination
    | LifeGained
    | BonusProgress
    | GameOver
    | ChatEvent
    | Error
    | Pong
)

_client_decoder = msgspec.json.Decoder(ClientMessage)
_encoder = msgspec.json.Encoder()


class ProtocolError(Exception):
    """Raised when a frame is not a valid client message."""


def decode_client(raw: str | bytes) -> ClientMessage:
    try:
        message: ClientMessage = _client_decoder.decode(raw)
        return message
    except (msgspec.DecodeError, msgspec.ValidationError) as exc:
        raise ProtocolError(str(exc)) from exc


def encode(message: ServerMessage | ClientMessage) -> bytes:
    return _encoder.encode(message)
