"""SMTP magic-link mail. Tests pass a fake SMTP factory; no network in unit tests."""

from __future__ import annotations

import smtplib
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any

from voya.accounts.magic_link import FakeMailer, Mailer
from voya.settings import Settings


def _reject_breaks(value: str, label: str) -> None:
    if "\r" in value or "\n" in value:
        raise ValueError(f"{label} contains a line break")


class SmtpMailer:
    """Sends one sign-in link per message. Credentials stay in the SMTP login call."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_addr: str,
        *,
        smtp_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self._factory = smtp_factory or smtplib.SMTP

    def send_magic_link(self, email: str, url: str) -> None:
        _reject_breaks(email, "email")
        _reject_breaks(url, "url")
        _reject_breaks(self.from_addr, "from")
        message = EmailMessage()
        message["Subject"] = "Sign in to VOYA"
        message["From"] = self.from_addr
        message["To"] = email
        message.set_content(
            "Sign in to VOYA by opening this link. It expires in 30 minutes.\n\n"
            f"{url}\n\n"
            "If you did not ask to sign in, ignore this email.\n"
        )
        with self._factory(self.host, self.port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(message)


def mailer_from_settings(settings: Settings) -> Mailer:
    if (
        settings.smtp_host
        and settings.smtp_from
        and settings.smtp_username
        and settings.smtp_password
    ):
        return SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_addr=settings.smtp_from,
        )
    return FakeMailer()
