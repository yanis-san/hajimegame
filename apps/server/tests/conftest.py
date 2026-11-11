from __future__ import annotations

import pytest

from app.japanese.candidates import CandidateIndex
from app.japanese.dictionary import Dictionary


@pytest.fixture(scope="session")
def dictionary() -> Dictionary:
    return Dictionary.load()


@pytest.fixture(scope="session")
def candidate_index(dictionary: Dictionary) -> CandidateIndex:
    return CandidateIndex(dictionary)
