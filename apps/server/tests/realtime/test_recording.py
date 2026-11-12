from __future__ import annotations

import uuid
from datetime import datetime

from app.games.bomb import events as ev
from app.realtime.recording import GameRecording, NullRecorder, SeatInfo

START = datetime(2026, 11, 12, 10, 0, 0)
GUEST = uuid.UUID("11111111-2222-3333-4444-555555555555")


def recording() -> GameRecording:
    seats = [
        SeatInfo("a", "Aya", guest_id=GUEST, lang="fr"),
        SeatInfo("b", "Ben", lang="en"),
        SeatInfo("c", "Momo", bot_difficulty="hard"),
    ]
    return GameRecording("ABC234", "classic", {"lives": 2}, seats, started_at=START, started=100.0)


def turn(turn_number: int, member: str, fragment: str, started: float, fuse: float = 10.0) -> ev.TurnStarted:
    return ev.TurnStarted(
        turn=turn_number, player_id=member, fragment=fragment, deadline=started + fuse, fuse_seconds=fuse
    )


def test_a_game_becomes_one_record_with_every_turn() -> None:
    r = recording()
    r.on_event(turn(1, "a", "しょ", 100.0), 100.0)
    r.on_event(ev.WordRejected(turn=1, player_id="a", text="zzz", reason="not_in_dictionary"), 101.0)
    r.on_event(ev.WordRejected(turn=1, player_id="a", text="yyy", reason="missing_fragment"), 101.5)
    r.on_event(
        ev.WordAccepted(turn=1, player_id="a", word="しょくじ", reading="しょくじ", score_gain=3, score=3),
        102.5,
    )
    r.on_event(turn(2, "b", "く", 102.5), 102.5)
    r.on_event(ev.Explosion(turn=2, player_id="b", lives=1), 112.5)
    r.on_event(turn(3, "c", "ん", 112.5), 112.5)
    r.on_event(ev.Explosion(turn=3, player_id="c", lives=1, cause="n_ending"), 113.0)

    record = r.finish(
        {"a": (1, 3, 1, "しょくじ"), "b": (2, 0, 0, ""), "c": (3, 0, 0, "")},
        ended_at=datetime(2026, 11, 12, 10, 1, 0),
        now=160.0,
    )

    assert (record.room_code, record.mode, record.settings) == ("ABC234", "classic", {"lives": 2})
    assert record.started_at == START
    assert record.duration_ms == 60_000
    assert [(t.turn, t.seat, t.fragment, t.outcome) for t in record.turns] == [
        (1, 0, "しょ", "word"),
        (2, 1, "く", "explosion"),
        (3, 2, "ん", "n_ending"),
    ]
    first = record.turns[0]
    assert (first.word, first.reading, first.response_ms, first.rejected_attempts) == (
        "しょくじ",
        "しょくじ",
        2500,
        2,
    )
    assert first.fuse_ms == 10_000
    assert record.turns[1].response_ms is None and record.turns[1].word == ""


def test_players_carry_their_stats_and_identity() -> None:
    r = recording()
    r.on_event(turn(1, "a", "か", 100.0), 100.0)
    r.on_event(
        ev.WordAccepted(turn=1, player_id="a", word="かさ", reading="かさ", score_gain=2, score=2), 101.0
    )
    r.on_event(turn(2, "a", "き", 101.0), 101.0)
    r.on_event(
        ev.WordAccepted(turn=2, player_id="a", word="きもの", reading="きもの", score_gain=3, score=5), 104.0
    )
    r.on_event(turn(3, "b", "さ", 104.0), 104.0)
    r.on_event(ev.Explosion(turn=3, player_id="b", lives=0), 114.0)

    record = r.finish(
        {"a": (1, 5, 2, "きもの"), "b": (2, 0, 0, ""), "c": (3, 0, 0, "")},
        ended_at=datetime(2026, 11, 12, 10, 1, 0),
        now=120.0,
    )
    aya, ben, momo = record.players
    assert (aya.seat, aya.name, aya.guest_id, aya.lang, aya.is_bot) == (0, "Aya", GUEST, "fr", False)
    assert (aya.place, aya.score, aya.words, aya.longest_word) == (1, 5, 2, "きもの")
    assert aya.avg_response_ms == 2000  # (1000 + 3000) / 2
    assert (ben.explosions, ben.avg_response_ms, ben.guest_id) == (1, None, None)
    assert (momo.is_bot, momo.bot_difficulty, momo.lang) == (True, "hard", None)


def test_events_of_another_turn_are_ignored_and_a_missing_result_gets_last_place() -> None:
    r = recording()
    r.on_event(turn(1, "a", "か", 100.0), 100.0)
    r.on_event(ev.WordRejected(turn=9, player_id="a", text="x", reason="too_late"), 101.0)  # stale turn
    record = r.finish({}, ended_at=datetime(2026, 11, 12, 10, 1, 0), now=101.0)
    assert record.turns == ()  # a turn that never ended is not invented
    assert [p.place for p in record.players] == [3, 3, 3]


def test_the_null_recorder_accepts_anything() -> None:
    record = recording().finish({}, ended_at=START, now=100.0)
    NullRecorder().submit(record)
