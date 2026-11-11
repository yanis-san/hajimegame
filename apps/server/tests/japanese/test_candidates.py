from __future__ import annotations

from app.japanese.candidates import PER_KEY, CandidateIndex
from app.japanese.dictionary import Dictionary
from app.japanese.kana import contains_fragment


def test_candidates_contain_the_fragment_and_are_commonest_first(
    dictionary: Dictionary, candidate_index: CandidateIndex
) -> None:
    found = candidate_index.candidates("しょ")
    assert 50 < len(found) <= PER_KEY
    assert all(contains_fragment(c.reading, "しょ") for c in found)
    ids = [c.entry_id for c in found]
    assert ids == sorted(ids)  # the dictionary is sorted by frequency
    ranks = [dictionary.entry(i).rank for i in ids]
    assert ranks == sorted(ranks)


def test_shiritori_candidates_start_with_the_kana(candidate_index: CandidateIndex) -> None:
    found = candidate_index.candidates("さ", starts_with=True)
    assert len(found) > 50
    assert all(c.reading[0] == "さ" for c in found)


def test_unknown_fragment_has_no_candidates(candidate_index: CandidateIndex) -> None:
    assert candidate_index.candidates("ぬぬぬ") == []


def test_every_candidate_is_accepted_by_the_real_validator(
    dictionary: Dictionary, candidate_index: CandidateIndex
) -> None:
    for fragment in ("く", "ばん", "ょう"[1:], "あ"):
        for candidate in candidate_index.candidates(fragment)[:30]:
            assert dictionary.matches(candidate.reading, fragment), (fragment, candidate)
