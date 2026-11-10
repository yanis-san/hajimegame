from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.japanese.romaji import romaji_to_hiragana


@pytest.mark.parametrize(
    ("romaji", "kana"),
    [
        ("konnichiwa", "こんにちわ"),
        ("sushi", "すし"),
        ("susi", "すし"),
        ("tsunami", "つなみ"),
        ("tunami", "つなみ"),
        ("shashin", "しゃしん"),
        ("syasin", "しゃしん"),
        ("gakkou", "がっこう"),
        ("kitte", "きって"),
        ("matcha", "まっちゃ"),
        ("hon", "ほん"),
        ("honn", "ほん"),
        ("kan'i", "かんい"),
        ("kanni", "かんに"),
        ("kinyuu", "きにゅう"),
        ("ryokou", "りょこう"),
        ("jikan", "じかん"),
        ("zyunbi", "じゅんび"),
        ("fuji", "ふじ"),
        ("huji", "ふじ"),
        ("chizu", "ちず"),
        ("rāmen", "らあめん"),
        ("ra-men", "らーめん"),
        ("tōkyō", "とうきょう"),
        ("xtsu", "っ"),
        ("sekai", "せかい"),
        ("nippon", "にっぽん"),
        ("ONSEN", "おんせん"),
        ("anna", "あんな"),
        ("denwa", "でんわ"),
    ],
)
def test_conversions(romaji: str, kana: str) -> None:
    assert romaji_to_hiragana(romaji) == kana


def test_unknown_characters_are_kept() -> None:
    assert romaji_to_hiragana("q") == "q"
    assert romaji_to_hiragana("") == ""


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz'-", max_size=30))
def test_never_crashes_and_is_deterministic(text: str) -> None:
    assert romaji_to_hiragana(text) == romaji_to_hiragana(text)


@given(
    st.lists(
        st.sampled_from(["ka", "ki", "su", "shi", "tsu", "na", "ho", "myo", "ryu", "pa", "ba"]),
        min_size=1,
        max_size=10,
    )
)
def test_syllable_concatenation_leaves_no_latin(parts: list[str]) -> None:
    result = romaji_to_hiragana("".join(parts))
    assert not any(c.isascii() for c in result)
