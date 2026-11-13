from __future__ import annotations

import asyncio
import itertools
from collections.abc import Callable
from typing import Any

import pytest
from websockets.exceptions import InvalidStatus

from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import CSRF, Client, RunningServer, running_server


@pytest.fixture
async def server(dictionary: Dictionary) -> Any:
    async with running_server(dictionary) as srv:
        yield srv


async def lobby(
    srv: RunningServer, count: int = 2, names: tuple[str, ...] = ("Aya", "Ben", "Chi", "Dai")
) -> tuple[str, list[Client]]:
    code = await srv.create_room()
    clients = [srv.client(code) for _ in range(count)]
    for client, name in zip(clients, names, strict=False):
        await client.connect()
        await client.join(code, name)
    return code, clients


async def start_game(clients: list[Client], **settings: Any) -> None:
    host = clients[0]
    if settings:
        await host.send(t="settings", **settings)
        await host.wait("patch", lambda m: "settings" in m)
    for client in clients[1:]:
        await client.send(t="ready", ready=True)
        await host.wait(
            "patch",
            lambda m, cid=client.player_id: m.get("players", {}).get(cid, {}).get("ready") is True,  # type: ignore[misc]
        )
    await host.send(t="start")
    for client in clients:
        await client.wait("turn", timeout=8)


def valid_word(dictionary: Dictionary, fragment: str, used: set[str]) -> str:
    """A word the game accepts for ``fragment``: every dictionary word is playable."""
    for word in dictionary.sample_words(fragment, 200):
        if word not in used:
            used.add(word)
            return word
    raise AssertionError(f"no word for {fragment}")


async def test_rest_create_and_info(server: RunningServer) -> None:
    code = await server.create_room()
    assert len(code) == 6
    assert not set(code) & set("01OIL")
    info = await server.http.get(f"/api/rooms/{code.lower()}")
    assert info.json()["phase"] == "lobby"
    assert (await server.http.get("/api/rooms/ZZZZZZ")).status_code == 404
    assert (await server.http.get("/healthz")).json() == {"status": "ok"}
    ready = await server.http.get("/readyz")
    assert ready.status_code == 200
    metrics = await server.http.get("/metrics")
    assert "hajime_rooms_active" in metrics.text


async def test_csrf_and_security_headers(server: RunningServer) -> None:
    no_header = await server.http.post("/api/rooms", headers={"Origin": CSRF["Origin"]})
    assert no_header.status_code == 403
    bad_origin = await server.http.post("/api/rooms", headers={**CSRF, "Origin": "https://evil.example"})
    assert bad_origin.status_code == 403
    ok = await server.http.get("/healthz")
    assert ok.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in ok.headers["content-security-policy"]


async def test_room_creation_is_rate_limited_per_ip(dictionary: Dictionary) -> None:
    async with running_server(dictionary, room_creations_per_minute=3, max_rooms_per_ip=50) as srv:
        statuses = [(await srv.http.post("/api/rooms", headers=CSRF)).status_code for _ in range(5)]
        assert statuses == [201, 201, 201, 429, 429]


async def test_rooms_per_ip_cap(dictionary: Dictionary) -> None:
    async with running_server(dictionary, max_rooms_per_ip=2) as srv:
        statuses = [(await srv.http.post("/api/rooms", headers=CSRF)).status_code for _ in range(3)]
        assert statuses == [201, 201, 429]


async def test_websocket_origin_is_checked(server: RunningServer) -> None:
    code = await server.create_room()
    evil = server.client(code, origin="https://evil.example")
    with pytest.raises(InvalidStatus):
        await evil.connect()


async def test_unknown_room(server: RunningServer) -> None:
    async with server.client("ZZZZZZ") as client:
        error = await client.wait("error")
        assert error["code"] == "room_not_found"


