from __future__ import annotations

import random

import pytest

from app.japanese.dictionary import Dictionary, WordMatch, WordRejected
from app.japanese.kanji import LEVELS, MIN_WORDS, KanjiBook


@pytest.fixture(scope="module")
def book(dictionary: Dictionary) -> KanjiBook:
    return KanjiBook.load(dictionary)


def accepted(book: KanjiBook, raw: str, char: str) -> bool:
    return isinstance(book.check(raw, char), WordMatch)


def test_the_levels_have_the_known_sizes(book: KanjiBook) -> None:
    # Waller's lists: 79, 166, 367, 367 and 1232 kanji (some may lack words and are never asked)
    sizes = {n: sum(1 for c in book.pool([n])) for n in LEVELS}
    assert 70 <= sizes[5] <= 79 and 150 <= sizes[4] <= 166 and 340 <= sizes[3] <= 367
    assert 320 <= sizes[2] <= 367 and 1000 <= sizes[1] <= 1232


def test_readings_and_levels_of_a_kanji(book: KanjiBook) -> None:
    tsuchi = book.get("土")
    assert tsuchi is not None and tsuchi.level == 5
    assert "ど" in tsuchi.on and "と" in tsuchi.on and "つち" in tsuchi.kun
    assert "terre" in tsuchi.meaning_fr
    # okurigana is not part of the reading of the kanji: 食べる -> た, 生まれる -> うま
    assert "た" in (book.get("食") or tsuchi).kun
    assert all("." not in r and "-" not in r for k in ("食", "生", "行") for r in book.get(k).kun)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("raw", "char"),
    [
        ("どようび", "土"),  # the example: the kanji of tsuchi is in doyoubi
        ("doyoubi", "土"),  # romaji
        ("ドヨウビ", "土"),  # katakana
        ("土曜日", "土"),  # typed in kanji
        ("つき", "月"),  # the moon: a reading alone, because a word exists for it
        ("げつようび", "月"),
        ("にほん", "日"),
        ("ようび", "日"),  # 曜日: the kanji is read び there
        ("ひ", "日"),
        ("がっこう", "学"),  # gemination of 学校
        ("せんせい", "生"),
        ("いきる", "生"),  # okurigana word
        ("たべる", "食"),
        ("ひとり", "人"),  # irregular reading of 一人 and 人
        ("にんげん", "人"),
        ("いっぷん", "分"),  # gemination
        ("ぶんぷ", "分"),
    ],
)
def test_words_written_with_the_kanji_are_accepted(book: KanjiBook, raw: str, char: str) -> None:
    assert accepted(book, raw, char), (raw, char)


@pytest.mark.parametrize(
    ("raw", "char", "reason"),
    [
        ("がっこう", "土", "missing_fragment"),  # a word, but not written with the kanji
        ("ねこ", "月", "missing_fragment"),
        ("ひがし", "日", "missing_fragment"),  # 東, not 日
        ("ぬぬぬぬぬ", "土", "not_in_dictionary"),
        ("", "土", "not_in_dictionary"),
        ("月曜日", "土", "missing_fragment"),  # kanji typed but another kanji
    ],
)
def test_other_words_are_refused_with_the_right_reason(
    book: KanjiBook, raw: str, char: str, reason: str
) -> None:
    result = book.check(raw, char)
    assert isinstance(result, WordRejected) and result.reason == reason, (raw, char, result)


def test_a_reading_that_is_not_a_word_is_refused(book: KanjiBook) -> None:
    # つち is a word (土), but a bare on reading without any word written with the kanji is not accepted
    assert accepted(book, "つち", "土")
    assert not accepted(book, "ぎょう", "土")


def test_every_kanji_asked_has_enough_words_and_the_draw_respects_levels(
    book: KanjiBook, dictionary: Dictionary
) -> None:
    rng = random.Random(1)
    for _ in range(300):
        char = book.draw([5, 4], rng)
        kanji = book.get(char)
        assert kanji is not None and kanji.level in (4, 5)
        assert book.word_count(char) >= MIN_WORDS
    recent = list(book.pool([5]))[:-3]
    assert book.draw([5], rng, recent) in book.pool([5])[-3:]
    with pytest.raises(ValueError):
        book.draw([], rng)


def test_every_asked_kanji_has_a_playable_word_for_the_bots(book: KanjiBook, dictionary: Dictionary) -> None:
    for char in book.pool(LEVELS):
        words = book.sample_words(char, 3)
        assert words, char
        assert accepted(book, words[0], char), (char, words[0])
