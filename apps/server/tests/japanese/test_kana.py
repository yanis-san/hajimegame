from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.japanese.kana import (
    contains_fragment,
    fragment_ngrams,
    is_hiragana,
    looks_like_romaji,
    normalize_text,
    shiritori_end,
    units,
)


def test_normalize_folds_katakana_width_and_spaces() -> None:
    assert normalize_text("ｶﾀｶﾅ") == "かたかな"
    assert normalize_text(" ラ ー メ ン　") == "らーめん"
    assert normalize_text("ＡＢＣ") == "ABC"


def test_normalize_keeps_kanji_and_long_mark() -> None:
    assert normalize_text("日本語") == "日本語"
    assert normalize_text("コーヒー") == "こーひー"


@given(st.text(max_size=40))
def test_normalize_is_idempotent(text: str) -> None:
    once = normalize_text(text)
    assert normalize_text(once) == once


@given(st.text(max_size=40))
def test_normalize_has_no_whitespace(text: str) -> None:
    assert not any(c.isspace() for c in normalize_text(text))


def test_units_attach_small_kana() -> None:
    assert units("しょくじ") == ["しょ", "く", "じ"]
    assert units("がっこう") == ["がっ", "こ", "う"]
    assert units("らーめん") == ["ら", "ー", "め", "ん"]
    assert units("っ") == ["っ"]


def test_fragment_never_cuts_small_kana() -> None:
    assert contains_fragment("しょくじ", "しょ")
    assert not contains_fragment("しょくじ", "し")
    assert contains_fragment("しじ", "し")
    assert not contains_fragment("きっと", "き")
    assert contains_fragment("きっと", "きっ")
    assert contains_fragment("ひしょし", "し")  # last し is a full unit
    assert not contains_fragment("あ", "")


def test_fragment_is_exact_kana_no_dakuten_folding() -> None:
    assert not contains_fragment("ばん", "はん")
    assert contains_fragment("ばん", "ばん")


def test_ngrams_skip_long_mark() -> None:
    grams = fragment_ngrams("らーめん")
    assert "らー" not in grams
    assert {"ら", "め", "ん", "めん"} <= grams


@given(st.text(alphabet="あいうえおかきくけこしょゃっ", min_size=1, max_size=12))
def test_every_ngram_is_found_in_reading(reading: str) -> None:
    for gram in fragment_ngrams(reading):
        assert contains_fragment(reading, gram)


def test_romaji_detection() -> None:
    assert looks_like_romaji("konnichiwa")
    assert not looks_like_romaji("こんにちは")
    assert not looks_like_romaji("")
    assert is_hiragana("らーめん")
    assert not is_hiragana("ラーメン")


def test_shiritori_end_kana() -> None:
    assert shiritori_end("くるま") == "ま"
    assert shiritori_end("ちきゅう") == "う"
    assert shiritori_end("ふらっしゅ") == "ゆ"  # small kana become full size
    assert shiritori_end("こーひー") == "い"  # ー repeats the vowel of the previous kana
    assert shiritori_end("ぎっ") == "ぎ"  # trailing っ is skipped
    assert shiritori_end("ほん") == "ん"
    assert shiritori_end("") == ""
