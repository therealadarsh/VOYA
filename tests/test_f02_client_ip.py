"""Client address behind a proxy. A spoofed header never picks the bucket."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.client_ip import client_address
from voya.store import Store


def _app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_ENV", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    monkeypatch.setattr(api_mod, "RATE_PER_MIN", 1)


def _post(client: TestClient, forwarded: str | None = None):
    headers = {"X-Forwarded-For": forwarded} if forwarded is not None else {}
    return client.post("/v1/feedback", json={"message": "proxy check"}, headers=headers)


def test_spoofed_header_is_ignored_when_the_setting_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VOYA_TRUSTED_PROXY_IPS", raising=False)
    _app(tmp_path, monkeypatch)
    client = TestClient(api_mod.app, client=("203.0.113.8", 50000))
    assert _post(client, "198.51.100.9").status_code == 201
    assert _post(client, "198.51.100.10").status_code == 429


def test_two_clients_behind_a_trusted_proxy_get_separate_buckets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOYA_TRUSTED_PROXY_IPS", "10.0.0.5")
    _app(tmp_path, monkeypatch)
    proxy = TestClient(api_mod.app, client=("10.0.0.5", 50000))
    assert _post(proxy, "198.51.100.1").status_code == 201
    assert _post(proxy, "198.51.100.2").status_code == 201
    assert _post(proxy, "198.51.100.1").status_code == 429
    assert (
        client_address(
            peer="10.0.0.5",
            forwarded_for="198.51.100.8, 10.1.1.1",
            trusted=frozenset({"10.0.0.5", "10.1.1.1"}),
        )
        == "198.51.100.8"
    )


def test_untrusted_peer_cannot_spoof(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOYA_TRUSTED_PROXY_IPS", "10.0.0.5")
    _app(tmp_path, monkeypatch)
    attacker = TestClient(api_mod.app, client=("203.0.113.50", 50000))
    assert _post(attacker, "198.51.100.1").status_code == 201
    assert _post(attacker, "198.51.100.2").status_code == 429


def test_helper_spend_scope_uses_the_same_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VOYA_TRUSTED_PROXY_IPS", "10.0.0.5")
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    seen: dict[str, str] = {}

    def fake_respond(*_args: object, **_kwargs: object) -> dict[str, object]:
        if _args:
            seen["scope"] = str(_args[-1])
        return {"reply": "ok", "options": []}

    monkeypatch.setattr(api_mod, "respond", fake_respond)
    proxy = TestClient(api_mod.app, client=("10.0.0.5", 50000))
    created = proxy.post(
        "/v1/plans",
        json={
            "destination": "chicago",
            "start_date": "2026-11-14",
            "budget": "300",
            "firmness": "wiggle",
            "party": {"adults": 2},
            "interests": ["food"],
        },
    )
    assert created.status_code == 200
    plan_id = created.json()["plan_id"]
    helped = proxy.post(
        f"/v1/plans/{plan_id}/helper",
        json={"message": "make it cheaper"},
        headers={"X-Forwarded-For": "198.51.100.7"},
    )
    assert helped.status_code == 200
    assert seen["scope"] == "198.51.100.7"
    stranger = TestClient(api_mod.app, client=("203.0.113.9", 50000))
    stranger.post(
        f"/v1/plans/{plan_id}/helper",
        json={"message": "make it cheaper"},
        headers={"X-Forwarded-For": "198.51.100.7"},
    )
    assert seen["scope"] == "203.0.113.9"
