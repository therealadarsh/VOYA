"""Sign-in email limits. The counter stores a hash, never the address."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.accounts.magic_link import FakeMailer
from voya.store import Store

ADDRESS = "Person@Example.com"


def _client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, dev_signin: str = "1"
) -> TestClient:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.setenv("VOYA_DEV_SIGNIN", dev_signin)
    monkeypatch.setenv("VOYA_SIGNIN_MAX_PER_15MIN", "3")
    monkeypatch.setenv("VOYA_SIGNIN_MAX_PER_DAY", "10")
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    api_mod._state["mailer"] = FakeMailer()
    return TestClient(api_mod.app)


def _post(client: TestClient, email: str = ADDRESS):
    return client.post("/v1/auth/start", json={"email": email, "is_adult": True})


def _seed(store: Store, email: str, when: datetime, count: int) -> None:
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    stamp = when.astimezone(UTC).isoformat(timespec="seconds")
    with store.tx() as cursor:
        for _ in range(count):
            cursor.execute(
                "INSERT INTO signin_attempts (email_hash, attempted_at) VALUES (?,?)",
                (digest, stamp),
            )


def test_under_the_limit_sends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    first = _post(client)
    second = _post(client)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["token"]
    assert len(api_mod.store().signin_attempt_rows()) == 2


def test_fifteen_minute_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _client(tmp_path, monkeypatch, dev_signin="0")
    caplog.set_level(logging.DEBUG)
    codes = [_post(client).status_code for _ in range(3)]
    assert codes == [200, 200, 200]
    blocked = _post(client)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "SIGNIN_LIMIT"
    assert ADDRESS.lower() not in blocked.text.lower()
    mailer = api_mod._state["mailer"]
    assert isinstance(mailer, FakeMailer)
    assert len(mailer.sent) == 3
    again = _post(client)
    assert again.status_code == 429
    assert len(mailer.sent) == 3
    assert ADDRESS.lower() not in caplog.text.lower()


def test_daily_limit_counts_older_attempts_outside_the_15_minute_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    store = api_mod.store()
    _seed(store, ADDRESS, datetime.now(UTC) - timedelta(hours=2), 10)
    blocked = _post(client)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "SIGNIN_LIMIT"
    assert len(store.signin_attempt_rows()) == 10


def test_daily_window_still_allows_a_new_email_when_under_both_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    store = api_mod.store()
    _seed(store, ADDRESS, datetime.now(UTC) - timedelta(hours=2), 9)
    allowed = _post(client)
    assert allowed.status_code == 200
    assert len(store.signin_attempt_rows()) == 10


def test_limit_is_case_insensitive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    assert _post(client, "Person@Example.com").status_code == 200
    assert _post(client, "person@example.com").status_code == 200
    assert _post(client, "PERSON@example.com").status_code == 200
    blocked = _post(client, "person@EXAMPLE.com")
    assert blocked.status_code == 429
    rows = api_mod.store().signin_attempt_rows()
    assert len(rows) == 3
    only = {row["email_hash"] for row in rows}
    assert only == {hashlib.sha256(b"person@example.com").hexdigest()}


def test_counter_and_logs_omit_the_plain_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _client(tmp_path, monkeypatch)
    caplog.set_level(logging.DEBUG)
    assert _post(client).status_code == 200
    rows = api_mod.store().signin_attempt_rows()
    assert rows
    blob = " ".join(f"{key}={value}" for row in rows for key, value in row.items())
    assert "email_hash" in blob
    assert ADDRESS.lower() not in blob.lower()
    assert "example.com" not in blob.lower()
    assert ADDRESS.lower() not in caplog.text.lower()
    with api_mod.store().tx() as cursor:
        schema = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE name='signin_attempts'"
        ).fetchone()
    assert schema is not None
    assert "email " not in str(schema["sql"]).lower()
