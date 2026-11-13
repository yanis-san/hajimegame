from __future__ import annotations

import random
from typing import Any

import pytest

from app.games.base import GameEvent, ManualClock, Phase, PlayerInfo
from app.games.bomb import events as ev
from app.games.bomb.engine import BONUS_POOL, BombEngine
from app.games.bomb.settings import BombSettings
from tests.games.helpers import WORDS, FakeValidator, FixedFragments, TierRecorder, make_engine


def kinds(events: list[GameEvent]) -> list[str]:
    return [type(e).__name__ for e in events]


def test_start_emits_game_started_and_first_turn() -> None:
    engine, clock = make_engine()
    events = engine.start()
    assert kinds(events) == ["GameStarted", "TurnStarted"]
    turn = events[1]
    assert isinstance(turn, ev.TurnStarted)
    assert turn.deadline == clock.now() + 10.0
    assert turn.fragment == "く"
    assert engine.current_player == turn.player_id
    assert engine.next_deadline == turn.deadline


def test_cannot_start_twice() -> None:
    engine, _ = make_engine()
    engine.start()
    with pytest.raises(RuntimeError):
        engine.start()


def test_valid_word_passes_the_bomb_and_resets_deadline() -> None:
    engine, clock = make_engine()
    engine.start()
    first = engine.current_player
    assert first is not None
    clock.advance(4)
    events = engine.submit(first, "くるま")
    assert kinds(events) == ["WordAccepted", "TurnStarted"]
    accepted, turn = events
    assert isinstance(accepted, ev.WordAccepted) and isinstance(turn, ev.TurnStarted)
    assert (
        accepted.score_gain == 12
    )  # 10 + 2 for the medium fragment, answered in 40% of the fuse: normal speed
    assert turn.player_id != first
    assert turn.deadline == clock.now() + 10.0


def test_turn_order_is_seat_order() -> None:
    engine, _ = make_engine(3)
    engine.start()
    seen = [engine.current_player]
    for word in ("くるま", "くも", "いく"):
        player = engine.current_player
        assert player is not None
        engine.submit(player, word)
        seen.append(engine.current_player)
    order = [f"p{i}" for i in range(3)]
    start = order.index(seen[0] or "")
    assert seen == [order[(start + i) % 3] for i in range(4)]


@pytest.mark.parametrize(
    ("text", "reason"),
    [("ねこ", "missing_fragment"), ("zzz", "not_in_dictionary")],
)
def test_rejections_keep_the_turn(text: str, reason: str) -> None:
    engine, _ = make_engine()
    engine.start()
    player = engine.current_player
    assert player is not None
    deadline = engine.next_deadline
    events = engine.submit(player, text)
    assert len(events) == 1
    rejected = events[0]
    assert isinstance(rejected, ev.WordRejected)
    assert rejected.reason == reason
    assert engine.current_player == player
    assert engine.next_deadline == deadline


def test_already_used_word_is_rejected() -> None:
    engine, _ = make_engine()
    engine.start()
    a = engine.current_player
    assert a is not None
    engine.submit(a, "くるま")
    b = engine.current_player
    assert b is not None
    events = engine.submit(b, "くるま")
    assert isinstance(events[0], ev.WordRejected) and events[0].reason == "already_used"


def test_homographs_are_separate_words() -> None:
    engine, _ = make_engine(words={"はし": [(7, "はし"), (8, "はし")]})
    engine._fragments = FixedFragments("は")
    engine.start()
    p = engine.current_player
    assert p is not None
    assert isinstance(engine.submit(p, "はし")[0], ev.WordAccepted)
    q = engine.current_player
    assert q is not None
    assert isinstance(engine.submit(q, "はし")[0], ev.WordAccepted)
    r = engine.current_player
    assert r is not None
    third = engine.submit(r, "はし")
    assert isinstance(third[0], ev.WordRejected) and third[0].reason == "already_used"


def test_not_your_turn() -> None:
    engine, _ = make_engine()
    engine.start()
    other = next(p.info.id for p in engine.players if p.info.id != engine.current_player)
    events = engine.submit(other, "くるま")
    assert isinstance(events[0], ev.WordRejected) and events[0].reason == "not_your_turn"
    assert engine.submit("ghost", "くるま") == []


def test_deadline_tie_goes_to_the_player() -> None:
    engine, _ = make_engine()
    engine.start()
    player = engine.current_player
    assert player is not None
    deadline = engine.next_deadline
    assert deadline is not None
    assert isinstance(engine.submit(player, "くるま", at=deadline)[0], ev.WordAccepted)