async def test_join_snapshot_and_host(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as a, server.client(code) as b:
        snap = await a.join(code, "Aya", avatar=3)
        assert snap["phase"] == "lobby"
        assert snap["host"] == snap["you"] == a.player_id
        assert snap["players"][0]["name"] == "Aya"
        assert snap["players"][0]["avatar"] == 3
        assert len(a.token) >= 16
        snap_b = await b.join(code, "Aya")  # duplicate name gets a suffix
        assert {p["name"] for p in snap_b["players"]} == {"Aya", "Aya 2"}
        patch = await a.wait("patch", lambda m: "players" in m and b.player_id in m["players"])
        assert patch["players"][b.player_id]["name"] == "Aya 2"
        assert patch["seq"] > snap["seq"]


async def test_invalid_nickname_is_refused(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send(t="join", room=code, name="fuck")
        assert (await c.wait("error"))["code"] == "name_invalid"


async def test_non_host_cannot_start_or_change_settings(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await b.send(t="start")
    assert (await b.wait("error"))["code"] == "not_host"
    await b.send(t="settings", lives=5)
    assert (await b.wait("error", lambda m: m["code"] == "not_host"))["code"] == "not_host"
    await a.close()
    await b.close()


async def test_start_requires_players_ready_and_two_players(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as a:
        await a.join(code, "Aya")
        await a.send(t="start")
        assert (await a.wait("error"))["code"] == "need_more_players"
        async with server.client(code) as b:
            await b.join(code, "Ben")
            await a.send(t="start")
            assert (await a.wait("error", lambda m: m["code"] == "players_not_ready"))[
                "code"
            ] == "players_not_ready"


async def test_settings_are_validated_and_broadcast(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await a.send(t="settings", lives=5, bonus_kana=True)
    patch = await b.wait("patch", lambda m: "settings" in m)
    assert patch["settings"]["lives"] == 5
    assert patch["settings"]["bonus_kana"] is True
    assert patch["settings"]["mode"] == "classic"
    await a.send(t="settings", lives=9)
    assert (await a.wait("error"))["code"] == "bad_message"
    await a.send(t="settings", max_players=2)
    await a.send(t="settings", max_players=3)
    await a.close()
    await b.close()


async def test_full_game_flow(server: RunningServer, dictionary: Dictionary) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b], lives=1)
    assert (await a.wait("countdown"))["ends_at"] > 0
    used: set[str] = set()
    clients = {a.player_id: a, b.player_id: b}

    turn = await a.wait("turn")
    active = clients[turn["player_id"]]
    # a bad word first: refused, still the same turn
    await active.send(t="submit", text="zzzzzz")
    rejected = await active.wait("rejected")
    assert rejected["reason"] == "not_in_dictionary"
    other = b if active is a else a
    await other.send(t="submit", text="くるま")
    assert (await other.wait("rejected"))["reason"] == "not_your_turn"

    word = valid_word(dictionary, turn["fragment"], used)
    await active.send(t="submit", text=word)
    accepted = await a.wait("accepted")
    assert accepted["word"] == dictionary.display_form(word)
    assert accepted["player_id"] == active.player_id
    assert accepted["score_gain"] >= 1
    next_turn = await a.wait("turn", lambda m: m["turn"] > turn["turn"])
    assert next_turn["player_id"] == other.player_id
    assert next_turn["deadline"] > turn["deadline"] - 1

    # nobody answers: lives=1 so the bomb eliminates someone and the game ends
    over = await a.wait("game_over", timeout=10)
    assert over["winner_id"] in clients
    assert [r["place"] for r in over["results"]] == [1, 2]
    assert [w["word"] for w in over["words"]] == [
        dictionary.display_form(word)
    ]  # the whole game, for the review
    assert over["words"][0]["player_id"] == active.player_id
    assert over["words"][0]["meaning_en"]
    assert (await b.wait("game_over"))["winner_id"] == over["winner_id"]
    assert a.count("explosion") >= 1
    assert a.count("elimination") == 1

    # rematch resets the room to the lobby
    host = a
    await host.send(t="rematch")
    patch = await host.wait("patch", lambda m: m.get("phase") == "lobby")
    assert all(not p["ready"] for p in patch["players"].values())


async def play_turn(
    watcher: Client, clients: dict[str, Client], dictionary: Dictionary, used: set[str], after_turn: int
) -> str:
    """Wait for the next turn and let its active player answer with a valid word; returns that word."""
    turn = await watcher.wait("turn", lambda m: m["turn"] > after_turn)
    word = valid_word(dictionary, turn["fragment"], used)
    await clients[turn["player_id"]].send(t="submit", text=word)
    shown = dictionary.display_form(word)  # a katakana word is shown in katakana
    await watcher.wait("accepted", lambda m: m["word"] == shown)
    return shown


async def test_game_over_carries_every_word_not_just_the_last_ones(
    server: RunningServer, dictionary: Dictionary
) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b], lives=1)
    clients = {a.player_id: a, b.player_id: b}
    used: set[str] = set()
    played: list[str] = []
    for _ in range(45):  # more than a snapshot carries during the game
        played.append(await play_turn(a, clients, dictionary, used, len(played)))
    over = await a.wait("game_over", timeout=30)
    assert [w["word"] for w in over["words"]] == played
    await a.close()
    await b.close()


async def test_seq_is_gapless_for_broadcasts(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b], lives=1)
    await a.wait("game_over", timeout=10)
    await asyncio.sleep(0.1)
    seqs = [
        m["seq"]
        for m in b.messages
        if m["t"] in {"patch", "turn", "explosion", "elimination", "game_over", "countdown", "accepted"}
    ]
    assert seqs == sorted(seqs)
    assert all(later - earlier <= 1 for earlier, later in itertools.pairwise(seqs))


