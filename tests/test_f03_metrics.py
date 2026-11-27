"""Metrics stay open in development and locked in production."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.preview import COOKIE, cookie_for, secret_matches
from voya.schema import upgrade_to_head
from voya.settings import load_settings, production_problems
from voya.store import Store


def _production(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


def test_production_refuses_to_start_without_a_metrics_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _production(monkeypatch, tmp_path)
    monkeypatch.delenv("VOYA_METRICS_TOKEN", raising=False)
    assert any("VOYA_METRICS_TOKEN" in item for item in production_problems(load_settings()))
    api_mod._state.clear()
    with pytest.raises(RuntimeError, match="VOYA_METRICS_TOKEN"), TestClient(api_mod.app):
        pass


def test_wrong_token_is_rejected_and_the_right_token_is_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _production(monkeypatch, tmp_path)
    monkeypatch.setenv("VOYA_METRICS_TOKEN", "metrics-test-token")
    monkeypatch.setenv("VOYA_DB", str(tmp_path / "t.db"))
    upgrade_to_head()
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    client = TestClient(api_mod.app)
    client.cookies.set(COOKIE, cookie_for("preview-invite-1"))
    wrong = client.get("/metrics", headers={"X-Metrics-Token": "not-the-token"})
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "METRICS_ONLY"
    short = client.get("/metrics", headers={"X-Metrics-Token": "x"})
    assert short.status_code == 401
    right = client.get("/metrics", headers={"X-Metrics-Token": "metrics-test-token"})
    assert right.status_code == 200
    assert "voya_http_requests_total" in right.text
    assert secret_matches("metrics-test-token", "metrics-test-token")
    assert not secret_matches("metrics-test-token", "x")


def test_valid_token_skips_the_invite_gate_and_a_wrong_one_does_not(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _production(monkeypatch, tmp_path)
    monkeypatch.setenv("VOYA_METRICS_TOKEN", "metrics-test-token")
    monkeypatch.setenv("VOYA_DB", str(tmp_path / "t.db"))
    upgrade_to_head()
    api_mod._state.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    client = TestClient(api_mod.app)
    blocked = client.get("/metrics", headers={"X-Metrics-Token": "not-the-token"})
    assert blocked.status_code == 401
    assert blocked.json()["error"]["code"] == "INVITE_REQUIRED"
    opened = client.get("/metrics", headers={"X-Metrics-Token": "metrics-test-token"})
    assert opened.status_code == 200


def test_development_metrics_stay_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_METRICS_TOKEN", raising=False)
    api_mod._state.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    client = TestClient(api_mod.app)
    opened = client.get("/metrics")
    assert opened.status_code == 200
    assert "voya_http_requests_total" in opened.text
