from __future__ import annotations

import random
import sys
import time

from app.japanese.dictionary import Dictionary, WordMatch, WordRejected
from app.japanese.fragments import DEFAULT_MIN_WORDS, FragmentTable


def test_loads_a_real_dictionary(dictionary: Dictionary) -> None:
    assert len(dictionary) > 100_000
    assert "JMdict" in str(dictionary.meta["source"])


def test_kana_kanji_and_romaji_inputs(dictionary: Dictionary) -> None:
    for raw in ("がっこう", "ガッコウ", "学校", "gakkou", "ｶﾞｯｺｳ"):
        result = dictionary.check(raw, "こう")
        assert isinstance(result, WordMatch), raw
        assert "こう" in result.reading


def test_rejection_reasons(dictionary: Dictionary) -> None:
    assert dictionary.check("がっこう", "ぬ") == WordRejected("missing_fragment")
    assert dictionary.check("あいうえおかきくけこ", "あ") == WordRejected("not_in_dictionary")
    assert dictionary.check("", "あ") == WordRejected("not_in_dictionary")
    assert dictionary.check("あ" * 200, "あ") == WordRejected("not_in_dictionary")


def test_fragment_must_not_cut_small_kana(dictionary: Dictionary) -> None:
    assert isinstance(dictionary.check("しょくじ", "しょ"), WordMatch)
    assert dictionary.check("しょくじ", "し") == WordRejected("missing_fragment")


def test_single_kana_words_are_excluded(dictionary: Dictionary) -> None:
    assert dictionary.check("あ", "あ") == WordRejected("not_in_dictionary")
    assert all(len(r) >= 2 for e in (dictionary.entry(i) for i in range(len(dictionary))) for r in e.readings)


def test_matches_returns_each_homograph_once(dictionary: Dictionary) -> None:
    found = dictionary.matches("はし", "は")
    assert len(found) >= 2
    assert len({m.entry_id for m in found}) == len(found)


def test_validation_is_fast(dictionary: Dictionary) -> None:
    words = ["がっこう", "たべる", "gakkou", "学校", "ありません", "zzzz"]
    rounds = 2_000
    start = time.perf_counter()
    for _ in range(rounds):
        for word in words:
            dictionary.check(word, "こう")
    per_call_us = (time.perf_counter() - start) / (rounds * len(words)) * 1e6
    # Real cost is about 3 microseconds; coverage tracing inflates it, so the budget is 10x under coverage.
    budget = 500 if "coverage" in sys.modules else 50
    assert per_call_us < budget, f"{per_call_us:.1f} microseconds per validation"


def test_there_are_enough_fragments(dictionary: Dictionary) -> None:
    table = FragmentTable(dictionary.fragment_counts)
    assert len(table) >= 30
    assert {f.tier for f in table.fragments} == {0, 1, 2}
    assert all(f.words >= DEFAULT_MIN_WORDS for f in table.fragments)


def test_fragment_pick_is_deterministic_and_avoids_recent(dictionary: Dictionary) -> None:
    table = FragmentTable(dictionary.fragment_counts)
    assert table.pick(random.Random(7), 0) == table.pick(random.Random(7), 0)
    recent = [f.text for f in table.fragments if f.tier == 0][:-1]
    assert table.pick(random.Random(1), 0, recent).text not in recent


