"""The operator's admin: closed unless configured, one login, read-only history, nothing secret on screen."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from argon2 import PasswordHasher
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import AppSettings
from app.db.games.bomb import BombTurn
from app.db.models import Game, GamePlayer
from app.japanese.dictionary import Dictionary
from tests.realtime.helpers import CSRF, running_server

PASSWORD = "a long operator password"
SECRET = "s" * 40
ADMIN: dict[str, Any] = {
    "admin_password_hash": PasswordHasher().hash(PASSWORD),
    "admin_secret": SECRET,
    "admin_username": "boss",
}
LISTS = (
    "player",
    "account",
    "login-session",
    "game",
    "game-player",
    "bomb-turn",
    "season",
    "group",
    "group-member",
    "challenge",
)


async def log_in(
    client: httpx.AsyncClient, password: str = PASSWORD, username: str = "boss"
) -> httpx.Response:
    return await client.post("/admin/login", data={"username": username, "password": password})


async def test_the_admin_does_not_exist_unless_it_is_configured(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        assert (await server.http.get("/admin/")).status_code == 404
        assert (await server.http.get("/admin/login")).status_code == 404


async def test_every_page_asks_for_the_login_first(database_url: str, dictionary: Dictionary) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        for page in ("", *(f"{name}/list" for name in LISTS)):
            response = await server.http.get(f"/admin/{page}")
            assert response.status_code in (302, 303, 307), page
            assert response.headers["location"].endswith("/admin/login"), page


async def test_a_wrong_password_or_name_does_not_get_in_and_the_right_one_does(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        wrong_password = await log_in(server.http, "not the password")
        wrong_name = await log_in(server.http, PASSWORD, username="admin")
        assert wrong_password.status_code == wrong_name.status_code == 400
        assert (await server.http.get("/admin/", follow_redirects=False)).status_code in (302, 303, 307)

        ok = await log_in(server.http)
        assert ok.status_code in (302, 303)
        cookie = ok.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie
        assert (await server.http.get("/admin/")).status_code == 200
        for name in LISTS:
            assert (await server.http.get(f"/admin/{name}/list")).status_code == 200, name

        await server.http.get("/admin/logout")
        assert (await server.http.get("/admin/", follow_redirects=False)).status_code in (302, 303, 307)


async def test_guessing_is_stopped_even_for_the_right_password(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        for _ in range(5):
            assert (await log_in(server.http, "wrong wrong wrong")).status_code == 400
        assert (await log_in(server.http)).status_code == 400  # locked: the right password waits too
        assert (await server.http.get("/admin/", follow_redirects=False)).status_code in (302, 303, 307)


async def test_history_is_read_only_and_games_can_be_removed(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        await log_in(server.http)
        for name in ("game-player", "bomb-turn", "game"):
            assert (await server.http.get(f"/admin/{name}/create")).status_code == 403, name
        assert (await server.http.get("/admin/player/create")).status_code == 403
        assert (await server.http.get("/admin/account/create")).status_code == 403


async def test_no_password_hash_or_token_ever_reaches_the_screen(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        born = date.today().replace(year=date.today().year - 31)
        body = {
            "username": "Aya",
            "password": "correct horse battery",
            "email": "aya@example.com",
            "birth_date": born.isoformat(),
            "guest_id": str(uuid.uuid4()),
        }
        created = await server.http.post("/api/auth/register", json=body, headers=CSRF)
        assert created.status_code == 201
        await log_in(server.http)

        listing = (await server.http.get("/admin/account/list")).text
        assert "aya" in listing
        assert re.search(r">\s*31\s*<", listing), "the age, computed from the date of birth, is listed"
        assert born.isoformat() in listing
        pages = [listing, (await server.http.get("/admin/login-session/list")).text]
        details = [link for page in pages[:1] for link in _links(page, "/admin/account/details/")]
        assert details, "the account list links to its detail page"
        pages.append((await server.http.get(details[0])).text)
        for page in pages:
            assert "$argon2" not in page and "password_hash" not in page and "token_hash" not in page


def _links(html: str, prefix: str) -> list[str]:
    import re

    return sorted(set(re.findall(rf'href="[^"]*?({re.escape(prefix)}[^"]+)"', html)))


async def test_the_admin_pages_have_their_own_policy_and_the_game_keeps_the_strict_one(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        await log_in(server.http)
        admin_csp = (await server.http.get("/admin/")).headers["content-security-policy"]
        assert "script-src 'self'" in admin_csp and "frame-ancestors 'none'" in admin_csp
        game_csp = (await server.http.get("/healthz")).headers["content-security-policy"]
        assert game_csp == "default-src 'none'; frame-ancestors 'none'"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"admin_secret": "short"}, "at least 32"),
        ({"admin_secret": None}, "at least 32"),
        ({"admin_password_hash": "plain-text-password"}, "Argon2"),
        ({"admin_path": "Admin Panel"}, "HAJIME_ADMIN_PATH"),
        ({"database_url": None}, "needs HAJIME_DATABASE_URL"),
    ],
)
def test_an_unsafe_admin_configuration_does_not_start(override: dict[str, Any], message: str) -> None:
    good: dict[str, Any] = {**ADMIN, "database_url": "sqlite+aiosqlite:///x.db"}
    with pytest.raises(ValidationError, match=message):
        AppSettings(**{**good, **override})


async def test_deleting_a_game_takes_its_seats_and_turns_with_it(
    database_url: str, dictionary: Dictionary
) -> None:
    now = datetime.now()
    kept, removed = uuid.uuid4(), uuid.uuid4()
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        for game_id in (kept, removed):
            await connection.execute(
                sa.insert(Game).values(
                    id=game_id,
                    kind="bomb",
                    mode="classic",
                    room_code="ROOM",
                    settings={},
                    started_at=now,
                    ended_at=now,
                )
            )
            await connection.execute(
                sa.insert(GamePlayer).values(
                    game_id=game_id, seat=0, display_name="Aya", place=1, score=1, words=1, longest_word=""
                )
            )
            await connection.execute(
                sa.insert(BombTurn).values(
                    game_id=game_id,
                    turn=0,
                    seat=0,
                    fragment="さ",
                    outcome="word",
                    word="さくら",
                    reading="さくら",
                )
            )

    async with running_server(dictionary, database_url=database_url, **ADMIN) as server:
        await log_in(server.http)
        response = await server.http.request("DELETE", f"/admin/game/delete?pks={removed}")
        assert response.status_code == 200

    async with engine.connect() as connection:
        for table in (Game, GamePlayer, BombTurn):
            left = (await connection.execute(sa.select(sa.func.count()).select_from(table))).scalar()
            assert left == 1, table.__tablename__  # only the game that was not deleted remains
    await engine.dispose()


async def test_the_admin_can_live_at_a_secret_address(database_url: str, dictionary: Dictionary) -> None:
    secret = f"/admin-{uuid.uuid4()}"
    async with running_server(dictionary, database_url=database_url, admin_path=secret, **ADMIN) as server:
        assert (await server.http.get(f"{secret}/login")).status_code == 200
        assert (await server.http.get("/admin/login")).status_code == 404  # the usual address is nothing
        login = await server.http.post(f"{secret}/login", data={"username": "boss", "password": PASSWORD})
        assert login.status_code in (302, 303)
        assert (await server.http.get(f"{secret}/")).status_code == 200
        assert (await server.http.get(f"{secret}/game/list")).status_code == 200
        csp = (await server.http.get(f"{secret}/")).headers["content-security-policy"]
        assert "script-src 'self'" in csp  # the admin's own page policy follows the address
