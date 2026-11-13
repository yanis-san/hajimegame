from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.api.games.bomb import build_view
from app.db.games.bomb import player_stats
from app.db.recorder import DatabaseRecorder
from app.games.bomb.recording import BombDetail, BombTurn
from app.games.recording import GameRecord, PlayerRecord
from app.japanese.dictionary import Dictionary

AYA = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
BEN = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
TODAY = date(2026, 11, 12)


def game(
    mode: str,
    ended: datetime,
    aya_words: list[tuple[str, int | None]],
    *,
    aya_place: int = 1,
    ben_words: tuple[str, ...] = (),
    bot: bool = True,
) -> GameRecord:
    """A two-human game (plus a CPU): Aya's turns come first, then Ben's, then the bomb wins one."""
    turns: list[BombTurn] = []
    for word, ms in aya_words:
        turns.append(BombTurn(len(turns) + 1, 0, "か", "word", word, word, ms, 10_000, 0))
    for word in ben_words:
        turns.append(BombTurn(len(turns) + 1, 1, "き", "word", word, word, 900, 10_000, 0))
    turns.append(BombTurn(len(turns) + 1, 1, "く", "explosion", "", "", None, 10_000, 0))
    players = [
        PlayerRecord(
            0,
            "Aya",
            AYA,
            "fr",
            False,
            None,
            aya_place,
            5,
            len(aya_words),
            max((w for w, _ in aya_words), key=len, default=""),
            0,
            800,
        ),
        PlayerRecord(1, "Ben", BEN, "ja", False, None, 3 - aya_place, 1, len(ben_words), "", 1, 900),
    ]
    if bot:
        players.append(PlayerRecord(2, "Momo", None, None, True, "hard", 3, 0, 4, "ねこ", 0, 100))
    return GameRecord(
        kind="bomb",
        id=uuid.uuid4(),
        room_code="ROOM01",
        mode=mode,
        settings={},
        started_at=ended - timedelta(minutes=2),
        ended_at=ended,
        duration_ms=120_000,
        players=tuple(players),
        detail=BombDetail(turns=tuple(turns)),
    )


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    recorder = DatabaseRecorder(engine)
    day = datetime(2026, 11, 12, 10, 0)
    for record in (
        game("classic", day - timedelta(days=3), [("さくら", 1000), ("ねこ", 2000)], ben_words=("きもの",)),
        game(
            "classic",
            day - timedelta(days=1),
            [("さくら", 1500), ("さくら", 500), ("ねこ", None)],
            aya_place=2,
        ),
        game("shiritori", day, [("さくら", 3000), ("らくだ", 1200)]),
        game("shiritori", day - timedelta(hours=5), [], bot=False),  # a game where Aya found nothing
    ):
        await recorder.save(record)
    yield engine
    await engine.dispose()


async def test_summary_counts_only_the_players_own_games_and_words(engine: AsyncEngine) -> None:
    stats = await player_stats(engine, [AYA], today=TODAY)
    s = stats.summary
    assert s.games == 4
    assert s.wins == 3  # place 1 in three of the four games
    assert s.words == 7  # her words only: not Ben's, not the CPU's
    assert s.distinct_words == 3  # さくら, ねこ, らくだ
    assert s.explosions == 0
    assert s.longest_word == "さくら" and s.fastest_ms == 500
    assert (
        s.avg_response_ms == 1533
    )  # (1000 + 2000 + 1500 + 500 + 3000 + 1200) / 6: the unmeasured one is ignored


async def test_most_used_words_come_first_with_their_counts(engine: AsyncEngine) -> None:
    stats = await player_stats(engine, [AYA], today=TODAY)
    assert [(w.word, w.count) for w in stats.top_words] == [("さくら", 4), ("ねこ", 2), ("らくだ", 1)]
    assert stats.top_words[0].last_played == TODAY  # played in today's shiritori game


async def test_the_latest_ten_words_newest_first(engine: AsyncEngine) -> None:
    stats = await player_stats(engine, [AYA], today=TODAY)
    assert [w.word for w in stats.recent_words[:2]] == [
        "らくだ",
        "さくら",
    ]  # today's game, its last word first
    assert len(stats.recent_words) == 7
    assert stats.recent_words[0].mode == "shiritori" and stats.recent_words[-1].mode == "classic"


async def test_the_mode_filter(engine: AsyncEngine) -> None:
    classic = await player_stats(engine, [AYA], "classic", today=TODAY)
    shiritori = await player_stats(engine, [AYA], "shiritori", today=TODAY)
    assert (classic.summary.games, classic.summary.words) == (2, 5)
    assert (shiritori.summary.games, shiritori.summary.words) == (2, 2)
    assert [w.word for w in shiritori.top_words] == ["さくら", "らくだ"]
    assert {r.mode for r in shiritori.recent_words} == {"shiritori"}


async def test_activity_is_games_per_day(engine: AsyncEngine) -> None:
    stats = await player_stats(engine, [AYA], today=TODAY)
    assert stats.activity == {date(2026, 11, 9): 1, date(2026, 11, 11): 1, date(2026, 11, 12): 2}


async def test_each_player_only_sees_their_own_data(engine: AsyncEngine) -> None:
    ben = await player_stats(engine, [BEN], today=TODAY)
    assert [w.word for w in ben.top_words] == ["きもの"]
    assert ben.summary.explosions == 4  # one per game he lost
    stranger = await player_stats(engine, [uuid.uuid4()], today=TODAY)
    assert (stranger.summary.games, stranger.summary.words, stranger.top_words, stranger.recent_words) == (
        0,
        0,
        [],
        [],
    )
    assert stranger.summary.avg_response_ms is None and stranger.summary.longest_word == ""


async def test_several_browsers_of_one_person_add_up(engine: AsyncEngine) -> None:
    both = await player_stats(engine, [AYA, BEN], today=TODAY)
    assert both.summary.games == 4  # the same games, counted once even though both seats are ours
    assert both.summary.words == 8


async def test_the_view_adds_meanings_and_fills_the_empty_days(
    engine: AsyncEngine, dictionary: Dictionary
) -> None:
    raw = await player_stats(engine, [AYA], today=TODAY)
    view = build_view(raw, "all", dictionary, TODAY)
    assert len(view.activity) == 30 and view.activity[-1].day == "2026-11-12" and view.activity[-1].games == 2
    assert sum(d.games for d in view.activity) == 4
    sakura = view.top_words[0]
    assert sakura.word == "さくら" and sakura.meaning_en  # known to the dictionary
    assert view.recent_words[0].word == "らくだ"


async def test_a_kanji_game_is_recorded_and_has_its_own_filter(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        await DatabaseRecorder(engine).save(
            game("kanji", datetime(2026, 11, 12, 10, 0), [("どようび", 1000), ("つき", 2500)])
        )
        kanji = await player_stats(engine, [AYA], "kanji", today=TODAY)
        assert (kanji.summary.games, kanji.summary.words) == (1, 2)
        assert {r.mode for r in kanji.recent_words} == {"kanji"}
        assert (await player_stats(engine, [AYA], "classic", today=TODAY)).summary.games == 0
    finally:
        await engine.dispose()