def test_too_late_costs_a_life_and_moves_on() -> None:
    engine, _ = make_engine()
    engine.start()
    player = engine.current_player
    deadline = engine.next_deadline
    assert player is not None and deadline is not None
    events = engine.submit(player, "くるま", at=deadline + 0.001)
    assert kinds(events) == ["WordRejected", "Explosion", "TurnStarted"]
    assert isinstance(events[0], ev.WordRejected) and events[0].reason == "too_late"
    state = next(p for p in engine.players if p.info.id == player)
    assert state.lives == 2


def test_timeout_explodes_only_after_deadline_and_for_current_turn() -> None:
    engine, clock = make_engine()
    engine.start()
    assert engine.timeout() == []  # too early
    turn = engine.turn
    clock.advance(10)
    assert engine.timeout(turn=turn + 1) == []  # stale turn
    events = engine.timeout(turn=turn)
    assert kinds(events) == ["Explosion", "TurnStarted"]
    assert engine.timeout(turn=turn) == []  # already handled


def test_elimination_and_game_over_with_two_players() -> None:
    engine, clock = make_engine(2, BombSettings(lives=1))
    engine.start()
    loser = engine.current_player
    clock.advance(10)
    events = engine.timeout()
    assert kinds(events) == ["Explosion", "PlayerEliminated", "GameOver"]
    assert engine.phase is Phase.FINISHED
    over = events[-1]
    assert isinstance(over, ev.GameOver)
    assert over.winner_id != loser
    assert over.ranking == (over.winner_id, loser)
    assert engine.next_deadline is None
    assert engine.submit(over.winner_id or "", "くるま") == []
    assert engine.timeout() == []
    assert engine.leave(over.winner_id or "") == []


def test_eliminated_player_is_skipped() -> None:
    engine, clock = make_engine(3, BombSettings(lives=1))
    engine.start()
    first = engine.current_player
    clock.advance(10)
    engine.timeout()
    assert engine.current_player != first
    alive = engine.alive_ids()
    assert first not in alive and len(alive) == 2


def test_places_follow_elimination_order() -> None:
    engine, clock = make_engine(4, BombSettings(lives=1))
    engine.start()
    places = []
    while engine.phase is Phase.PLAYING:
        clock.advance(10)
        for event in engine.timeout():
            if isinstance(event, ev.PlayerEliminated):
                places.append(event.place)
    assert places == [4, 3, 2]


def test_leave_current_player_passes_the_bomb() -> None:
    engine, _ = make_engine(3)
    engine.start()
    leaver = engine.current_player
    assert leaver is not None
    events = engine.leave(leaver)
    assert kinds(events) == ["PlayerEliminated", "TurnStarted"]
    assert engine.current_player != leaver
    assert engine.leave(leaver) == []  # already gone


def test_leave_other_player_keeps_the_turn() -> None:
    engine, _ = make_engine(3)
    engine.start()
    current = engine.current_player
    other = next(i for i in engine.alive_ids() if i != current)
    events = engine.leave(other)
    assert kinds(events) == ["PlayerEliminated"]
    assert engine.current_player == current


def test_last_player_standing_wins_when_others_leave() -> None:
    engine, _ = make_engine(2)
    engine.start()
    leaver = engine.current_player or ""
    events = engine.leave(leaver)
    assert isinstance(events[-1], ev.GameOver)
    assert engine.winner is not None and engine.winner != leaver


def test_leave_unknown_player_is_noop() -> None:
    engine, _ = make_engine()
    engine.start()
    assert engine.leave("ghost") == []


def test_fast_answers_raise_the_difficulty_and_explosions_lower_it() -> None:
    picker = TierRecorder()
    engine, clock = make_engine(2, BombSettings(lives=5), fragments=picker)
    engine.start()
    first = engine.current_player or ""
    clock.advance(1)  # 10% of a 10 s fuse: fast
    engine.submit(first, "くるま")
    other = engine.current_player or ""
    clock.advance(1)
    engine.submit(other, "くも")
    # the first player is up again: their fast answer earned a harder fragment
    assert engine.current_player == first
    assert picker.tiers[-1] == 2
    clock.advance(10)
    engine.timeout()  # they let the bomb explode: next time an easy fragment
    engine.timeout(at=clock.now() + 10)
    assert next(p for p in engine.players if p.info.id == first).skill == 0
    assert 0 in picker.tiers[3:]