def test_every_fragment_has_a_real_answer(dictionary: Dictionary) -> None:
    table = FragmentTable(dictionary.fragment_counts)
    for fragment in table.fragments[:: max(1, len(table) // 60)]:
        assert dictionary.sample_words(fragment.text, 1), fragment.text


def test_words_carry_both_meanings_when_available(dictionary: Dictionary) -> None:
    result = dictionary.check("さくら", "さ")
    assert isinstance(result, WordMatch)
    assert result.meaning_en
    entries = [dictionary.entry(i) for i in range(len(dictionary))]
    english = [e for e in entries if e.meaning_en]
    french = [e for e in entries if e.meaning_fr]
    assert len(english) > 0.95 * len(entries)
    assert len(french) > 5_000  # JMdict has French for a minority of entries; the rest is English only
    both = [e for e in french if e.meaning_en]
    assert len(both) > 0.5 * len(french)  # most French entries also carry the English meaning


def test_shiritori_start_matching(dictionary: Dictionary) -> None:
    assert isinstance(dictionary.check("くるま", "く", starts_with=True), WordMatch)
    assert dictionary.check("くるま", "る", starts_with=True) == WordRejected("missing_fragment")
    assert dictionary.check("kuruma", "く", starts_with=True) != WordRejected("not_in_dictionary")
    assert dictionary.start_count("く") > 500


def test_words_can_carry_an_example_sentence(dictionary: Dictionary) -> None:
    entries = [dictionary.entry(i) for i in range(len(dictionary))]
    with_example = [e for e in entries if e.example[0]]
    assert len(with_example) > 20_000
    assert sum(1 for e in with_example if e.example[2]) > 3_000  # some have a French translation too
    assert all(
        len(e.example[0]) <= 45 and e.example[1] for e in with_example
    )  # fits a phone, always has English
    result = dictionary.check("うちゅう", "う")
    assert isinstance(result, WordMatch)
    assert "宇宙" in result.example_ja
    assert result.example_en
    assert result.example_fr


def test_a_word_without_example_has_empty_sentence_fields(dictionary: Dictionary) -> None:
    bare = next(
        e for e in (dictionary.entry(i) for i in range(len(dictionary))) if not e.example[0] and e.words
    )
    result = dictionary.check(bare.words[0], bare.readings[0][:1])
    assert isinstance(result, WordMatch)
    assert (result.example_ja, result.example_en, result.example_fr) == ("", "", "")


def test_words_whose_kanji_has_a_special_reading_are_playable_in_kana(dictionary: Dictionary) -> None:
    """JMdict tags the usual kana of 果物 (くだもの), 今日 (きょう), 大人 (おとな)... as `gikun`. Players type
    them in kana, and a shiritori word starting with く must be accepted (it was once refused as unknown)."""
    for kana, first in [
        ("くだもの", "く"),
        ("きょう", "き"),
        ("おとな", "お"),
        ("あした", "あ"),
        ("へた", "へ"),
    ]:
        found = dictionary.check(kana, first, starts_with=True)
        assert isinstance(found, WordMatch), f"{kana} was refused: {found}"
    assert isinstance(dictionary.check("くだもの", "だも"), WordMatch)  # classic mode too
    assert isinstance(dictionary.check("果物", "く", starts_with=True), WordMatch)  # and typed in kanji


def test_a_word_typed_in_kana_keeps_the_reading_that_was_typed(dictionary: Dictionary) -> None:
    """毎年 is read まいとし or まいねん. Typing まいねん must count as ending in ん (the shiritori penalty
    and the next fragment depend on it), not as the first reading that happens to fit."""
    both = dictionary.check("まいねん", "ま", starts_with=True)
    assert isinstance(both, WordMatch) and both.reading == "まいねん"
    other = dictionary.check("まいとし", "ま", starts_with=True)
    assert isinstance(other, WordMatch) and other.reading == "まいとし"
    classic = dictionary.check("まいねん", "い")  # both readings contain い: the typed one wins
    assert isinstance(classic, WordMatch) and classic.reading == "まいねん"
    typed_in_kanji = dictionary.check("毎年", "ま", starts_with=True)
    assert (
        isinstance(typed_in_kanji, WordMatch) and typed_in_kanji.reading == "まいとし"
    )  # the first that fits


def test_a_katakana_word_is_shown_in_katakana(dictionary: Dictionary) -> None:
    # kana is compared as hiragana, but the lists show the word as the dictionary writes it
    assert dictionary.display_form("こーひー") == "コーヒー"
    assert dictionary.display_form("てれび") == "テレビ"
    # a word that is also written in hiragana, kanji, or is not in the dictionary stays as it is
    assert dictionary.display_form("ねこ") == "ねこ"
    assert dictionary.display_form("学校") == "学校"
    assert dictionary.display_form("ぬぬぬぬぬ") == "ぬぬぬぬぬ"
