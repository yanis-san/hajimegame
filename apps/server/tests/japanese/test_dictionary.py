from __future__ import annotations

import random
import time

import pytest

from app.japanese.dictionary import Dictionary, WordMatch, WordRejected
from app.japanese.fragments import FragmentTable, playable_table
from app.japanese.levels import LEVELS


def test_loads_a_real_dictionary(dictionary: Dictionary) -> None:
    assert len(dictionary) > 100_000
    assert "JMdict" in str(dictionary.meta["source"])


def test_kana_kanji_and_romaji_inputs(dictionary: Dictionary) -> None:
    for raw in ("がっこう", "ガッコウ", "学校", "gakkou", "ｶﾞｯｺｳ"):
        result = dictionary.check(raw, "こう", "n1")
        assert isinstance(result, WordMatch), raw
        assert "こう" in result.reading


def test_rejection_reasons(dictionary: Dictionary) -> None:
    assert dictionary.check("がっこう", "ぬ", "n1") == WordRejected("missing_fragment")
    assert dictionary.check("あいうえおかきくけこ", "あ", "n1") == WordRejected("not_in_dictionary")
    assert dictionary.check("", "あ", "n1") == WordRejected("not_in_dictionary")
    assert dictionary.check("あ" * 200, "あ", "n1") == WordRejected("not_in_dictionary")


def test_fragment_must_not_cut_small_kana(dictionary: Dictionary) -> None:
    assert isinstance(dictionary.check("しょくじ", "しょ", "n1"), WordMatch)
    assert dictionary.check("しょくじ", "し", "n1") == WordRejected("missing_fragment")


def test_level_filters_rare_words(dictionary: Dictionary) -> None:
    assert isinstance(dictionary.check("がっこう", "こう", "n5"), WordMatch)
    rare = next(
        e for e in (dictionary.entry(i) for i in range(len(dictionary) - 1, 0, -1)) if len(e.readings[0]) >= 4
    )
    reading = rare.readings[0]
    assert dictionary.check(reading, reading[:2], "n5") == WordRejected("not_in_dictionary")
    assert isinstance(dictionary.check(reading, reading[:2], "n1"), WordMatch)


def test_single_kana_words_are_excluded(dictionary: Dictionary) -> None:
    assert dictionary.check("あ", "あ", "n1") == WordRejected("not_in_dictionary")
    assert all(len(r) >= 2 for e in (dictionary.entry(i) for i in range(len(dictionary))) for r in e.readings)


def test_matches_returns_each_homograph_once(dictionary: Dictionary) -> None:
    found = dictionary.matches("はし", "は", "n1")
    assert len(found) >= 2
    assert len({m.entry_id for m in found}) == len(found)


def test_validation_is_fast(dictionary: Dictionary) -> None:
    words = ["がっこう", "たべる", "gakkou", "学校", "ありません", "zzzz"]
    rounds = 2_000
    start = time.perf_counter()
    for _ in range(rounds):
        for word in words:
            dictionary.check(word, "こう", "n1")
    per_call_us = (time.perf_counter() - start) / (rounds * len(words)) * 1e6
    assert per_call_us < 50, f"{per_call_us:.1f} microseconds per validation"


@pytest.mark.parametrize("level", LEVELS)
def test_every_level_has_enough_fragments(dictionary: Dictionary, level: str) -> None:
    table = playable_table(dictionary.fragment_buckets, level)
    assert len(table) >= 30
    assert {f.tier for f in table.fragments} == {0, 1, 2}
    assert all(f.words >= table.min_words for f in table.fragments)


def test_fragment_pick_is_deterministic_and_avoids_recent(dictionary: Dictionary) -> None:
    table = FragmentTable(dictionary.fragment_buckets, "n1")
    assert table.pick(random.Random(7), 0) == table.pick(random.Random(7), 0)
    recent = [f.text for f in table.fragments if f.tier == 0][:-1]
    assert table.pick(random.Random(1), 0, recent).text not in recent


@pytest.mark.parametrize("level", LEVELS)
def test_every_fragment_has_a_real_answer(dictionary: Dictionary, level: str) -> None:
    table = playable_table(dictionary.fragment_buckets, level)
    for fragment in table.fragments[:: max(1, len(table) // 60)]:
        assert dictionary.sample_words(fragment.text, level, 1), (level, fragment.text)
