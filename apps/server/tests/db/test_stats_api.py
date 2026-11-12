"""`GET /api/me/stats/bomb` on a real server: a game is played, then each player reads their own."""

from __future__ import annotations

import asyncio
import uuid

from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import running_server
from tests.realtime.test_websocket import start_game, valid_word

AYA = str(uuid.uuid4())
BEN = str(uuid.uuid4())


async def test_each_player_reads_their_own_words_and_nobody_elses(
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

        turn = await aya.wait("turn")
        word = valid_word(dictionary, turn["fragment"], set())
        active, other_guest = (aya, BEN) if turn["player_id"] == aya.player_id else (ben, AYA)
        mine, theirs = (AYA, BEN) if active is aya else (BEN, AYA)
        await active.send(t="submit", text=word)
        await aya.wait("accepted")
        await aya.wait("game_over", timeout=15)
        for _ in range(100):  # the record is written in the background
            response = await server.http.get("/api/me/stats/bomb", headers={"x-hajime-guest": mine})
            if response.json()["summary"]["games"]:
                break
            await asyncio.sleep(0.05)

        stats = response.json()
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert stats["mode"] == "all"
        assert stats["summary"]["games"] == 1 and stats["summary"]["words"] == 1
        assert [w["word"] for w in stats["top_words"]] == [word]
        assert stats["top_words"][0]["reading"] and stats["top_words"][0]["count"] == 1
        assert stats["recent_words"][0]["word"] == word and stats["recent_words"][0]["mode"] == "classic"
        assert len(stats["activity"]) == 30 and stats["activity"][-1]["games"] == 1

        # the other player did not submit that word: their page holds none of it
        other = (await server.http.get("/api/me/stats/bomb", headers={"x-hajime-guest": theirs})).json()
        assert other["summary"]["games"] == 1 and other["summary"]["words"] == 0
        assert other["top_words"] == [] and other["recent_words"] == []
        assert other_guest == theirs

        # the mode filter: this was a classic game
        shiritori = (
            await server.http.get("/api/me/stats/bomb?mode=shiritori", headers={"x-hajime-guest": mine})
        ).json()
        assert shiritori["summary"]["games"] == 0 and shiritori["top_words"] == []
        await aya.close()
        await ben.close()


async def test_the_endpoint_checks_who_is_asking(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        assert (await server.http.get("/api/me/stats/bomb")).status_code == 401  # no identifier
        bad = await server.http.get("/api/me/stats/bomb", headers={"x-hajime-guest": "not-a-uuid"})
        assert bad.status_code == 400 and bad.json()["detail"] == "bad_guest"
        wrong_mode = await server.http.get("/api/me/stats/bomb?mode=zzz", headers={"x-hajime-guest": AYA})
        assert wrong_mode.status_code == 422
        unknown = await server.http.get("/api/me/stats/bomb", headers={"x-hajime-guest": str(uuid.uuid4())})
        assert (
            unknown.status_code == 200 and unknown.json()["summary"]["games"] == 0
        )  # a stranger sees nothing


async def test_an_unknown_game_has_no_statistics(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        response = await server.http.get("/api/me/stats/chess", headers={"x-hajime-guest": AYA})
        assert response.status_code == 404 and response.json()["detail"] == "unknown_game"


async def test_it_is_rate_limited(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        headers = {"x-hajime-guest": AYA}
        codes = [
            (await server.http.get("/api/me/stats/bomb", headers=headers)).status_code for _ in range(32)
        ]
        assert codes[:30] == [200] * 30 and codes[30:] == [429, 429]


async def test_without_a_database_the_endpoint_says_so(dictionary: Dictionary) -> None:
    async with running_server(dictionary) as server:  # no database_url
        response = await server.http.get("/api/me/stats/bomb", headers={"x-hajime-guest": AYA})
        assert response.status_code == 503 and response.json()["detail"] == "stats_unavailable"
