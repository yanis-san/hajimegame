from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.japanese.fragments import FragmentTable, count_fragments, playable_table
from app.japanese.levels import bucket_for_rank, level_index

APP = Path(__file__).resolve().parent.parent / "app"
FORBIDDEN = {"fastapi", "starlette", "redis", "sqlalchemy", "asyncpg", "uvicorn", "msgspec"}


@pytest.mark.parametrize("package", ["games", "japanese"])
def test_pure_packages_do_not_import_infrastructure(package: str) -> None:
    for path in (APP / package).rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in FORBIDDEN, f"{path.name} imports {name}"
                assert not name.startswith(("app.realtime", "app.api", "app.db")), (
                    f"{path.name} imports {name}"
                )


def test_levels() -> None:
    assert level_index("n5") == 0
    assert bucket_for_rank(1) == 0
    assert bucket_for_rank(7) == 1
    assert bucket_for_rank(99) == 4
    with pytest.raises(ValueError, match="unknown level"):
        level_index("n0")


def test_count_fragments_counts_each_entry_once_per_bucket() -> None:
    # one entry with two readings that both contain "か" still counts once
    counts = count_fragments([(1, ["かさ", "さか"]) for _ in range(25)])
    assert counts["か"] == [0, 25, 0, 0, 0]
    assert counts["かさ"] == [0, 25, 0, 0, 0]
    assert count_fragments([(0, ["かさ"])]) == {}  # too rare to store


def test_fragment_table_requires_playable_fragments() -> None:
    with pytest.raises(ValueError, match="no fragment"):
        FragmentTable({"か": [1, 0, 0, 0, 0]}, "n5", min_words=80)
    with pytest.raises(ValueError, match="cannot build"):
        playable_table({"か": [1, 0, 0, 0, 0]}, "n5")


def test_unplayable_single_kana_are_skipped() -> None:
    buckets = {
        "ん": [999] * 5,
        "を": [999] * 5,
        **{f"{c}": [100] * 5 for c in "かきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも"},
    }
    table = FragmentTable(buckets, "n1")
    assert "ん" not in {f.text for f in table.fragments}
