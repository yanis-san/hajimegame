"""Confirming an e-mail address: the message, the link, its limits, and a mail server that fails."""

from __future__ import annotations

import asyncio
import re
import socket
import uuid
import warnings
from datetime import datetime, timedelta
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db import accounts
from app.japanese.dictionary import Dictionary
from app.mail import SmtpMailer
from tests.db.test_accounts import PASSWORD, sign_up, who
from tests.realtime.helpers import CSRF, running_server

SITE = "https://hajime.test"
SETTINGS: dict[str, Any] = {"public_url": SITE}


class Outbox:
    """A mailer that keeps what it was asked to send, and can be told to fail."""

    def __init__(self, fail: bool = False) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.fail = fail

    async def send(self, to: str, subject: str, body: str) -> None:
        if self.fail:
            raise ConnectionRefusedError("the mail server is down")
        self.sent.append((to, subject, body))

    async def wait_for(self, count: int) -> None:
        for _ in range(200):  # the message is sent in the background
            if len(self.sent) >= count:
                return
            await asyncio.sleep(0.02)
        raise AssertionError(f"expected {count} message(s), got {len(self.sent)}")

    def token(self, index: int = -1) -> str:
        match = re.search(r"/verify\?token=([\w-]+)", self.sent[index][2])
        assert match, self.sent[index][2]
        return match.group(1)


async def verify(client: httpx.AsyncClient, token: str) -> httpx.Response:
    return await client.post("/api/auth/verify", json={"token": token}, headers=CSRF)


async def resend(client: httpx.AsyncClient, lang: str = "fr") -> httpx.Response:
    return await client.post("/api/auth/verify/resend", json={"lang": lang}, headers=CSRF)


async def confirmed(client: httpx.AsyncClient) -> object:
    return ((await who(client)) or {}).get("email_verified")  # type: ignore[attr-defined]


async def player_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.connect() as connection:
        return uuid.UUID(str((await connection.execute(sa.text("select player_id from accounts"))).scalar()))


async def test_signing_up_sends_one_message_with_a_link_that_confirms_the_address(
    database_url: str, dictionary: Dictionary
) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        assert (await sign_up(server.http, "Aya", email="aya@example.com")).status_code == 201
        await outbox.wait_for(1)
        to, subject, body = outbox.sent[0]
        assert to == "aya@example.com" and "Confirme ton email" in subject and "Bonjour Aya" in body
        assert f"{SITE}/verify?token=" in body  # French: the bare address
        assert await confirmed(server.http) is False  # not confirmed yet

        done = await verify(server.http, outbox.token())
        assert (done.status_code, done.json()) == (200, {"verified": True})
        assert await confirmed(server.http) is True


async def test_the_message_and_its_link_speak_the_language_of_the_page(
    database_url: str, dictionary: Dictionary
) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya", lang="en")
        await outbox.wait_for(1)
        assert "Confirm your email" in outbox.sent[0][1] and f"{SITE}/en/verify?token=" in outbox.sent[0][2]
        other = httpx.AsyncClient(base_url=str(server.http.base_url))
        try:
            await sign_up(other, "Ben", lang="ja")
            await outbox.wait_for(2)
            assert "メールアドレスの確認" in outbox.sent[1][1]
            assert f"{SITE}/ja/verify?token=" in outbox.sent[1][2]
            await sign_up(other, "Cleo", lang="xx")  # an unknown language falls back to French
            await outbox.wait_for(3)
            assert "Confirme ton email" in outbox.sent[2][1]
        finally:
            await other.aclose()


async def test_a_link_works_once_and_a_wrong_or_expired_one_does_nothing(
    database_url: str, dictionary: Dictionary
) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya")
        await outbox.wait_for(1)
        token = outbox.token()
        assert (await verify(server.http, "not-a-token")).json() == {"detail": "bad_token"}
        assert (await verify(server.http, "")).status_code == 400
        assert (await verify(server.http, token)).status_code == 200
        again = await verify(server.http, token)
        assert (again.status_code, again.json()) == (400, {"detail": "bad_token"})  # used: once only

        # an expired link: a fresh secret whose time has run out
        engine = create_async_engine(database_url)
        async with engine.begin() as connection:
            await connection.execute(sa.text("update accounts set email_verified_at = null"))
        stale = await accounts.issue_email_token(engine, await player_id(engine), "aya@example.com", 24)
        async with engine.begin() as connection:
            await connection.execute(
                sa.text("update email_tokens set expires_at = :t"),
                {"t": datetime.now() - timedelta(minutes=1)},
            )
        await engine.dispose()
        assert (await verify(server.http, stale)).status_code == 400
        assert await confirmed(server.http) is False


async def test_only_the_hash_of_the_secret_is_stored(database_url: str, dictionary: Dictionary) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya")
        await outbox.wait_for(1)
        engine = create_async_engine(database_url)
        async with engine.connect() as connection:
            stored = (
                (await connection.execute(sa.text("select token_hash from email_tokens"))).scalars().all()
            )
        await engine.dispose()
        assert len(stored) == 1 and stored[0] != outbox.token() and len(stored[0]) == 64


