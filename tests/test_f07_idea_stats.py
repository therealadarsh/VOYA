"""Anonymous idea counters: shown, swapped, and kept. No identity columns."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.store import Store

_BODY = {
    "destination": "new-york",
    "start_date": "2026-11-14",
    "budget": "400",
    "firmness": "wiggle",
    "party": {"adults": 1},
    "interests": ["food"],
    "days": 1,
}


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "1")
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    return TestClient(api_mod.app)


def _row(store: Store, option_id: str) -> dict[str, int]:
    found = [row for row in store.idea_stat_rows() if row["option_id"] == option_id]
    assert found
    return found[0]


def test_shown_swapped_and_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/v1/plans", json=_BODY).json()
    plan_id = created["plan_id"]
    first = {slot["slot"]: slot["id"] for slot in created["ideas"]["days"][0]["slots"]}
    store = api_mod.store()
    for option_id in first.values():
        assert _row(store, option_id)["shown"] == 1
        assert _row(store, option_id)["swapped"] == 0
        assert _row(store, option_id)["kept"] == 0
    moved = client.post(f"/v1/plans/{plan_id}/ideas/1/morning/another").json()
    morning = next(slot for slot in moved["ideas"]["days"][0]["slots"] if slot["slot"] == "morning")
    assert _row(store, first["morning"])["swapped"] == 1
    assert _row(store, morning["id"])["shown"] == 1
    token = client.post(
        "/v1/auth/start", json={"email": "ideas@example.com", "is_adult": True}
    ).json()["token"]
    saved = client.post(f"/v1/plans/{plan_id}/save", headers={"X-VOYA-Token": token})
    assert saved.status_code == 200
    kept_ids = [slot["id"] for slot in saved.json()["ideas"]["days"][0]["slots"]]
    for option_id in kept_ids:
        assert _row(store, option_id)["kept"] == 1
    monkeypatch.setenv("VOYA_OPS_TOKEN", "ops-test-token")
    ops = client.get("/v1/ops", headers={"X-Ops-Token": "ops-test-token"})
    assert ops.status_code == 200
    assert any(row["option_id"] == morning["id"] for row in ops.json()["idea_stats"])


def test_wrapping_back_does_not_count_shown_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/v1/plans", json=_BODY).json()
    plan_id = created["plan_id"]
    original = next(
        slot["id"] for slot in created["ideas"]["days"][0]["slots"] if slot["slot"] == "morning"
    )
    back = created
    for _ in range(3):
        response = client.post(f"/v1/plans/{plan_id}/ideas/1/morning/another")
        assert response.status_code == 200
        back = response.json()
    morning = next(
        slot["id"] for slot in back["ideas"]["days"][0]["slots"] if slot["slot"] == "morning"
    )
    assert morning == original
    assert _row(api_mod.store(), original)["shown"] == 1


def test_idea_stats_has_no_identifying_columns(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "t.db"))
    with store.tx() as cursor:
        row = cursor.execute("SELECT sql FROM sqlite_master WHERE name='idea_stats'").fetchone()
    assert row is not None
    sql = str(row["sql"]).lower()
    assert "option_id" in sql and "shown" in sql and "kept" in sql and "swapped" in sql
    for banned in ("user", "plan_id", "email", "ip_address", "owner"):
        assert banned not in sql