def test_slow_answers_lower_the_difficulty() -> None:
    picker = TierRecorder()
    engine, clock = make_engine(2, BombSettings(lives=5), fragments=picker)
    engine.start()
    player = engine.current_player or ""
    clock.advance(8)  # 80% of the fuse
    engine.submit(player, "くるま")
    assert next(p for p in engine.players if p.info.id == player).skill == 0


def shiritori() -> tuple[BombEngine, ManualClock]:
    return make_engine(2, BombSettings(lives=3, mode="shiritori"))


def test_shiritori_chain_follows_the_last_kana() -> None:
    engine, _ = shiritori()
    engine.start()
    assert engine.fragment == "く"  # opening kana
    a = engine.current_player or ""
    events = engine.submit(a, "くるま")
    assert isinstance(events[0], ev.WordAccepted)
    assert engine.fragment == "ま"  # くるま ends on ま
    b = engine.current_player or ""
    assert isinstance(engine.submit(b, "まくら")[0], ev.WordAccepted)
    assert engine.fragment == "ら"


def test_shiritori_word_must_start_with_the_kana() -> None:
    engine, _ = shiritori()
    engine.start()
    player = engine.current_player or ""
    events = engine.submit(player, "ねこ")  # real word, wrong start
    assert isinstance(events[0], ev.WordRejected) and events[0].reason == "missing_fragment"
    assert engine.current_player == player


def test_shiritori_word_ending_in_n_is_refused() -> None:
    engine, _ = shiritori()
    engine.start()
    engine.submit(engine.current_player or "", "くるま")
    engine.submit(engine.current_player or "", "まくら")
    player = engine.current_player or ""
    events = engine.submit(player, "らーめん")
    assert isinstance(events[0], ev.WordRejected) and events[0].reason == "ends_with_n"
    assert engine.current_player == player
    assert isinstance(engine.submit(player, "らくだ")[0], ev.WordAccepted)
    assert engine.fragment == "だ"


def test_shiritori_n_ending_can_cost_a_life_instead_of_being_refused() -> None:
    engine, _ = make_engine(2, BombSettings(lives=3, mode="shiritori", n_penalty=True))
    engine.start()
    player = engine.current_player or ""
    events = engine.submit(player, "くるん")
    assert kinds(events) == ["WordAccepted", "Explosion", "TurnStarted"]
    boom = events[1]
    assert isinstance(boom, ev.Explosion) and boom.cause == "n_ending" and boom.lives == 2
    assert engine.current_player != player
    assert engine.fragment != "ん"  # the chain restarts on a normal kana
    assert next(p for p in engine.players if p.info.id == player).score > 0


def test_shiritori_n_penalty_can_eliminate() -> None:
    engine, _ = make_engine(2, BombSettings(lives=1, mode="shiritori", n_penalty=True))
    engine.start()
    events = engine.submit(engine.current_player or "", "くるん")
    assert kinds(events) == ["WordAccepted", "Explosion", "PlayerEliminated", "GameOver"]


def test_shiritori_chain_survives_an_explosion() -> None:
    engine, clock = shiritori()
    engine.start()
    engine.submit(engine.current_player or "", "くるま")
    before = engine.fragment
    clock.advance(10)
    engine.timeout()
    assert engine.fragment == before  # the bomb passed on, the chain did not reset


def test_bonus_kana_grants_a_life_when_the_list_is_used() -> None:
    kana = BONUS_POOL[:3]
    words = {f"か{k}く": [(i, f"か{k}く")] for i, k in enumerate(kana)}
    engine, _ = make_engine(2, BombSettings(lives=2, bonus_kana=True), words=words)
    engine.start()
    player = engine.current_player or ""
    state = next(p for p in engine.players if p.info.id == player)
    state.bonus_left = set(kana)
    gained: list[GameEvent] = []
    for i, k in enumerate(kana):
        engine._fragments = FixedFragments("か")
        current = engine.current_player or ""
        if current != player:
            engine._current = player
        events = engine.submit(player, f"か{k}く")
        assert isinstance(events[0], ev.WordAccepted), (i, events)
        gained += events
    assert any(isinstance(e, ev.LifeGained) for e in gained)
    assert state.lives == 3
    assert len(state.bonus_left) == 3  # a fresh list


def test_bonus_life_is_capped() -> None:
    kana = BONUS_POOL[:3]
    words = {f"か{k}く": [(i, f"か{k}く")] for i, k in enumerate(kana)}
    engine, _ = make_engine(2, BombSettings(lives=5, bonus_kana=True), words=words)
    engine.start()
    player = engine.current_player or ""
    state = next(p for p in engine.players if p.info.id == player)
    state.bonus_left = {kana[0]}
    engine._fragments = FixedFragments("か")
    engine._fragment = "か"
    engine.submit(player, f"か{kana[0]}く")
    assert state.lives == 5


