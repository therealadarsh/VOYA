"""Public NYC slice: Postgres SQL, places pipeline, idea bank, demo banner, metrics."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.catalog import (
    Catalog,
    Destination,
    LodgingNight,
    Place,
    PriceInfo,
    Rules,
    show_demo_banner,
)
from voya.cost.model import CostSource
from voya.db import prepare_sql
from voya.ideas import ideas_after, ideas_for, nyc_transit
from voya.providers.foursquare import (
    FoursquarePlaces,
    dollars_from_level,
    from_env,
    live_blockers,
    round_coord,
)
from voya.store import Store


def test_upsert_sql_targets_postgres_conflicts() -> None:
    sql = prepare_sql("INSERT OR REPLACE INTO magic_links VALUES (?,?,?)", postgres=True)
    assert "ON CONFLICT (token_hash)" in sql
    assert "?" not in sql
    assert prepare_sql("SELECT 1", postgres=False) == "SELECT 1"


def test_postgres_round_trip() -> None:
    url = os.environ.get("VOYA_TEST_DATABASE_URL", "")
    if not url.startswith("postgres"):
        pytest.skip("set VOYA_TEST_DATABASE_URL to a Postgres URL")
    store = Store(url)
    with store.tx() as cursor:
        for table in (
            "feedback",
            "plan_versions",
            "plans",
            "preferences",
            "ai_spend",
            "magic_links",
            "users",
        ):
            cursor.execute(f"DELETE FROM {table}")
    pid = store.create_plan('{"destination":"new-york"}')
    assert store.plan(pid)["request_json"] == '{"destination":"new-york"}'
    store.add_feedback("from postgres", "a@example.com")
    assert store.feedback_all()[0]["message"] == "from postgres"
    store.set_pref("owner", "pace", "relaxed", "test")
    store.set_pref("owner", "pace", "packed", "test")
    assert store.prefs("owner")[0]["value"] == "packed"
    store.add_ai_spend("month:2026-11", Decimal("0.10"))
    store.add_ai_spend("month:2026-11", Decimal("0.15"))
    assert store.ai_spent("month:2026-11") == Decimal("0.25")
    store.save_magic_link("a@example.com", "link-token", datetime.now(UTC) + timedelta(minutes=5))
    assert store.consume_magic_link("link-token") == "a@example.com"
    again = Store(url)
    assert again.plan(pid)["id"] == pid


def test_sqlite_store_still_round_trips(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "t.db"))
    store.ping()
    store.add_feedback("idea card", None)
    assert store.feedback_all()[0]["message"] == "idea card"


def test_same_seed_keeps_the_set_and_another_rotates() -> None:
    first = ideas_for("alpha", days=7)
    again = ideas_for("alpha", days=1)
    assert first["set_id"] == again["set_id"]
    assert len(first["days"]) == 7
    assert len(again["days"]) == 1
    nxt = ideas_after(first["set_id"], days=1)
    assert nxt["set_id"] != first["set_id"]
    assert nxt["days"][0]["slots"][0]["title"] != first["days"][0]["slots"][0]["title"]
    blob = json.dumps(first["days"])
    assert "$" not in blob


def test_transit_cost_comes_from_the_cited_fare_file() -> None:
    transit = nyc_transit()
    assert transit is not None
    raw = json.loads(Path("data/cities/nyc/transit_fares.json").read_text(encoding="utf-8"))
    assert transit["amount"] == raw["fares"][0]["full_fare_usd"]
    assert transit["source"] == raw["source"]
    assert transit["observed_at"] == raw["observed_at"]


def test_demo_banner_stays_until_every_place_cost_is_sourced() -> None:
    cat = _catalog(CostSource.OWNER_CHECK, synthetic=False)
    assert show_demo_banner(cat) is False
    guessed = _catalog(CostSource.TYPE_GUESS, synthetic=False)
    assert show_demo_banner(guessed) is True
    assert show_demo_banner(_catalog(CostSource.OWNER_CHECK, synthetic=True)) is True
    assert show_demo_banner(cat, (CostSource.TYPE_GUESS,)) is True


def test_places_live_stays_off_without_a_key_and_budget() -> None:
    blockers = live_blockers({})
    assert blockers and "FOURSQUARE_API_KEY" in blockers[0]
    assert "VOYA_PLACES_BUDGET_USD" in blockers[0]
    client = from_env({})
    with pytest.raises(Exception, match="FOURSQUARE_API_KEY"):
        client.search("park", near_lat=40.74882, near_lng=-73.98551)
    assert dollars_from_level(2) is None
    assert round_coord(40.74882) == 40.749
    assert round_coord(-73.98551) == -73.986


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str], dict[str, str]]] = []

    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]):
        self.calls.append((url, params, headers))

        class _Response:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "results": [
                        {
                            "fsq_place_id": "abc",
                            "name": "Example Coffee",
                            "latitude": 40.74882,
                            "longitude": -73.98551,
                            "categories": [{"name": "Coffee Shop"}],
                            "price": 2,
                        }
                    ]
                }

        return _Response()


def test_foursquare_search_rounds_coordinates_and_stops_at_the_budget() -> None:
    http = _FakeHttp()
    places = FoursquarePlaces(
        api_key="test-key",
        budget_usd=Decimal("0.02"),
        usd_per_call=Decimal("0.02"),
        live=True,
        client=http,
    )
    found = places.search("coffee", near_lat=40.74882, near_lng=-73.98551, limit=1)
    assert found[0].lat == 40.749
    assert found[0].lng == -73.986
    assert found[0].price_level == 2
    assert dollars_from_level(found[0].price_level) is None
    assert http.calls[0][1]["ll"] == "40.749,-73.986"
    assert "test-key" not in http.calls[0][0]
    assert http.calls[0][2]["X-Places-Api-Version"] == "2025-06-17"
    with pytest.raises(Exception, match="budget"):
        places.search("coffee", near_lat=40.7, near_lng=-73.9)


def test_ideas_and_metrics_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VOYA_INVITE_CODE", raising=False)
    monkeypatch.delenv("VOYA_METRICS_TOKEN", raising=False)
    api_mod._state.clear()
    api_mod._hits.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    client = TestClient(api_mod.app)
    ideas = client.get("/v1/ideas", params={"city": "nyc", "seed": "alpha", "days": 2})
    assert ideas.status_code == 200
    body = ideas.json()
    assert body["transit"]["amount"] == "2.90"
    assert len(body["days"]) == 2
    other = client.post("/v1/ideas/next", json={"current_id": body["set_id"], "days": 1})
    assert other.status_code == 200
    assert other.json()["set_id"] != body["set_id"]
    missing = client.get("/v1/ideas", params={"city": "paris"})
    assert missing.status_code == 404
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "voya_http_requests_total" in metrics.text
    monkeypatch.setenv("VOYA_METRICS_TOKEN", "metrics-secret")
    denied = client.get("/metrics")
    assert denied.status_code == 401
    allowed = client.get("/metrics", headers={"X-Metrics-Token": "metrics-secret"})
    assert allowed.status_code == 200


def _catalog(source: CostSource, *, synthetic: bool) -> Catalog:
    place = Place(
        id="p",
        name="Cited place",
        category="attraction",
        tags=("art",),
        lat=40.748,
        lng=-73.986,
        open="09:00",
        close="17:00",
        duration_min=60,
        rating=None,
        reviews=None,
        price=PriceInfo(
            low=Decimal(1), point=Decimal(1), high=Decimal(1), source=source, confidence=0.9
        ),
    )
    rules = Rules(
        sales_tax_pct=Decimal(0),
        occupancy_tax_pct=Decimal(0),
        transit_fare=Decimal(0),
        extras_per_person_day=Decimal(0),
        lodging_night=LodgingNight(low=Decimal(0), point=Decimal(0), high=Decimal(0)),
        park_fee_vehicle=Decimal(0),
    )
    dest = Destination(
        id="nyc",
        name="New York City",
        kind="city",
        state="NY",
        tz="America/New_York",
        center=(40.748, -73.986),
        rules=rules,
        places=(place,),
    )
    return Catalog(
        synthetic=synthetic,
        notice="",
        version="test",
        destinations=(dest,),
        routes=(),
        fuel_price_per_gallon={},
        default_mpg=25,
    )
