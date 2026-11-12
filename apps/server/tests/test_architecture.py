from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.japanese.fragments import FragmentTable, count_fragments

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


def test_count_fragments_counts_each_entry_once() -> None:
    # one entry with two readings that both contain "か" still counts once
    counts = count_fragments([["かさ", "さか"] for _ in range(25)])
    assert counts["か"] == 25
    assert counts["かさ"] == 25
    assert count_fragments([["かさ"]]) == {}  # too rare to store


def test_fragment_table_requires_playable_fragments() -> None:
    with pytest.raises(ValueError, match="no fragment"):
        FragmentTable({"か": 1}, min_words=80)


def test_unplayable_single_kana_are_skipped() -> None:
    buckets = {
        "ん": 999,
        "を": 999,
        **{f"{c}": 100 for c in "かきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも"},
    }
    table = FragmentTable(buckets)
    assert "ん" not in {f.text for f in table.fragments}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names |= {f"{node.module}.{a.name}" for a in node.names}
    return names


def _game_modules(package: Path) -> list[Path]:
    """One module (or folder) per game, not counting the package's own ``__init__``."""
    return [p for p in sorted(package.iterdir()) if p.name not in {"__init__.py", "__pycache__"}]


def test_a_game_never_imports_another_game() -> None:
    """Each game is isolated: its engine, recording, tables and statistics know only themselves."""
    layers = {
        "app.games": [p for p in _game_modules(APP / "games") if p.is_dir()],
        "app.db.games": [p for p in _game_modules(APP / "db" / "games") if p.suffix == ".py"],
        "app.api.games": [p for p in _game_modules(APP / "api" / "games") if p.suffix == ".py"],
    }
    for package, games in layers.items():
        names = {g.stem for g in games}
        for game in games:
            files = list(game.rglob("*.py")) if game.is_dir() else [game]
            for file in files:
                for imported in _imports(file):
                    for other in names - {game.stem}:
                        assert not imported.startswith(f"{package}.{other}"), (
                            f"{file.relative_to(APP)} imports {imported}: a game must not use another game"
                        )


def test_the_common_database_model_knows_no_particular_game() -> None:
    forbidden = ("app.db.games", "app.games.bomb", "app.api.games")
    for imported in _imports(APP / "db" / "models.py"):
        assert not imported.startswith(forbidden), (
            f"app/db/models.py imports {imported}: it is the shared part"
        )
    for imported in _imports(APP / "games" / "recording.py"):
        assert not imported.startswith("app.games.bomb"), f"the shared recording imports {imported}"
