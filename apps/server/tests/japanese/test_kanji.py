from __future__ import annotations

import random

import pytest

from app.japanese.dictionary import Dictionary, WordMatch, WordRejected
from app.japanese.kanji import LEVELS, MIN_WORDS, KanjiBook, shared_book


@pytest.fixture(scope="module")
def book(dictionary: Dictionary) -> KanjiBook:
    return shared_book(dictionary)


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
        ("ひがし", "土", "missing_fragment"),  # 東, not 土
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


def test_every_chosen_level_is_asked_in_proportion_not_in_proportion_to_its_size(book: KanjiBook) -> None:
    rng = random.Random(4)
    counts = {level: 0 for level in LEVELS}
    for _ in range(3000):
        counts[book.get(book.draw(LEVELS, rng)).level] += 1  # type: ignore[union-attr]
    # N1 has 15 times more kanji than N5, but each level gets about a fifth of the turns
    assert all(450 <= c <= 750 for c in counts.values()), counts


def test_the_commonest_kanji_do_not_dominate_a_level(book: KanjiBook) -> None:
    rng = random.Random(8)
    seen = {book.draw([5, 4], rng) for _ in range(1500)}
    assert len(seen) >= 0.9 * len(book.pool([5, 4]))  # most of the kanji of the levels come up


@pytest.mark.parametrize(
    ("raw", "char"),
    [
        ("ueno", "上"),  # the district of Tokyo and the family name: a proper name, not in JMdict
        ("ueno", "野"),
        ("うえの", "野"),
        ("上野", "上"),
        ("tanaka", "田"),  # a family name
        ("tanaka", "中"),
        ("ikebukuro", "池"),  # a place
    ],
)
def test_proper_names_written_with_the_kanji_are_accepted(book: KanjiBook, raw: str, char: str) -> None:
    result = book.check(raw, char)
    assert isinstance(result, WordMatch), (raw, char, result)


def test_a_proper_name_is_shown_in_kanji_and_counts_once(book: KanjiBook) -> None:
    names = [m for m in book.matches("ueno", "野") if m.entry_id >= 1 << 30]
    assert len(names) == 1  # one name for one typed word: it cannot be played twice under two spellings
    assert names[0].text == "上野"  # the shortest form made of kanji only
    assert book.check("ueno", "上").text == "上野"  # type: ignore[union-attr]  # not 上の, which has a kana
    assert "nom" in names[0].meaning_fr.lower() and names[0].meaning_en.startswith("Proper name")
    assert book.matches("ueno", "野")[0].entry_id == names[0].entry_id  # always the same id


def test_a_name_without_the_kanji_is_refused_like_any_word(book: KanjiBook) -> None:
    result = book.check("ueno", "土")
    assert isinstance(result, WordRejected) and result.reason == "missing_fragment"
    assert book.check("ぬぬぬぬぬ", "土") == WordRejected("not_in_dictionary")


def test_proper_names_exist_only_in_the_kanji_game(dictionary: Dictionary) -> None:
    # the fragment game does not know 上野 (うえの): only the kanji game does
    assert dictionary.check("うえの", "うえ").__class__.__name__ == "WordRejected"
