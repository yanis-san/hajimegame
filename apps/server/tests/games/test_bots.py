from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

import pytest

from app.games.bomb.bots import DIFFICULTIES, LEVELS, MAX_THINK, Difficulty, plan_turn


@dataclass(frozen=True)
class Word:
    entry_id: int
    reading: str


class FakeSource:
    """500 words 'くNNN', commonest first, plus a few special ones."""

    def __init__(self) -> None:
        self.words = [
            Word(i, f"くあ{i:03d}".translate(str.maketrans("0123456789", "あいうえおかきくけこ")))
            for i in range(500)
        ]

    def candidates(self, fragment: str, starts_with: bool = False) -> list[Word]:
        return self.words


def plan(difficulty: Difficulty, seed: int, **kw: object) -> object:
    args: dict[str, object] = {
        "shiritori": False,
        "used": set(),
        "fuse_seconds": 10.0,
        "source": FakeSource(),
        "rng": random.Random(seed),
    }
    args.update(kw)
    return plan_turn(difficulty, "く", **args)  # type: ignore[arg-type]


def test_same_seed_same_plan() -> None:
    assert plan("normal", 3) == plan("normal", 3)


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_never_answers_in_the_last_part_of_the_fuse(difficulty: Difficulty) -> None:
    for seed in range(200):
        result = plan(difficulty, seed)
        assert result.delay <= 10.0 * MAX_THINK + 1e-9  # type: ignore[attr-defined]
        assert 0 < result.typing_at < result.delay  # type: ignore[attr-defined]


def test_harder_bots_are_faster_and_draw_fewer_blanks() -> None:
    delays: dict[str, float] = {}
    blanks: dict[str, float] = {}
    for difficulty in DIFFICULTIES:
        plans = [plan(difficulty, seed) for seed in range(600)]
        delays[difficulty] = statistics.mean(p.delay for p in plans)  # type: ignore[attr-defined]
        blanks[difficulty] = sum(p.word is None for p in plans) / len(plans)  # type: ignore[attr-defined]
    assert delays["easy"] > delays["normal"] > delays["hard"]
    assert blanks["easy"] > blanks["normal"] > blanks["hard"]
    for difficulty in DIFFICULTIES:  # within a few points of the configured rate
        assert abs(blanks[difficulty] - LEVELS[difficulty].blank) < 0.06


def test_vocabulary_grows_with_difficulty() -> None:
    seen: dict[str, set[str]] = {d: set() for d in DIFFICULTIES}
    for difficulty in DIFFICULTIES:
        for seed in range(2000):
            word = plan(difficulty, seed).word  # type: ignore[attr-defined]
            if word:
                seen[difficulty].add(word)
    assert len(seen["easy"]) <= LEVELS["easy"].vocabulary
    assert len(seen["easy"]) < len(seen["normal"]) < len(seen["hard"])


def test_bots_do_not_replay_used_words() -> None:
    source = FakeSource()
    used = {w.entry_id for w in source.words[:-3]}  # only 3 words left
    left = {w.reading for w in source.words[-3:]}
    for seed in range(100):
        word = plan("hard", seed, used=used).word  # type: ignore[attr-defined]
        assert word is None or word in left


def test_a_bot_with_nothing_to_say_draws_a_blank() -> None:
    source = FakeSource()
    everything = {w.entry_id for w in source.words}
    assert plan("hard", 1, used=everything).word is None  # type: ignore[attr-defined]


def test_shiritori_bots_never_end_a_word_with_n() -> None:
    class NSource:
        def candidates(self, fragment: str, starts_with: bool = False) -> list[Word]:
            return [Word(1, "くるん"), Word(2, "くるま"), Word(3, "くだん"), Word(4, "くつ")]

    for seed in range(200):
        word = plan("hard", seed, shiritori=True, source=NSource()).word  # type: ignore[attr-defined]
        assert word in {None, "くるま", "くつ"}


def test_one_kana_words_are_skipped() -> None:
    class Short:
        def candidates(self, fragment: str, starts_with: bool = False) -> list[Word]:
            return [Word(1, "く")]

    assert plan("hard", 1, source=Short()).word is None  # type: ignore[attr-defined]
