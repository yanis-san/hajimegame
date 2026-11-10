from __future__ import annotations

import pytest

from app.japanese.dictionary import Dictionary


@pytest.fixture(scope="session")
def dictionary() -> Dictionary:
    return Dictionary.load()
