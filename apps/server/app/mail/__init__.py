"""Sending e-mail: a small interface, the SMTP implementation, and the messages themselves.

Nothing in the game waits for a mail: a message is sent in the background, and a failure is logged and
counted, never shown as an error to the player (who can ask for another one)."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Literal, Protocol

from app.core import metrics
from app.core.config import AppSettings
from app.core.logging import get_logger

log = get_logger("mail")

Security = Literal["ssl", "starttls", "none"]


class Mailer(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text message. Raises when it could not be handed to the mail server."""
        ...


class SmtpMailer:
    """Sends through an SMTP server with a login (for example the site's own mailbox)."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        security: Security = "ssl",
        site_name: str = "Bakahatsu",
        timeout: float = 20.0,
    ) -> None:
        self._host, self._port, self._user, self._password = host, port, user, password
        self._sender, self._security, self._site_name, self._timeout = sender, security, site_name, timeout

    async def send(self, to: str, subject: str, body: str) -> None:
        await asyncio.to_thread(self._send_blocking, to, subject, body)

    def _message(self, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = f"{self._site_name} <{self._sender}>"
        message["To"] = to
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain=self._sender.rpartition("@")[2])
        message["Auto-Submitted"] = "auto-generated"  # a robot wrote it: no out-of-office replies
        message.set_content(body, charset="utf-8")
        return message

    def _send_blocking(self, to: str, subject: str, body: str) -> None:
        message = self._message(to, subject, body)
        context = ssl.create_default_context()
        if self._security == "ssl":
            with smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context) as smtp:
                smtp.login(self._user, self._password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._security == "starttls":
                smtp.starttls(context=context)
            smtp.login(self._user, self._password)
            smtp.send_message(message)


def build_mailer(settings: AppSettings) -> Mailer | None:
    """The mailer the settings describe, or None when no mail server is configured (then nothing is sent)."""
    if not settings.email_enabled:
        return None
    assert settings.smtp_host and settings.smtp_user and settings.smtp_password  # checked by the settings
    return SmtpMailer(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password,
        settings.smtp_from or settings.smtp_user,
        settings.smtp_security,
    )


async def deliver(mailer: Mailer, kind: str, to: str, subject: str, body: str) -> bool:
    """Send one message in the background's name: never raises, counts and logs the outcome."""
    try:
        await mailer.send(to, subject, body)
    except Exception as exc:  # a mail server can fail in many ways: none may reach the player's request
        metrics.EMAILS.labels(kind, "failed").inc()
        log.warning("email_failed", kind=kind, error=type(exc).__name__)
        return False
    metrics.EMAILS.labels(kind, "sent").inc()
    return True
