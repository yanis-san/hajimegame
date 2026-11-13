from __future__ import annotations

import random
from collections.abc import Sequence

import pytest

from app.games.base import ManualClock, PlayerInfo
from app.games.bomb import events as ev
from app.games.bomb.bots import plan_turn
from app.games.bomb.engine import BombEngine
from app.games.bomb.ports import WordHit
from app.games.bomb.settings import BombSettings
from app.japanese.dictionary import Dictionary, Reject, WordMatch
from app.japanese.fragments import FragmentTable
from app.japanese.kanji import KanjiBook


@pytest.fixture(scope="module")
def book(dictionary: Dictionary) -> KanjiBook:
    return KanjiBook.load(dictionary)


def make(
    dictionary: Dictionary, book: KanjiBook, levels: tuple[int, ...] = (5,), seed: int = 3
) -> tuple[BombEngine, ManualClock]:
    clock = ManualClock(100.0)
    engine = BombEngine(
        [PlayerInfo("a", "A"), PlayerInfo("b", "B")],
        BombSettings(mode="kanji", levels=levels),
        validator=dictionary,
        fragments=FragmentTable(dictionary.fragment_counts, 80),
        clock=clock,
        rng=random.Random(seed),
        kanji=book,
    )
    return engine, clock


def test_the_kanji_mode_needs_a_kanji_source(dictionary: Dictionary) -> None:
    with pytest.raises(ValueError):
        BombEngine(
            [PlayerInfo("a", "A"), PlayerInfo("b", "B")],
            BombSettings(mode="kanji"),
            validator=dictionary,
            fragments=FragmentTable(dictionary.fragment_counts, 80),
            clock=ManualClock(0.0),
            rng=random.Random(1),
        )


def test_levels_are_checked() -> None:
    with pytest.raises(ValueError):
        BombSettings(mode="kanji", levels=())
    with pytest.raises(ValueError):
        BombSettings(mode="kanji", levels=(6,))
    assert BombSettings(mode="kanji", levels=(1, 2, 3, 4, 5)).levels == (1, 2, 3, 4, 5)


def test_every_turn_asks_a_kanji_of_the_chosen_levels(dictionary: Dictionary, book: KanjiBook) -> None:
    engine, _ = make(dictionary, book, levels=(5,))
    events = engine.start()
    asked = []
    turn = next(e for e in events if isinstance(e, ev.TurnStarted))
    for _ in range(12):
        asked.append(turn.fragment)
        kanji = book.get(turn.fragment)
        assert kanji is not None and kanji.level == 5
        out = engine.timeout(at=turn.deadline)  # nobody answers: the next kanji comes with the next player
        nxt = [e for e in out if isinstance(e, ev.TurnStarted)]
        if not nxt:
            break
        turn = nxt[0]
    assert len(set(asked)) > 3  # not always the same kanji


def test_a_word_written_with_the_kanji_passes_the_bomb(dictionary: Dictionary, book: KanjiBook) -> None:
    engine, _ = make(dictionary, book, levels=(5, 4, 3, 2, 1))
    turn = next(e for e in engine.start() if isinstance(e, ev.TurnStarted))
    word = book.sample_words(turn.fragment, 1)[0]
    out = engine.submit(turn.player_id, word)
    accepted = [e for e in out if isinstance(e, ev.WordAccepted)]
    assert accepted, (turn.fragment, word, out)
    # the same word cannot be played twice
    assert engine.current_player != turn.player_id


def test_a_word_without_the_kanji_is_refused_and_the_turn_goes_on(
    dictionary: Dictionary, book: KanjiBook
) -> None:
    engine, _ = make(dictionary, book, levels=(5,))
    turn = next(e for e in engine.start() if isinstance(e, ev.TurnStarted))
    other = next(
        c
        for c in book.pool([5])
        if c != turn.fragment
        and not isinstance(book.check(book.sample_words(c, 1)[0], turn.fragment), WordMatch)
    )
    out = engine.submit(turn.player_id, book.sample_words(other, 1)[0])
    assert len(out) == 1 and isinstance(out[0], ev.WordRejected)
    assert out[0].reason == "missing_fragment"
    assert engine.current_player == turn.player_id
    out = engine.submit(turn.player_id, "ぬぬぬぬぬ")
    assert isinstance(out[0], ev.WordRejected) and out[0].reason == "not_in_dictionary"


class SameKanji:
    """The kanji source of the real book, but always asking the same kanji."""

    def __init__(self, book: KanjiBook, char: str) -> None:
        self._book, self._char = book, char

    def draw(self, levels: Sequence[int], rng: random.Random, recent: Sequence[str] = ()) -> str:
        return self._char

    def matches(self, text: str, char: str) -> Sequence[WordHit]:
        return self._book.matches(text, char)

    def reject_reason(self, text: str, char: str) -> Reject:
        return self._book.reject_reason(text, char)

    def difficulty(self, char: str) -> int:
        return self._book.difficulty(char)


def test_a_word_already_played_is_refused(dictionary: Dictionary, book: KanjiBook) -> None:
    engine = BombEngine(
        [PlayerInfo("a", "A"), PlayerInfo("b", "B")],
        BombSettings(mode="kanji"),
        validator=dictionary,
        fragments=FragmentTable(dictionary.fragment_counts, 80),
        clock=ManualClock(100.0),
        rng=random.Random(5),
        kanji=SameKanji(book, "日"),
    )
    first = next(e for e in engine.start() if isinstance(e, ev.TurnStarted))
    word = "にほん"
    assert any(isinstance(e, ev.WordAccepted) for e in engine.submit(first.player_id, word))
    again = engine.submit(engine.current_player or "", word)
    assert isinstance(again[0], ev.WordRejected) and again[0].reason == "already_used"
    # a homophone written with the kanji is the same entry only when it is: 二本 is another word
    assert any(isinstance(e, ev.WordAccepted) for e in engine.submit(engine.current_player or "", "ひ"))


def test_a_cpu_can_play_every_kanji(book: KanjiBook) -> None:
    rng = random.Random(2)
    for char in book.pool([5, 4]):
        plan = plan_turn(
            "hard", char, shiritori=False, used=frozenset(), fuse_seconds=10.0, source=book, rng=rng
        )
        if plan.word is not None:
            assert isinstance(book.check(plan.word, char), WordMatch), (char, plan.word)
