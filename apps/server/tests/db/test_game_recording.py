"""A real game over WebSockets against a server with a database: what is stored and what stays private."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import running_server
from tests.realtime.test_websocket import start_game, valid_word

AYA = str(uuid.uuid4())
BEN = str(uuid.uuid4())


async def query(url: str, sql: str) -> list[tuple[Any, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            return [tuple(row) for row in (await connection.execute(sa.text(sql))).all()]
    finally:
        await engine.dispose()


async def wait_for_game(url: str) -> None:
    for _ in range(100):
        if await query(url, "select id from games"):
            return
        await asyncio.sleep(0.05)
    raise AssertionError("the finished game was never written to the database")


async def test_a_played_game_is_stored_and_guest_ids_stay_private(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        code = await server.create_room()
        aya, ben = server.client(code), server.client(code)
        await aya.connect()
        await ben.connect()
        await aya.join(code, "Aya", guest_id=AYA, lang="fr")
        await ben.join(code, "Ben", guest_id=BEN, lang="ja")
        await start_game([aya, ben], lives=1)

        clients = {aya.player_id: aya, ben.player_id: ben}
        turn = await aya.wait("turn")
        word = valid_word(dictionary, turn["fragment"], set())
        await clients[turn["player_id"]].send(t="submit", text=word)
        await aya.wait("accepted")
        await aya.wait("game_over", timeout=15)  # nobody answers the next prompt: the bomb ends the game
        await wait_for_game(database_url)

        ready = await server.http.get("/readyz")
        assert ready.status_code == 200 and ready.json()["checks"]["database"] is True

        game = (await query(database_url, "select mode, players_count, bots_count, duration_ms from games"))[
            0
        ]
        assert game[:3] == ("classic", 2, 0) and game[3] > 0
        players = await query(
            database_url, "select display_name, lang, is_bot, place, words from game_players order by seat"
        )
        assert sorted(players, key=lambda p: p[3]) and {(p[0], p[1], p[2]) for p in players} == {
            ("Aya", "fr", False),
            ("Ben", "ja", False),
        }
        guests = {str(row[0]) for row in await query(database_url, "select guest_id from game_players")}
        assert {g.replace("-", "") for g in guests} == {AYA.replace("-", ""), BEN.replace("-", "")}
        turns = await query(
            database_url, "select turn, fragment, outcome, word from bomb_turns order by turn"
        )
        assert turns[0][:2] == (1, turn["fragment"]) and turns[0][2:] == ("word", word)
        assert turns[-1][2] == "explosion"

        # The identifiers are private: no message sent to any player contains them.
        everything = json.dumps([aya.messages, ben.messages])
        assert AYA not in everything and BEN not in everything
        await aya.close()
        await ben.close()


async def test_a_malformed_guest_id_is_refused_and_a_missing_one_is_fine(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        code = await server.create_room()
        bad = server.client(code)
        await bad.connect()
        await bad.send(t="join", room=code, name="Zed", guest_id="not-a-uuid")
        assert (await bad.wait("error"))["code"] == "bad_message"
        await bad.close()

        anonymous = server.client(code)
        await anonymous.connect()
        snapshot = await anonymous.join(code, "Anon")  # no guest id, no language: still welcome
        assert snapshot["phase"] == "lobby"
        await anonymous.close()
