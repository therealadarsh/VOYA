"""Feedback length and the privacy note about the optional contact address."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.store import Store


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_ENV", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    return TestClient(api_mod.app)


def test_feedback_rejects_more_than_1000_characters(client: TestClient) -> None:
    allowed = client.post("/v1/feedback", json={"message": "a" * 1000})
    assert allowed.status_code == 201
    blocked = client.post("/v1/feedback", json={"message": "a" * 1001, "contact": "a@example.com"})
    assert blocked.status_code == 422
    page = (Path(__file__).resolve().parents[1] / "src/voya/web/index.html").read_text(
        encoding="utf-8"
    )
    assert 'maxlength="1000"' in page
    assert "0 / 1000" in page


def test_privacy_page_mentions_the_optional_contact_address(client: TestClient) -> None:
    privacy = client.get("/privacy").text.lower()
    assert "optional contact address" in privacy
    assert "deleted" in privacy
    assert "feedback" in privacy