def test_same_seed_same_game() -> None:
    def play(seed: int) -> list[str]:
        engine, clock = make_engine(4, BombSettings(lives=2), seed=seed)
        log = [repr(e) for e in engine.start()]
        words = list(WORDS)
        while engine.phase is Phase.PLAYING:
            player = engine.current_player or ""
            if words and engine.turn % 2:
                log += [repr(e) for e in engine.submit(player, words.pop(0))]
            else:
                clock.advance(10)
                log += [repr(e) for e in engine.timeout()]
        return log

    assert play(5) == play(5)
    assert play(5) != play(6)


def _build(players: list[PlayerInfo]) -> BombEngine:
    return BombEngine(
        players,
        BombSettings(),
        validator=FakeValidator({}),
        fragments=FixedFragments(),
        clock=ManualClock(),
        rng=random.Random(0),
    )


def test_constructor_validation() -> None:
    with pytest.raises(ValueError):
        _build([PlayerInfo("a", "A")])
    with pytest.raises(ValueError):
        _build([PlayerInfo("a", "A"), PlayerInfo("a", "B")])
    with pytest.raises(ValueError):
        _build([PlayerInfo(str(i), "x") for i in range(9)])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lives": 0},
        {"lives": 6},
        {"fuse_seconds": 4.9},
        {"fuse_seconds": 20.1},
        {"max_players": 1},
        {"mode": "chess"},
    ],
)
def test_settings_bounds(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        BombSettings(**kwargs)


def test_manual_clock_cannot_go_backwards() -> None:
    clock = ManualClock(5)
    with pytest.raises(ValueError):
        clock.advance(-1)
    with pytest.raises(ValueError):
        clock.set(1)
    clock.set(7)
    assert clock.now() == 7


# --------------------------------------------------------------------------- points


def test_difficulty_and_a_little_length_make_the_base() -> None:
    from app.games.bomb.engine import word_points

    assert word_points(0, 0.5) == 10  # normal speed, easy prompt
    assert word_points(1, 0.5) == 12
    assert word_points(2, 0.5) == 14
    # length is a small part: nothing up to 4 kana, +1 from 5, +2 from 7 (never more)
    assert [word_points(0, 0.5, k) for k in (1, 4, 5, 6, 7, 12)] == [10, 10, 11, 11, 12, 12]
    assert word_points(0, 0.1, 7) == 18 and word_points(0, 0.9, 7) == 10  # the speed multiplies the whole


def test_a_very_quick_answer_earns_half_as_much_again_and_a_late_one_a_fifth_less() -> None:
    from app.games.bomb.engine import word_points

    assert [word_points(0, r) for r in (0.0, 0.25)] == [15, 15]  # within the first quarter of the fuse
    assert [word_points(0, r) for r in (0.26, 0.5, 0.7)] == [10, 10, 10]
    assert [word_points(0, r) for r in (0.71, 1.0)] == [8, 8]
    assert word_points(2, 0.1) == 21 and word_points(2, 0.9) == 11  # the hard prompt's base is 14


def play_for_points(delay: float, credit: float = 0.0, word: str = "くるま") -> int:
    engine, clock = make_engine()
    engine.start()
    player = engine.current_player
    assert player is not None
    clock.advance(delay)
    accepted = engine.submit(player, word, credit=credit)[0]
    assert isinstance(accepted, ev.WordAccepted)
    return accepted.score_gain


def test_the_speed_is_what_the_server_measured_with_the_round_trip_credited() -> None:
    # fuse 10 s, medium fragment (base 12): 2.4 s is the limit of the quick band (25%)
    assert play_for_points(2.0) == 18
    assert play_for_points(2.6) == 12  # a slow connection would have made this one normal...
    assert play_for_points(2.6, credit=0.2) == 18  # ...but its round trip of 0.2 s is credited
    assert play_for_points(8.0) == 10  # late: 12 * 0.8
    # the credit is capped: a connection cannot claim a huge latency to look faster
    assert play_for_points(2.9, credit=5.0) == 12  # only 0.25 s credited: 2.65 s is above the quick band
    assert play_for_points(2.9, credit=-1.0) == 12  # a negative credit is nothing


# --------------------------------------------------------------------------- timed games


def timed(duration: int = 120, n: int = 3) -> tuple[BombEngine, ManualClock]:
    return make_engine(n, settings=BombSettings(duration=duration))


def test_durations_are_checked() -> None:
    assert BombSettings(duration=300).duration == 300
    with pytest.raises(ValueError):
        BombSettings(duration=61)


def test_a_game_without_a_clock_has_no_end_time() -> None:
    engine, _ = make_engine()
    engine.start()
    assert engine.ends_at is None
    assert engine.time_up(at=10_000) == []


def test_the_clock_starts_with_the_game_and_cannot_end_it_early() -> None:
    engine, clock = timed(120)
    engine.start()
    assert engine.ends_at == clock.now() + 120
    assert engine.time_up(at=clock.now() + 119.9) == []
    assert engine.phase is Phase.PLAYING


def play_word(engine: BombEngine, clock: ManualClock, word: str, wait: float = 1.0) -> None:
    clock.advance(wait)
    player = engine.current_player
    assert player is not None
    assert any(isinstance(e, ev.WordAccepted) for e in engine.submit(player, word))


def test_when_the_clock_ends_the_best_score_wins() -> None:
    engine, clock = timed(120)
    engine.start()
    first = engine.current_player
    play_word(engine, clock, "くるま")  # first scores
    clock.set(engine.ends_at or 0)
    events = engine.time_up()
    over = events[-1]
    assert isinstance(over, ev.GameOver) and over.winner_id == first
    assert over.ranking[0] == first and set(over.ranking) == {"p0", "p1", "p2"}
    assert engine.phase is Phase.FINISHED


def test_an_explosion_costs_points_not_a_life_and_nobody_is_eliminated() -> None:
    engine, clock = timed(120, n=2)
    engine.start()
    first = engine.current_player
    play_word(engine, clock, "くるま")  # the first player scores
    score = next(p.score for p in engine.players if p.info.id == first)
    assert score > 0
    # the second one lets the bomb explode, then the first one too: points go down, lives stay
    for _ in range(3):
        clock.advance(11)
        events = engine.timeout()
        explosion = next(e for e in events if isinstance(e, ev.Explosion))
        assert explosion.lives == 3
        assert not any(isinstance(e, ev.PlayerEliminated) for e in events)
    assert engine.phase is Phase.PLAYING
    scores = {p.info.id: p.score for p in engine.players}
    assert min(scores.values()) == 0  # never negative
    assert all(p.lives == 3 and p.alive for p in engine.players)


def test_the_explosion_penalty_is_one_normal_word() -> None:
    from app.games.bomb.engine import EXPLOSION_PENALTY

    engine, clock = timed(300, n=2)
    engine.start()
    first = engine.current_player
    play_word(engine, clock, "くるま", wait=5)  # 12 points
    for _ in range(2):
        clock.advance(11)
        events = engine.timeout()
    explosion = next(e for e in events if isinstance(e, ev.Explosion))
    assert explosion.player_id == first and explosion.score == 12 - EXPLOSION_PENALTY


def test_a_word_that_arrives_after_the_clock_ends_the_game_instead() -> None:
    engine, clock = timed(120, n=2)
    engine.start()
    player = engine.current_player
    assert player is not None
    clock.set((engine.ends_at or 0) + 0.01)
    events = engine.submit(player, "くるま")
    assert [type(e).__name__ for e in events] == ["GameOver"]
    assert all(p.score == 0 for p in engine.players)  # the late word did not count


def test_a_bomb_that_goes_off_after_the_clock_ends_the_game_instead() -> None:
    engine, clock = timed(120, n=2)
    engine.start()
    clock.set((engine.ends_at or 0) + 0.01)
    assert [type(e).__name__ for e in engine.timeout()] == ["GameOver"]


def test_ties_are_broken_by_words_then_by_fewer_explosions() -> None:
    engine, _ = timed(300, n=2)
    engine.start()
    states = {p.info.id: p for p in engine.players}
    states["p0"].score = states["p1"].score = 20
    states["p0"].words, states["p1"].words = 2, 3
    assert engine.ranking()[0] == "p1"  # more words
    states["p0"].words = 3
    states["p0"].explosions, states["p1"].explosions = 2, 1
    assert engine.ranking()[0] == "p1"  # fewer explosions


def test_a_timed_game_ends_when_everybody_else_has_left() -> None:
    engine, _ = timed(120, n=2)
    engine.start()
    events = engine.leave("p1")
    assert isinstance(events[-1], ev.GameOver) and events[-1].winner_id == "p0"
