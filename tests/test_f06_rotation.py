"""Classic picks rotate one slot at a time and stay with the plan."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.ideas import day_one_titles
from voya.store import Store

_BODY = {
    "destination": "new-york",
    "start_date": "2026-11-14",
    "budget": "400",
    "firmness": "wiggle",
    "party": {"adults": 2},
    "interests": ["food"],
    "days": 7,
}


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_ENV", raising=False)
    monkeypatch.setenv("VOYA_DEV_SIGNIN", "1")
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    return TestClient(api_mod.app)


def _titles(payload: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for day in payload["ideas"]["days"]:
        for slot in day["slots"]:
            found[f"{day['day']}:{slot['slot']}"] = slot["title"]
    return found


def test_the_same_plan_id_keeps_the_same_picks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/v1/plans", json={**_BODY, "days": 2})
    assert created.status_code == 200
    plan_id = created.json()["plan_id"]
    again = client.get(f"/v1/plans/{plan_id}")
    assert _titles(created.json()) == _titles(again.json())
    assert created.json()["ideas"]["label"] == "Classic picks"
    assert "price not yet checked" in again.text


def test_different_plan_ids_vary_the_first_day() -> None:
    combos = {day_one_titles(f"seed-{index}") for index in range(50)}
    assert len(combos) >= 3


def test_a_trip_does_not_repeat_a_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/v1/plans", json=_BODY)
    titles = list(_titles(created.json()).values())
    assert len(titles) == 21
    assert len(set(titles)) == 21


def test_another_changes_only_that_slot_and_undo_restores_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post("/v1/plans", json=_BODY).json()
    plan_id = created["plan_id"]
    before = _titles(created)
    moved = client.post(f"/v1/plans/{plan_id}/ideas/1/morning/another")
    assert moved.status_code == 200
    after = _titles(moved.json())
    assert after["1:morning"] != before["1:morning"]
    rest = {key: value for key, value in after.items() if key != "1:morning"}
    assert rest == {key: value for key, value in before.items() if key != "1:morning"}
    restored = client.post(f"/v1/plans/{plan_id}/undo")
    assert restored.status_code == 200
    assert _titles(restored.json()) == before


def test_old_idea_routes_are_retired(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(tmp_path, monkeypatch)
    listed = client.get("/v1/ideas", params={"city": "nyc", "seed": "alpha"})
    nxt = client.post("/v1/ideas/next", json={"current_id": "harbor", "days": 1})
    assert listed.status_code == 410
    assert nxt.status_code == 410
    chicago = client.post(
        "/v1/plans",
        json={**_BODY, "destination": "chicago", "days": 1},
    )
    assert chicago.status_code == 200
    assert chicago.json()["ideas"] is None
