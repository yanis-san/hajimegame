from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.japanese.candidates import CandidateIndex
from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import Client, RunningServer, running_server


@pytest.fixture
async def server(dictionary: Dictionary, candidate_index: CandidateIndex) -> Any:
    async with running_server(dictionary, candidates=candidate_index) as srv:
        yield srv


async def host_room(srv: RunningServer, mode: str = "classic") -> tuple[str, Client]:
    created = await srv.http.post("/api/rooms", headers=_headers(), json={"mode": mode})
    code = created.json()["code"]
    host = srv.client(code)
    await host.connect()
    await host.join(code, "Yanis")
    return code, host


def _headers() -> dict[str, str]:
    from tests.realtime.helpers import CSRF

    return CSRF


async def test_host_adds_and_removes_cpu_players(server: RunningServer) -> None:
    _, host = await host_room(server)
    await host.send(t="add_bot", difficulty="hard")
    patch = await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    bot = next(p for p in patch["players"].values() if p["bot"])
    assert bot["difficulty"] == "hard"
    assert bot["connected"] is True and bot["ready"] is True  # CPU players are always ready
    assert bot["name"] and bot["id"] != host.player_id

    await host.send(t="remove_bot", player_id=bot["id"])
    gone = await host.wait("patch", lambda m: m.get("players", {}).get(bot["id"], 1) is None)
    assert gone["players"][bot["id"]] is None
    await host.close()


async def test_only_the_host_manages_cpu_players(server: RunningServer) -> None:
    code, host = await host_room(server)
    guest = server.client(code)
    await guest.connect()
    await guest.join(code, "Aya")
    await guest.send(t="add_bot")
    assert (await guest.wait("error"))["code"] == "not_host"
    await host.send(t="add_bot")
    patch = await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    bot_id = next(i for i, p in patch["players"].items() if p["bot"])
    await guest.send(t="remove_bot", player_id=bot_id)
    assert (await guest.wait("error", lambda m: m["code"] == "not_host"))["code"] == "not_host"
    await host.send(t="remove_bot", player_id=host.player_id)  # a human is not a bot
    assert (await host.wait("error", lambda m: m["code"] == "not_allowed"))["code"] == "not_allowed"
    await guest.close()
    await host.close()


async def test_cpu_players_count_toward_the_room_limit(server: RunningServer) -> None:
    _, host = await host_room(server)
    await host.send(t="settings", max_players=2)
    await host.send(t="add_bot")
    await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    await host.send(t="add_bot")
    assert (await host.wait("error"))["code"] == "room_full"
    await host.close()


async def test_cpus_are_refused_while_the_word_index_is_still_loading(dictionary: Dictionary) -> None:
    async with running_server(dictionary) as srv:  # no index
        _, host = await host_room(srv)
        await host.send(t="add_bot")
        assert (await host.wait("error"))["code"] == "bots_loading"
        await host.close()


async def test_a_human_can_start_alone_against_a_cpu_and_the_cpu_plays(server: RunningServer) -> None:
    _, host = await host_room(server)
    await host.send(t="settings", lives=3)
    await host.send(t="add_bot", difficulty="hard")
    patch = await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    bot_id = next(i for i, p in patch["players"].items() if p["bot"])
    await host.send(t="start")  # no "ready" needed: the CPU is always ready
    await host.wait("turn", timeout=8)

    # the human never answers; the CPU answers on its turns, then the human runs out of lives
    over = await host.wait("game_over", timeout=30)
    assert over["winner_id"] == bot_id
    accepted = [m for m in host.messages if m["t"] == "accepted"]
    assert accepted, "the CPU never played a word"
    assert all(m["player_id"] == bot_id for m in accepted)
    assert all(m["meaning_en"] or m["meaning_fr"] for m in accepted[:3])
    assert any(m["t"] == "typing" and m["player_id"] == bot_id for m in host.messages)  # we saw it "type"
    await host.close()


async def test_cpu_follows_the_shiritori_chain(server: RunningServer) -> None:
    _, host = await host_room(server, mode="shiritori")
    await host.send(t="settings", lives=2)
    await host.send(t="add_bot", difficulty="hard")
    await host.send(t="add_bot", difficulty="hard")
    await host.wait(
        "patch", lambda m: sum(1 for p in m.get("players", {}).values() if p and p.get("bot")) >= 1
    )
    await asyncio.sleep(0.3)
    await host.send(t="start")
    await host.wait("turn", timeout=8)
    await host.wait("accepted", timeout=15)
    await host.wait("game_over", timeout=60)
    turns = [m for m in host.messages if m["t"] == "turn"]
    words = [m for m in host.messages if m["t"] == "accepted"]
    assert len(words) >= 2
    for word in words:
        turn = next(t for t in turns if t["turn"] == word["turn"])
        assert word["reading"][0] == turn["fragment"]  # starts with the kana it was given
        assert not word["reading"].endswith("ん")
    await host.close()


async def test_cpus_stay_in_the_room_for_the_rematch(server: RunningServer) -> None:
    _, host = await host_room(server)
    await host.send(t="settings", lives=1)
    await host.send(t="add_bot", difficulty="hard")
    await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    await host.send(t="start")
    await host.wait("game_over", timeout=40)
    await host.send(t="rematch")
    patch = await host.wait("patch", lambda m: m.get("phase") == "lobby")
    assert any(p["bot"] for p in patch["players"].values())
    assert all(p["ready"] for p in patch["players"].values() if p["bot"])
    await host.close()
