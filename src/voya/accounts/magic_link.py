"""Email magic-link sign-in (fake mailer in tests; dev token when configured)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from voya.store import Store


class Mailer(Protocol):
    def send_magic_link(self, email: str, url: str) -> None: ...


@dataclass
class FakeMailer:
    """Captures links in tests; never sends network mail."""

    sent: list[tuple[str, str]] = field(default_factory=list)

    def send_magic_link(self, email: str, url: str) -> None:
        self.sent.append((email, url))


def dev_mode_returns_token() -> bool:
    from voya.settings import load_settings

    return load_settings().dev_signin


@dataclass
class MagicLinkService:
    store: Store
    mailer: Mailer
    base_url: str = "http://localhost:8000"

    def request_sign_in(self, email: str, adult_attested: bool) -> dict[str, object]:
        if not adult_attested:
            return {"error": "ADULT_REQUIRED", "message": "Account holders must be 18+."}
        token = secrets.token_urlsafe(32)
        self.store.save_magic_link(
            email, token, expires=datetime.now(tz=UTC) + timedelta(minutes=30)
        )
        link = f"{self.base_url}/v1/auth/verify?token={token}"
        if dev_mode_returns_token():
            user_token = self.store.create_user(email, adult_attested)
            return {
                "token": user_token,
                "dev_mode": True,
                "note": "Development sign-in: in production this arrives as an email magic link.",
            }
        self.mailer.send_magic_link(email, link)
        return {"status": "email_sent", "message": "Check your email for a sign-in link."}

    def verify(self, token: str) -> dict[str, object] | None:
        email = self.store.consume_magic_link(token)
        if not email:
            return None
        user_token = self.store.create_user(email, True)
        return {"token": user_token}
