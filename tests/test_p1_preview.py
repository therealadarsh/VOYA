"""Private preview: settings, invite gate, email sign-in, backups, safety."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Self

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.accounts.smtp_mailer import SmtpMailer
from voya.backup import backup_sqlite
from voya.log import JsonFormatter, request_path
from voya.settings import load_settings, production_problems
from voya.store import Store


def _production_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VOYA_ENV", "production")
    monkeypatch.setenv("VOYA_INVITE_CODE", "preview-invite-1")
    monkeypatch.setenv("VOYA_PUBLIC_URL", "https://preview.example")
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "0")
    monkeypatch.setenv("VOYA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOYA_SMTP_HOST", "smtp.example")
    monkeypatch.setenv("VOYA_SMTP_PORT", "587")
    monkeypatch.setenv("VOYA_SMTP_USERNAME", "voya")
    monkeypatch.setenv("VOYA_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("VOYA_SMTP_FROM", "sign-in@example.com")


def test_development_settings_do_not_require_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "1")
    settings = load_settings()
    assert settings.production is False
    assert settings.invite_required is False
    assert settings.dev_signin is True
    assert settings.preview_label is True
    assert production_problems(settings) == []


def test_production_settings_name_each_missing_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOYA_ENV", "production")
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_PUBLIC_URL", raising=False)
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "1")
    monkeypatch.delenv("VOYA_DATA_DIR", raising=False)
    monkeypatch.delenv("VOYA_SMTP_HOST", raising=False)
    monkeypatch.delenv("VOYA_SMTP_FROM", raising=False)
    text = "\n".join(production_problems(load_settings()))
    assert "VOYA_INVITE_CODE" in text
    assert "VOYA_PUBLIC_URL" in text
    assert "VOYA_DEV_SIGNIN" in text
    assert "VOYA_DATA_DIR" in text
    assert "VOYA_SMTP_HOST" in text
    assert "VOYA_SMTP_FROM" in text


def test_production_settings_accept_a_complete_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _production_env(monkeypatch, tmp_path)
    settings = load_settings()
    assert production_problems(settings) == []
    assert settings.invite_required is True
    assert settings.dev_signin is False
    assert settings.data_dir == tmp_path
    assert settings.public_url == "https://preview.example"


def test_short_invite_code_is_not_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _production_env(monkeypatch, tmp_path)
    monkeypatch.setenv("VOYA_INVITE_CODE", "short")
    assert any("VOYA_INVITE_CODE" in item for item in production_problems(load_settings()))


def test_store_uses_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VOYA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("VOYA_DB", raising=False)
    store = Store()
    assert Path(store.path) == tmp_path / "voya.db"
    store.ping()


def test_backup_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "voya.db"
    store = Store(str(db))
    store.add_feedback("The range bar is hard to see", "a@example.com")
    dest = backup_sqlite(db, tmp_path / "backups", now=datetime(2026, 11, 13, 5, 30, tzinfo=UTC))
    assert dest.name == "voya-20261113T053000Z.db"
    restored = Store(str(dest))
    rows = restored.feedback_all()
    assert rows[0]["message"] == "The range bar is hard to see"
    assert rows[0]["contact"] == "a@example.com"


class _FakeSMTP:
    last: _FakeSMTP | None = None

    def __init__(self, host: str, port: int, timeout: float | None = None) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sent: list[EmailMessage] = []
        self.logged: tuple[str, str] | None = None
        _FakeSMTP.last = self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        self.logged = (user, password)

    def send_message(self, message: EmailMessage) -> None:
        self.sent.append(message)


def test_smtp_mailer_sends_the_link_without_opening_a_socket() -> None:
    mailer = SmtpMailer(
        host="smtp.example",
        port=587,
        username="voya",
        password="secret",
        from_addr="sign-in@example.com",
        smtp_factory=_FakeSMTP,
    )
    mailer.send_magic_link("a@example.com", "https://preview.example/v1/auth/verify?token=abc")
    sent = _FakeSMTP.last
    assert sent is not None
    assert sent.logged == ("voya", "secret")
    message = sent.sent[0]
    assert message["To"] == "a@example.com"
    assert message["From"] == "sign-in@example.com"
    assert "token=abc" in message.get_content()
    assert "est." not in message.get_content()


def test_smtp_mailer_rejects_header_injection() -> None:
    mailer = SmtpMailer(
        host="smtp.example",
        port=587,
        username=None,
        password=None,
        from_addr="sign-in@example.com",
        smtp_factory=_FakeSMTP,
    )
    with pytest.raises(ValueError):
        mailer.send_magic_link("a@example.com\nBcc: x@evil.example", "https://preview.example/x")


def test_request_path_drops_the_query() -> None:
    assert request_path("/v1/auth/verify?token=secret") == "/v1/auth/verify"


def test_json_log_has_no_query_string() -> None:
    record = logging.LogRecord(
        name="voya.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request",
        args=(),
        exc_info=None,
    )
    record.method = "GET"  # type: ignore[attr-defined]
    record.path = "/healthz"  # type: ignore[attr-defined]
    record.status_code = 200  # type: ignore[attr-defined]
    record.trace_id = "tr_1"  # type: ignore[attr-defined]
    record.duration_ms = 3  # type: ignore[attr-defined]
    line = JsonFormatter().format(record)
    assert '"path": "/healthz"' in line
    assert "token" not in line


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    return TestClient(api_mod.app)


def test_security_headers_on_health(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in response.headers


def test_readyz_pings_the_database(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_hsts_when_production(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _production_env(monkeypatch, tmp_path)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    with TestClient(api_mod.app) as prod:
        response = prod.get("/healthz")
    assert "max-age=" in response.headers["Strict-Transport-Security"]


def test_invite_gate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VOYA_INVITE_CODE", "preview-invite-1")
    monkeypatch.delenv("VOYA_ENV", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    gate = TestClient(api_mod.app)
    blocked = gate.get("/v1/meta")
    assert blocked.status_code == 401
    assert blocked.json()["error"]["code"] == "INVITE_REQUIRED"
    page = gate.get("/")
    assert "Invite code" in page.text
    assert gate.get("/privacy").status_code == 200
    assert gate.get("/terms").status_code == 200
    assert gate.get("/healthz").status_code == 200
    foreign = gate.post(
        "/v1/preview/unlock",
        json={"code": "preview-invite-1"},
        headers={"Origin": "https://evil.example"},
    )
    assert foreign.status_code == 403
    bad = gate.post("/v1/preview/unlock", json={"code": "wrong-code-1"})
    assert bad.status_code == 401
    ok = gate.post("/v1/preview/unlock", json={"code": "preview-invite-1"})
    assert ok.status_code == 200
    assert "voya_preview" in ok.headers["set-cookie"].lower() or "voya_preview" in ok.cookies
    cookie = ok.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" not in cookie
    assert gate.get("/v1/meta").status_code == 200


def test_preview_pages_and_feedback(client: TestClient) -> None:
    home = client.get("/")
    assert "Preview" in home.text
    assert "Feedback" in home.text
    assert 'href="/privacy"' in home.text
    assert 'href="/terms"' in home.text
    meta = client.get("/v1/meta").json()
    assert meta["preview"] is True
    privacy = client.get("/privacy").text
    terms = client.get("/terms").text
    assert "Draft" in privacy
    assert "Draft" in terms
    assert "not a privacy policy" in privacy.lower()
    assert "not terms of service" in terms.lower()
    saved = client.post(
        "/v1/feedback",
        json={"message": "Preview label is easy to miss", "contact": "a@example.com"},
    )
    assert saved.status_code == 201
    rows = api_mod.store().feedback_all()
    assert rows[0]["message"] == "Preview label is easy to miss"
    empty = client.post("/v1/feedback", json={"message": "   "})
    assert empty.status_code == 422


def test_dev_sign_in_still_returns_a_token(client: TestClient) -> None:
    started = client.post(
        "/v1/auth/start", json={"email": "a@example.com", "is_adult": True}
    ).json()
    assert started["token"]
    assert started["dev_mode"] is True


def test_email_sign_in_page_stores_the_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "0")
    monkeypatch.setenv("VOYA_PUBLIC_URL", "http://localhost:8000")
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    from voya.accounts.magic_link import FakeMailer

    api_mod._state["mailer"] = FakeMailer()
    web = TestClient(api_mod.app)
    started = web.post("/v1/auth/start", json={"email": "a@example.com", "is_adult": True})
    assert started.status_code == 200
    assert "token" not in started.json()
    _email, url = api_mod._state["mailer"].sent[0]
    token = url.split("token=")[-1]
    html = web.get("/v1/auth/verify", params={"token": token}, headers={"Accept": "text/html"})
    assert html.status_code == 200
    found = re.search(r'name="voya-token" content="([^"]+)"', html.text)
    assert found is not None
    session = found.group(1)
    assert session and session != token
    api_json = web.get("/v1/auth/verify", params={"token": "not-a-real-token"})
    assert api_json.status_code == 400


def test_production_refuses_to_start_when_settings_are_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOYA_ENV", "production")
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_SMTP_HOST", raising=False)
    api_mod._state.clear()
    with pytest.raises(RuntimeError, match="VOYA_INVITE_CODE"), TestClient(api_mod.app):
        pass
