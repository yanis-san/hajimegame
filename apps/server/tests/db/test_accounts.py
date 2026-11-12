"""Accounts on a real server: sign up and in, sign out, past games following the account, deletion."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import CSRF, RunningServer, running_server
from tests.realtime.test_websocket import start_game, valid_word

PASSWORD = "correct horse battery"


def browser(server: RunningServer) -> httpx.AsyncClient:
    """A second browser: its own cookies."""
    return httpx.AsyncClient(base_url=str(server.http.base_url))


async def sign_up(
    client: httpx.AsyncClient, name: str = "Aya", guest: uuid.UUID | None = None, **extra: object
) -> httpx.Response:
    body: dict[str, object] = {"username": name, "password": PASSWORD, **extra}
    if guest is not None:
        body["guest_id"] = str(guest)
    return await client.post("/api/auth/register", json=body, headers=CSRF)


async def who(client: httpx.AsyncClient) -> object:
    return (await client.get("/api/auth/me")).json()["user"]


async def test_sign_up_signs_in_and_sign_out_signs_out(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        created = await sign_up(server.http, "Aya", email="Aya@Example.com")
        assert created.status_code == 201
        cookie = created.headers["set-cookie"].lower()
        assert (
            "httponly" in cookie
            and "samesite=lax" in cookie
            and created.headers["cache-control"] == "no-store"
        )
        assert await who(server.http) == {
            "username": "Aya",
            "email": "aya@example.com",
            "email_verified": False,
        }

        assert (await server.http.post("/api/auth/logout", headers=CSRF)).status_code == 200
        assert await who(server.http) is None


async def test_names_are_unique_whatever_the_case_and_inputs_are_checked(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        assert (await sign_up(server.http, "Aya")).status_code == 201
        assert (await sign_up(server.http, "aYA")).status_code == 409
        for name in ("ab", "a b c", "x" * 21, "salope42", "<script>"):
            response = await sign_up(server.http, name)
            assert (response.status_code, response.json()["detail"]) == (400, "bad_username"), name
        assert (await sign_up(server.http, "Ben", password="short")).json()["detail"] == "bad_password"
        assert (await sign_up(server.http, "Ben", password="Ben")).json()["detail"] == "bad_password"
        assert (await sign_up(server.http, "Ben", email="nope")).json()["detail"] == "bad_email"
        assert (await sign_up(server.http, "日本語の名前")).status_code == 201  # any script is welcome


async def test_sign_in_gives_the_same_answer_for_an_unknown_name_and_a_wrong_password(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        await sign_up(server.http, "Aya")
        other = browser(server)
        try:
            wrong = await other.post(
                "/api/auth/login", json={"username": "Aya", "password": "nope-nope"}, headers=CSRF
            )
            unknown = await other.post(
                "/api/auth/login", json={"username": "Zed", "password": "nope-nope"}, headers=CSRF
            )
            assert (
                (wrong.status_code, wrong.json())
                == (unknown.status_code, unknown.json())
                == (401, {"detail": "bad_credentials"})
            )
            assert await who(other) is None

            ok = await other.post(
                "/api/auth/login", json={"username": "aya", "password": PASSWORD}, headers=CSRF
            )
            assert ok.status_code == 200 and ok.json() == {"username": "Aya"}  # the name as it was written
            assert await who(other) == {"username": "Aya", "email": None, "email_verified": False}
        finally:
            await other.aclose()


async def test_mutations_need_the_same_site_headers(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        body = {"username": "Aya", "password": PASSWORD}
        assert (await server.http.post("/api/auth/register", json=body)).status_code == 403
        evil = {**CSRF, "Origin": "https://evil.example"}
        assert (await server.http.post("/api/auth/register", json=body, headers=evil)).status_code == 403


async def test_too_many_wrong_passwords_are_refused(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        await sign_up(server.http, "Aya")
        statuses = [
            (
                await server.http.post(
                    "/api/auth/login", json={"username": "Aya", "password": f"wrong-{n}-pass"}, headers=CSRF
                )
            ).status_code
            for n in range(12)
        ]
        assert statuses[:10] == [401] * 10 and statuses[10:] == [429, 429]
        # even the right password waits: the name is locked, not just the guess
        right = await server.http.post(
            "/api/auth/login", json={"username": "Aya", "password": PASSWORD}, headers=CSRF
        )
        assert right.status_code == 429


async def test_the_captcha_is_checked_when_a_secret_is_set(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url, turnstile_secret="secret") as server:
        response = await sign_up(server.http, "Aya", captcha="")
        assert (response.status_code, response.json()["detail"]) == (403, "captcha_failed")
        assert await who(server.http) is None


async def test_production_closes_sign_up_when_there_is_no_captcha(
    database_url: str, dictionary: Dictionary
) -> None:
    prod: dict[str, Any] = {
        "env": "prod",
        "allowed_origins": ["https://hajime.test.fr"],
        "allow_missing_origin": False,
        "cookie_secure": True,
    }
    async with running_server(dictionary, database_url=database_url, **prod) as server:
        headers = {**CSRF, "Origin": "https://hajime.test.fr"}
        response = await server.http.post(
            "/api/auth/register", json={"username": "Aya", "password": PASSWORD}, headers=headers
        )
        assert (response.status_code, response.json()["detail"]) == (503, "accounts_unavailable")


async def test_without_a_database_accounts_are_unavailable(dictionary: Dictionary) -> None:
    async with running_server(dictionary) as server:
        assert (await sign_up(server.http, "Aya")).status_code == 503
        assert await who(server.http) is None


async def play_one_game(server: RunningServer, dictionary: Dictionary, aya: uuid.UUID, ben: uuid.UUID) -> str:
    """Aya and Ben play one short game with their guest identifiers; returns the word that was played."""
    code = await server.create_room()
    first, second = server.client(code), server.client(code)
    await first.connect()
    await second.connect()
    await first.join(code, "Aya", guest_id=str(aya), lang="fr")
    await second.join(code, "Ben", guest_id=str(ben), lang="fr")
    await start_game([first, second], lives=1)
    turn = await first.wait("turn")
    word = valid_word(dictionary, turn["fragment"], set())
    active = first if turn["player_id"] == first.player_id else second
    await active.send(t="submit", text=word)
    await first.wait("game_over", timeout=15)
    return word


async def wait_for_games(
    client: httpx.AsyncClient, headers: dict[str, str] | None = None
) -> dict[str, object]:
    for _ in range(100):  # the record is written in the background
        response = await client.get("/api/me/stats/bomb", headers=headers or {})
        if response.status_code == 200 and response.json()["summary"]["games"]:
            return dict(response.json())
        await asyncio.sleep(0.05)
    raise AssertionError("the game was never recorded")


async def test_signing_up_attaches_the_games_played_as_a_guest(
    database_url: str, dictionary: Dictionary
) -> None:
    aya_guest, ben_guest, aya_phone = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with running_server(dictionary, database_url=database_url) as server:
        await play_one_game(server, dictionary, aya_guest, ben_guest)
        await wait_for_games(server.http, {"x-hajime-guest": str(aya_guest)})

        # as a guest, Aya reads her page with her browser's identifier; with nothing she is refused
        assert (await server.http.get("/api/me/stats/bomb")).status_code == 401

        await sign_up(server.http, "Aya", guest=aya_guest)
        signed_in = (await server.http.get("/api/me/stats/bomb")).json()  # no header: the account is enough
        assert signed_in["summary"]["games"] == 1

        # a second device: signing in there brings the same history, and its own games join it
        phone = browser(server)
        try:
            await phone.post(
                "/api/auth/login",
                json={"username": "Aya", "password": PASSWORD, "guest_id": str(aya_phone)},
                headers=CSRF,
            )
            assert (await phone.get("/api/me/stats/bomb")).json()["summary"]["games"] == 1
            await play_one_game(server, dictionary, aya_phone, ben_guest)
            for _ in range(100):
                if (await phone.get("/api/me/stats/bomb")).json()["summary"]["games"] == 2:
                    break
                await asyncio.sleep(0.05)
            assert (await phone.get("/api/me/stats/bomb")).json()["summary"]["games"] == 2
            assert (await server.http.get("/api/me/stats/bomb")).json()["summary"]["games"] == 2
        finally:
            await phone.aclose()


async def test_a_browser_that_belongs_to_one_account_cannot_be_claimed_by_another(
    database_url: str, dictionary: Dictionary
) -> None:
    aya_guest, ben_guest = uuid.uuid4(), uuid.uuid4()
    async with running_server(dictionary, database_url=database_url) as server:
        await play_one_game(server, dictionary, aya_guest, ben_guest)
        await wait_for_games(server.http, {"x-hajime-guest": str(aya_guest)})
        await sign_up(server.http, "Aya", guest=aya_guest)

        thief = browser(server)
        try:
            await sign_up(thief, "Mallory", guest=aya_guest)  # knows the identifier, but it is already Aya's
            assert (await thief.get("/api/me/stats/bomb")).json()["summary"]["games"] == 0
        finally:
            await thief.aclose()


async def test_deleting_the_account_signs_out_and_detaches_the_games(
    database_url: str, dictionary: Dictionary
) -> None:
    aya_guest, ben_guest = uuid.uuid4(), uuid.uuid4()
    async with running_server(dictionary, database_url=database_url) as server:
        await play_one_game(server, dictionary, aya_guest, ben_guest)
        await wait_for_games(server.http, {"x-hajime-guest": str(aya_guest)})
        await sign_up(server.http, "Aya", guest=aya_guest)

        wrong = await server.http.post("/api/auth/delete", json={"password": "nope-nope-nope"}, headers=CSRF)
        assert wrong.status_code == 401 and await who(server.http) is not None

        assert (
            await server.http.post("/api/auth/delete", json={"password": PASSWORD}, headers=CSRF)
        ).status_code == 200
        assert await who(server.http) is None
        again = await server.http.post(
            "/api/auth/login", json={"username": "Aya", "password": PASSWORD}, headers=CSRF
        )
        assert again.status_code == 401
        assert (await sign_up(server.http, "Aya")).status_code == 201  # the name is free again
        assert (await server.http.get("/api/me/stats/bomb")).json()["summary"]["games"] == 0
