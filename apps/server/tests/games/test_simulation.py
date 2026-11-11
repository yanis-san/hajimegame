"""Mass simulation: random bots play thousands of games, invariants are checked after every action."""

from __future__ import annotations

import os
import random

import pytest

from app.games.base import GameEvent, ManualClock, Phase, PlayerInfo
from app.games.bomb import events as ev
from app.games.bomb.engine import BombEngine
from app.games.bomb.settings import LIFE_CAP, MODES, BombSettings
from app.japanese.dictionary import Dictionary
from app.japanese.fragments import FragmentTable, playable_table
from app.japanese.kana import fragment_ngrams, shiritori_end

GAMES = int(os.environ.get("HAJIME_SIM_GAMES", "1000"))


@pytest.fixture(scope="module")
def table(dictionary: Dictionary) -> FragmentTable:
    return playable_table(dictionary.fragment_buckets, "n1")


def check_invariants(engine: BombEngine, all_ids: set[str]) -> None:
    alive = engine.alive_ids()
    for state in engine.players:
        assert 0 <= state.lives <= LIFE_CAP
        assert 0 <= state.skill <= 2
        if state.alive:
            assert state.lives >= 1
    ids = [h.entry_id for h in engine.history]
    assert len(ids) == len(set(ids)), "a word was played twice"
    turns = [h.turn for h in engine.history]
    assert turns == sorted(turns)
    if engine.settings.mode == "shiritori":
        assert all(shiritori_end(word.reading) != "ん" for word in engine.history)
    if engine.phase is Phase.FINISHED:
        assert len(alive) <= 1
        assert engine.winner == (alive[0] if alive else None)
        assert set(engine.ranking()) == all_ids
        assert engine.next_deadline is None
    else:
        assert len(alive) >= 2
        assert engine.current_player in alive
        assert engine.next_deadline is not None


_CONTAINS: dict[str, list[str]] = {}
_STARTS: dict[str, list[str]] = {}


def build_index(dictionary: Dictionary) -> None:
    """One pass over the dictionary: fragment -> example readings, and first kana -> example readings."""
    for entry_id in range(len(dictionary)):
        for reading in dictionary.entry(entry_id).readings:
            for gram in fragment_ngrams(reading):
                bucket = _CONTAINS.setdefault(gram, [])
                if len(bucket) < 60:
                    bucket.append(reading)
            starts = _STARTS.setdefault(reading[0], [])
            if len(starts) < 60:
                starts.append(reading)


def candidates(dictionary: Dictionary, fragment: str, mode: str) -> list[str]:
    if not _CONTAINS:
        build_index(dictionary)
    return (_STARTS if mode == "shiritori" else _CONTAINS).get(fragment, [])


def play_one(seed: int, dictionary: Dictionary, table: FragmentTable) -> int:
    rng = random.Random(seed)
    settings = BombSettings(
        lives=rng.randint(1, 5),
        fuse_seconds=rng.choice([5.0, 10.0, 20.0]),
        mode=rng.choice(MODES),
        bonus_kana=rng.random() < 0.3,
    )
    count = rng.randint(2, 8)
    players = [PlayerInfo(f"p{i}", f"P{i}") for i in range(count)]
    clock = ManualClock()
    engine = BombEngine(
        players, settings, validator=dictionary, fragments=table, clock=clock, rng=random.Random(seed + 1)
    )
    ids = {p.id for p in players}
    events: list[GameEvent] = engine.start()
    check_invariants(engine, ids)
    actions = 0
    while engine.phase is Phase.PLAYING:
        actions += 1
        assert actions < 5_000, "game does not terminate"
        player = engine.current_player or ""
        deadline = engine.next_deadline or 0.0
        roll = rng.random()
        if roll < 0.02:
            events = engine.leave(rng.choice(engine.alive_ids()))
        elif roll < 0.55:
            words = candidates(dictionary, engine.fragment, settings.mode)
            clock.set(max(clock.now(), min(deadline, clock.now() + rng.random() * 3)))
            events = engine.submit(player, rng.choice(words)) if words else []
        elif roll < 0.65:
            events = engine.submit(player, rng.choice(["zzz", "あ", "", "漢字漢字漢字漢字"]))
        elif roll < 0.70:
            other = rng.choice(list(ids))
            events = engine.submit(other, "ありがとう", at=clock.now())
        else:
            clock.set(deadline)
            events = engine.timeout()
        check_invariants(engine, ids)
        for event in events:
            if isinstance(event, ev.TurnStarted):
                assert event.deadline >= clock.now()
                assert event.fragment
    return actions


def test_simulated_games_both_modes(dictionary: Dictionary, table: FragmentTable) -> None:
    total = sum(play_one(seed, dictionary, table) for seed in range(GAMES))
    assert total > GAMES  # every game took several actions