async def test_a_link_for_an_address_that_has_since_changed_confirms_nothing(
    database_url: str, dictionary: Dictionary
) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya", email="old@example.com")
        await outbox.wait_for(1)
        engine = create_async_engine(database_url)
        async with engine.begin() as connection:
            await connection.execute(sa.text("update accounts set email = 'new@example.com'"))
        await engine.dispose()
        assert (await verify(server.http, outbox.token())).status_code == 400
        assert await confirmed(server.http) is False


async def test_resending_replaces_the_link(database_url: str, dictionary: Dictionary) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        assert (await resend(server.http)).status_code == 401  # nobody is signed in
        await sign_up(server.http, "Aya")
        await outbox.wait_for(1)
        first = outbox.token()
        assert (await resend(server.http, "en")).status_code == 202
        await outbox.wait_for(2)
        assert "Confirm your email" in outbox.sent[1][1]
        assert (await verify(server.http, first)).status_code == 400  # the earlier link stopped working
        assert (await verify(server.http, outbox.token())).status_code == 200
        assert (await resend(server.http)).status_code == 409  # confirmed: nothing to send


async def test_asking_again_too_often_is_refused(database_url: str, dictionary: Dictionary) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya")
        statuses = [(await resend(server.http)).status_code for _ in range(5)]
        assert statuses == [202, 202, 202, 429, 429]


async def test_a_mail_server_that_fails_never_breaks_the_sign_up(
    database_url: str, dictionary: Dictionary
) -> None:
    outbox = Outbox(fail=True)
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        created = await sign_up(server.http, "Aya")
        assert created.status_code == 201  # the account exists whatever the mail server does
        await asyncio.sleep(0.2)
        assert ((await who(server.http)) or {}).get("username") == "Aya"  # type: ignore[attr-defined]
        outbox.fail = False
        assert (await resend(server.http)).status_code == 202  # and another message can be asked for
        await outbox.wait_for(1)


async def test_without_a_mail_server_accounts_still_work_and_resending_says_so(
    database_url: str, dictionary: Dictionary
) -> None:
    async with running_server(dictionary, database_url=database_url) as server:
        assert (await sign_up(server.http, "Aya")).status_code == 201
        refused = await resend(server.http)
        assert (refused.status_code, refused.json()) == (503, {"detail": "email_unavailable"})


async def test_deleting_the_account_deletes_its_links(database_url: str, dictionary: Dictionary) -> None:
    outbox = Outbox()
    async with running_server(dictionary, database_url=database_url, mailer=outbox, **SETTINGS) as server:
        await sign_up(server.http, "Aya")
        await outbox.wait_for(1)
        gone = await server.http.post("/api/auth/delete", json={"password": PASSWORD}, headers=CSRF)
        assert gone.status_code == 200
        engine = create_async_engine(database_url)
        async with engine.connect() as connection:
            assert (await connection.execute(sa.text("select count(*) from email_tokens"))).scalar() == 0
        await engine.dispose()
        assert (await verify(server.http, outbox.token())).status_code == 400


# --- the real SMTP implementation, against a local mail server ----------------------------------------


class Inbox:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def handle_DATA(self, server: Any, session: Any, envelope: Any) -> str:
        self.messages.append(envelope)
        return "250 OK"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def local_mail_server(inbox: Inbox, authenticator: Any) -> tuple[Controller, int]:
    port = free_port()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # plain AUTH on a local test server only
        controller = Controller(
            inbox,
            hostname="127.0.0.1",
            port=port,
            authenticator=authenticator,
            auth_required=True,
            auth_require_tls=False,
        )
    controller.start()
    return controller, port


async def test_the_smtp_mailer_logs_in_and_delivers_a_utf8_message() -> None:
    inbox = Inbox()
    logins: list[tuple[Any, Any]] = []

    def authenticate(server: Any, session: Any, envelope: Any, mechanism: str, data: Any) -> AuthResult:
        logins.append((data.login, data.password))
        return AuthResult(success=True)

    controller, port = local_mail_server(inbox, authenticate)
    try:
        mailer = SmtpMailer("127.0.0.1", port, "contact@example.org", "s3cret", "contact@example.org", "none")
        await mailer.send(
            "aya@example.com", "Confirme ton email · Bakahatsu", "こんにちは — accents : é à ü\n"
        )
    finally:
        controller.stop()
    assert logins == [(b"contact@example.org", b"s3cret")]
    assert len(inbox.messages) == 1
    envelope = inbox.messages[0]
    assert envelope.rcpt_tos == ["aya@example.com"]
    raw = envelope.content.decode("utf-8")
    assert "From: Bakahatsu <contact@example.org>" in raw and "Auto-Submitted: auto-generated" in raw


async def test_the_smtp_mailer_reports_a_refused_login() -> None:
    def refuse(server: Any, session: Any, envelope: Any, mechanism: str, data: Any) -> AuthResult:
        return AuthResult(success=False, handled=False)

    controller, port = local_mail_server(Inbox(), refuse)
    try:
        mailer = SmtpMailer("127.0.0.1", port, "contact@example.org", "wrong", "contact@example.org", "none")
        with pytest.raises(Exception, match=r"(?i)authentication"):
            await mailer.send("aya@example.com", "x", "y")
    finally:
        controller.stop()
