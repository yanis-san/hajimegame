from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

TOOL = Path(__file__).resolve().parents[3] / "tools" / "gen_protocol.py"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_protocol", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_protocol_files_are_up_to_date() -> None:
    tool = load_tool()
    ts, schema = tool.generate()
    assert tool.TS_PATH.read_text(encoding="utf-8") == ts, "run `make protocol`"
    assert tool.SCHEMA_PATH.read_text(encoding="utf-8") == schema, "run `make protocol`"


def test_generated_types_cover_every_message() -> None:
    ts, _ = load_tool().generate()
    for name in (
        "Join",
        "Rejoin",
        "Submit",
        "Snapshot",
        "Patch",
        "Turn",
        "Accepted",
        "GameOver",
        "Pong",
        "Error",
    ):
        assert f"export interface {name} " in ts
    assert "export type ServerMessage =" in ts
    assert "players?: Record<string, PlayerView | null>;" in ts


@pytest.mark.parametrize("tag", ["join", "settings", "typing", "submit", "ping"])
def test_schema_lists_client_tags(tag: str) -> None:
    _, schema = load_tool().generate()
    assert f'"{tag}"' in schema