async def test_typing_is_relayed_to_others_only(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b])
    clients = {a.player_id: a, b.player_id: b}
    turn = await a.wait("turn")
    active = clients[turn["player_id"]]
    other = b if active is a else a
    await active.send(t="typing", text="くる")
    event = await other.wait("typing")
    assert event["text"] == "くる"
    assert event["player_id"] == active.player_id
    await asyncio.sleep(0.2)
    assert active.count("typing") == 0
    # a non-active player cannot spoof typing
    before = active.count("typing")
    await other.send(t="typing", text="spoof")
    await asyncio.sleep(0.2)
    assert active.count("typing") == before


async def test_typing_is_rate_capped(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b])
    clients = {a.player_id: a, b.player_id: b}
    turn = await a.wait("turn")
    active = clients[turn["player_id"]]
    other = b if active is a else a
    start = other.count("typing")
    for i in range(20):
        await active.send(t="typing", text="あ" * (i % 5 + 1))
    await asyncio.sleep(0.5)
    relayed = other.count("typing") - start
    assert 1 <= relayed < 20


async def test_ping_returns_server_time(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send(t="ping", n=7, t0=123.5)
        pong = await c.wait("pong")
        assert pong["n"] == 7
        assert pong["t0"] == 123.5
        assert pong["server_time"] > 0


async def test_invalid_messages_are_counted_and_eventually_kick(dictionary: Dictionary) -> None:
    async with running_server(dictionary, invalid_messages_before_kick=3) as srv:
        code = await srv.create_room()
        async with srv.client(code) as c:
            for _ in range(4):
                await c.send_raw("{not json")
            assert (await c.wait("error"))["code"] == "bad_message"
            assert await c.wait_closed() == 1008


async def test_oversized_frame_closes_connection(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send_raw("x" * 5000)
        assert await c.wait_closed() == 1009


async def test_wrong_protocol_version(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send(t="join", room=code, name="Aya", v=99)
        assert (await c.wait("error"))["code"] == "bad_version"


async def test_message_rate_limit(dictionary: Dictionary) -> None:
    async with running_server(dictionary, messages_per_second=5, message_burst=5) as srv:
        code = await srv.create_room()
        async with srv.client(code) as c:
            await c.join(code, "Aya")
            for _ in range(30):
                await c.send(t="ready", ready=True)
            assert (await c.wait("error", lambda m: m["code"] == "rate_limited"))["code"] == "rate_limited"


async def test_join_attempt_rate_limit_per_ip(dictionary: Dictionary) -> None:
    async with running_server(dictionary, join_attempts_per_minute=2) as srv:
        code = await srv.create_room()
        async with srv.client(code), srv.client(code):
            pass
        denied = srv.client(code)
        with pytest.raises(InvalidStatus):
            await denied.connect()


async def test_room_full_and_spectators(server: RunningServer) -> None:
    code = await server.create_room()
    players = [server.client(code) for _ in range(8)]
    for i, p in enumerate(players):
        await p.connect()
        await p.join(code, f"P{i}")
    extra = server.client(code)
    await extra.connect()
    await extra.send(t="join", room=code, name="Late")
    assert (await extra.wait("error"))["code"] == "room_full"
    watcher = server.client(code)
    await watcher.connect()
    snap = await watcher.join(code, "Watcher", spectator=True)
    assert snap["spectator"] is True
    assert len(snap["players"]) == 8
    patch = await players[0].wait("patch", lambda m: m.get("spectators") == 1)
    assert patch["spectators"] == 1
    await watcher.send(t="ready", ready=True)
    assert (await watcher.wait("error"))["code"] == "wrong_phase"
    for c in [*players, extra, watcher]:
        await c.close()


async def test_cannot_join_a_running_game_as_player_but_can_spectate(server: RunningServer) -> None:
    code, (a, b) = await lobby(server)
    await start_game([a, b])
    late = server.client(code)
    await late.connect()
    await late.send(t="join", room=code, name="Late")
    assert (await late.wait("error"))["code"] == "wrong_phase"
    snap = await late.join(code, "Late", spectator=True)
    assert snap["phase"] == "playing"
    assert snap["turn"] is not None
    await late.close()


async def test_host_can_kick_and_host_transfers_on_leave(server: RunningServer) -> None:
    _code, (a, b, c) = await lobby(server, 3)
    await a.send(t="kick", player_id=c.player_id)
    assert (await c.wait("error"))["code"] == "kicked"
    assert await c.wait_closed() == 4403
    patch = await b.wait("patch", lambda m: m.get("players", {}).get(c.player_id, 1) is None)
    assert patch["players"][c.player_id] is None
    await a.send(t="leave")
    transfer = await b.wait("patch", lambda m: m.get("host") == b.player_id)
    assert transfer["host"] == b.player_id
    await a.close()
    await b.close()


async def test_chat_is_filtered_and_rate_limited(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await a.send(t="chat", text="salut <b>tout le monde</b>")
    chat = await b.wait("chat")
    assert chat["text"] == "salut <b>tout le monde</b>"  # sent as text; the client never renders HTML
    assert chat["name"] == "Aya"
    await a.send(t="chat", text="espèce de connard")
    await asyncio.sleep(0.1)
    assert b.count("chat") == 1
    for _ in range(6):
        await a.send(t="chat", text="spam")
    assert (await a.wait("error", lambda m: m["code"] == "rate_limited"))["code"] == "rate_limited"


async def test_actions_before_join_are_refused(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send(t="submit", text="くるま")
        assert (await c.wait("error"))["code"] == "not_allowed"


async def test_bad_token_is_refused(server: RunningServer) -> None:
    code = await server.create_room()
    async with server.client(code) as c:
        await c.send(t="rejoin", room=code, token="x" * 22)
        assert (await c.wait("error"))["code"] == "bad_token"
        assert await c.wait_closed() == 4401


async def test_reconnect_keeps_place_and_state(server: RunningServer, dictionary: Dictionary) -> None:
    code, (a, b) = await lobby(server)
    await start_game([a, b])
    clients = {a.player_id: a, b.player_id: b}
    turn = await a.wait("turn")
    active = clients[turn["player_id"]]
    other = b if active is a else a
    word = valid_word(dictionary, turn["fragment"], set())
    await active.send(t="submit", text=word)
    await other.wait("accepted")
    token, pid = other.token, other.player_id

    await other.drop()
    gone = await active.wait("patch", lambda m: m.get("players", {}).get(pid, {}).get("connected") is False)
    assert gone["players"][pid]["connected"] is False

    back = server.client(code)
    await back.connect()
    await back.send(t="rejoin", room=code, token=token)
    welcome = await back.wait("welcome")
    assert welcome["player_id"] == pid
    snap = await back.wait("snapshot")
    assert snap["phase"] == "playing"
    assert snap["you"] == pid
    assert any(w["word"] == dictionary.display_form(word) for w in snap["words"])
    me = next(p for p in snap["players"] if p["id"] == pid)
    assert me["connected"] is True
    scorer = next(p for p in snap["players"] if p["id"] == active.player_id)
    assert scorer["score"] >= 2  # the exact state, including what happened while we were away
    again = await active.wait("patch", lambda m: m.get("players", {}).get(pid, {}).get("connected") is True)
    assert again["players"][pid]["connected"] is True
    await back.close()
    await active.close()


async def test_new_connection_replaces_the_old_one(server: RunningServer) -> None:
    code, (a, b) = await lobby(server)
    dup = server.client(code)
    await dup.connect()
    await dup.send(t="rejoin", room=code, token=b.token)
    await dup.wait("snapshot")
    assert (await b.wait("error"))["code"] == "replaced"
    assert await b.wait_closed() == 4000
    await a.send(t="ready", ready=True)  # the room still works
    await dup.wait("patch", lambda m: "players" in m)
    await dup.close()
    await a.close()


async def test_disconnected_player_is_removed_after_grace(dictionary: Dictionary) -> None:
    async with running_server(dictionary, scale=50.0, grace_seconds=5.0) as srv:
        code, (a, b) = await lobby(srv)
        await a.drop()
        removed = await b.wait("patch", lambda m: m.get("players", {}).get(a.player_id, 1) is None, timeout=5)
        assert removed["players"][a.player_id] is None
        host = await b.wait("patch", lambda m: m.get("host") == b.player_id)
        assert host["host"] == b.player_id
        late = srv.client(code)
        await late.connect()
        await late.send(t="rejoin", room=code, token=a.token)
        assert (await late.wait("error"))["code"] == "bad_token"
        await b.close()


async def test_disconnected_player_is_eliminated_after_grace_during_game(dictionary: Dictionary) -> None:
    async with running_server(dictionary, scale=50.0, grace_seconds=5.0) as srv:
        _, (a, b) = await lobby(srv)
        await start_game([a, b], lives=5)
        await a.drop()
        over = await b.wait("game_over", timeout=10)
        assert over["winner_id"] == b.player_id
        eliminated = b.last("elimination")
        assert eliminated is not None
        assert eliminated["player_id"] == a.player_id
        await b.close()


async def test_countdown_is_aborted_if_players_leave(dictionary: Dictionary) -> None:
    async with running_server(dictionary, scale=1.0, countdown_seconds=1.0) as srv:
        _, (a, b) = await lobby(srv)
        await b.send(t="ready", ready=True)
        await asyncio.sleep(0.1)
        await a.send(t="start")
        await a.wait("countdown")
        await b.send(t="leave")
        patch = await a.wait("patch", lambda m: m.get("phase") == "lobby")
        assert patch["phase"] == "lobby"
        await a.close()


async def test_graceful_shutdown_tells_clients_to_reconnect(dictionary: Dictionary) -> None:
    async with running_server(dictionary) as srv:
        code = await srv.create_room()
        c = srv.client(code)
        await c.connect()
        await c.join(code, "Aya")
        await srv.manager.shutdown()
        error = await c.wait("error")
        assert error["code"] == "server_restarting"
        assert await c.wait_closed() == 1012
        assert srv.manager.room_count == 0


async def test_zombie_connection_is_closed_by_heartbeat(dictionary: Dictionary) -> None:
    async with running_server(dictionary, scale=1.0, heartbeat_seconds=0.2) as srv:
        code = await srv.create_room()
        c = srv.client(code)
        await c.connect()
        await c.join(code, "Aya")
        assert await c.wait_closed(timeout=3) == 1001


async def test_idle_room_is_cleaned_up(dictionary: Dictionary) -> None:
    async with running_server(dictionary, scale=1.0, room_idle_seconds=0.3) as srv:
        await srv.create_room()
        assert srv.manager.room_count == 1
        for _ in range(40):
            if srv.manager.room_count == 0:
                break
            await asyncio.sleep(0.05)
        assert srv.manager.room_count == 0


async def test_slow_consumer_is_disconnected(dictionary: Dictionary) -> None:
    from app.realtime.connection import CloseRequest, Connection

    conn = Connection(ip="x", queue_size=3)
    assert all(conn.offer("frame") for _ in range(3))
    assert conn.offer("overflow") is False
    items = []
    while not conn.queue.empty():
        items.append(conn.queue.get_nowait())
    assert isinstance(items[-1], CloseRequest)
    assert items[-1].code == 1013
    assert conn.offer("later") is False


async def test_mode_is_fixed_when_the_room_is_created(server: RunningServer) -> None:
    created = await server.http.post("/api/rooms", headers=CSRF, json={"mode": "shiritori"})
    code = created.json()["code"]
    async with server.client(code) as host:
        snap = await host.join(code, "Aya")
        assert snap["settings"]["mode"] == "shiritori"
        await host.send(t="settings", mode="classic")  # no such field: refused as an invalid message
        assert (await host.wait("error"))["code"] == "bad_message"
        await host.send(t="settings", lives=2)
        patch = await host.wait("patch", lambda m: "settings" in m)
        assert patch["settings"]["mode"] == "shiritori"
        assert patch["settings"]["lives"] == 2


async def test_the_proxy_probe_says_starting_until_the_cpu_index_is_built(server: RunningServer) -> None:
    """`/startupz` is what the reverse proxy asks: 503 while the CPU index is not built (no CPU player can
    be added yet), 200 afterwards, and it never depends on the database."""
    assert (await server.http.get("/startupz")).status_code == 200  # tests do not preload the CPU index
    settings = server.app.state.settings
    index = server.manager.candidates
    settings.preload_bots = True  # as in production: the index is expected
    try:
        server.manager.candidates = None
        starting = await server.http.get("/startupz")
        assert (starting.status_code, starting.json()) == (503, {"status": "starting"})
        server.manager.candidates = index or object()
        assert (await server.http.get("/startupz")).json() == {"status": "ready"}
    finally:
        settings.preload_bots = False
        server.manager.candidates = index


async def test_kanji_mode_levels_a_kanji_turn_and_a_word_written_with_it(
    server: RunningServer, dictionary: Dictionary
) -> None:
    from app.japanese.kanji import KanjiBook

    book = KanjiBook.load(dictionary)
    created = await server.http.post("/api/rooms", headers=CSRF, json={"mode": "kanji"})
    code = created.json()["code"]
    a, b = server.client(code), server.client(code)
    for client, name in ((a, "Aya"), (b, "Ben")):
        await client.connect()
        snap = await client.join(code, name)
        assert snap["settings"]["mode"] == "kanji"
    assert snap["settings"]["levels"] == [5, 4]  # the default
    await a.send(t="settings", levels=[5])
    patch = await a.wait("patch", lambda m: "settings" in m)
    assert patch["settings"]["levels"] == [5]
    await a.send(t="settings", levels=[])  # at least one level
    assert (await a.wait("error"))["code"] == "bad_message"
    await a.send(t="settings", levels=[7])
    assert (await a.wait("error", start=1))["code"] == "bad_message"

    clients = {a.player_id: a, b.player_id: b}
    await start_game([a, b])
    turn = await a.wait("turn")
    kanji = book.get(turn["fragment"])
    assert kanji is not None and kanji.level == 5  # the fragment of the turn is a kanji of the chosen level
    active = clients[turn["player_id"]]
    other = b if active is a else a

    # a word that is not written with this kanji: refused, same turn
    wrong = next(
        w for c in book.pool([5]) for w in book.sample_words(c, 1) if book.reject_reason(w, turn["fragment"])
    )
    await active.send(t="submit", text=wrong)
    assert (await active.wait("rejected"))["reason"] == "missing_fragment"
    # a word that is: accepted, and the other player gets the next kanji
    word = book.sample_words(turn["fragment"], 1)[0]
    await active.send(t="submit", text=word)
    accepted = await a.wait("accepted")
    assert accepted["word"] and accepted["player_id"] == active.player_id
    nxt = await a.wait("turn", lambda m: m["turn"] > turn["turn"])
    assert nxt["player_id"] == other.player_id and book.get(nxt["fragment"]) is not None
    await a.close()
    await b.close()


def turn_after(number: int) -> Callable[[dict[str, Any]], bool]:
    return lambda m: bool(m["turn"] > number)


def turn_is(number: int) -> Callable[[dict[str, Any]], bool]:
    return lambda m: bool(m["turn"] == number)


async def test_a_cpu_plays_the_kanji_mode(server: RunningServer, dictionary: Dictionary) -> None:
    from app.japanese.kanji import KanjiBook

    book = KanjiBook.load(dictionary)
    created = await server.http.post("/api/rooms", headers=CSRF, json={"mode": "kanji"})
    code = created.json()["code"]
    host = server.client(code)
    await host.connect()
    await host.join(code, "Aya")
    await host.send(
        t="add_bot", difficulty="hard"
    )  # works without the fragment index: it plays from the kanji table
    await host.wait("patch", lambda m: any(p and p.get("bot") for p in m.get("players", {}).values()))
    await host.send(t="start")
    last = 0
    for _ in range(8):  # the human does not answer: the CPU plays within the first turns
        turn = await host.wait("turn", turn_after(last), timeout=15)
        last = turn["turn"]
        assert book.get(turn["fragment"]) is not None
        if turn["player_id"] != host.player_id:
            accepted = await host.wait("accepted", turn_is(last), timeout=15)
            assert accepted["player_id"] == turn["player_id"]
            break
    else:
        raise AssertionError("the CPU never played a word")
    await host.close()


async def test_a_player_who_leaves_mid_game_is_still_named_in_the_recap(server: RunningServer) -> None:
    _, (a, b, c) = await lobby(server, 3)
    await start_game([a, b, c], lives=1, fuse_seconds=5)
    await c.send(t="leave")  # leaves in the middle of the game: eliminated, the game goes on for the others
    over = await a.wait("game_over", timeout=30)
    rows = {r["player_id"]: r for r in over["results"]}
    assert len(rows) == 3
    assert rows[c.player_id]["name"] == "Chi" and rows[c.player_id]["avatar"] >= 0
    assert {r["name"] for r in rows.values()} == {"Aya", "Ben", "Chi"}
    await a.close()
    await b.close()


async def test_a_timed_game_tells_every_turn_when_the_clock_ends(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await a.send(t="settings", duration=61)  # only the offered durations
    assert (await a.wait("error"))["code"] == "bad_message"
    await start_game([a, b], duration=120)
    turn = await a.wait("turn")
    assert turn["ends_at"] is not None
    snapshot_turn = (await b.wait("turn"))["ends_at"]
    assert snapshot_turn == turn["ends_at"]
    # an explosion takes points, not a life, and nobody is eliminated
    explosion = await a.wait("explosion", timeout=20)
    assert explosion["lives"] == 3 and explosion["score"] == 0
    await a.close()
    await b.close()


async def test_a_game_without_a_clock_has_no_end_time(server: RunningServer) -> None:
    _, (a, b) = await lobby(server)
    await start_game([a, b])
    assert (await a.wait("turn"))["ends_at"] is None
    await a.close()
    await b.close()
