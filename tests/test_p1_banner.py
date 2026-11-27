"""S04: the demo banner is per destination, not one switch for the whole catalog.

Cited destinations in these tests are built in memory with synthetic=False.
That flag is a test control, not a claim that the bundled prices are real.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voya import api as api_mod
from voya.catalog import (
    Catalog,
    Destination,
    destination_is_demo,
    load_catalog,
    show_demo_banner,
)
from voya.cost.model import CostSource
from voya.planner import PlanRequest, build
from voya.store import Store

ROOT = Path(__file__).resolve().parents[1]
DAY = date(2026, 11, 14)
SAFE_SOURCES = (
    CostSource.OWNER_CHECK,
    CostSource.FARE_QUOTE,
    CostSource.RULE,
    CostSource.SETTING,
    CostSource.USER_ENTERED,
    CostSource.USER_ACTUAL,
    CostSource.PRICE_RANGE,
)


@pytest.fixture
def client(tmp_path):
    api_mod._state.clear()
    api_mod._state["store"] = Store(str(tmp_path / "t.db"))
    api_mod._hits.clear()
    return TestClient(api_mod.app)


def _retarget(
    dest: Destination, *, synthetic: bool | None, source: CostSource | None
) -> Destination:
    places = dest.places
    if source is not None:
        places = tuple(
            p.model_copy(update={"price": p.price.model_copy(update={"source": source})})
            for p in places
        )
    return dest.model_copy(update={"synthetic": synthetic, "places": places})


def mixed_catalog() -> Catalog:
    """In-memory catalog: synthetic=False. Chicago places are owner_check or fare_quote. NYC stays demo."""
    cat = load_catalog()
    dests: list[Destination] = []
    for dest in cat.destinations:
        if dest.id == "chicago":
            places = tuple(
                p.model_copy(
                    update={
                        "price": p.price.model_copy(
                            update={
                                "source": CostSource.OWNER_CHECK
                                if i % 2 == 0
                                else CostSource.FARE_QUOTE
                            }
                        )
                    }
                )
                for i, p in enumerate(dest.places)
            )
            dests.append(dest.model_copy(update={"synthetic": False, "places": places}))
        elif dest.id == "new-york":
            dests.append(dest.model_copy(update={"synthetic": True}))
        else:
            dests.append(dest)
    return cat.model_copy(update={"synthetic": False, "destinations": tuple(dests)})


def _plan(dest_id: str, cat: Catalog) -> dict:
    return build(
        PlanRequest(
            destination=dest_id,
            start_date=DAY,
            budget=Decimal("500"),
            party={"adults": 1},
            interests=["food"],
        ),
        cat,
    )


def test_meta_on_todays_demo_catalog_marks_every_destination(client):
    meta = client.get("/v1/meta").json()
    assert meta["demo_data"] is True
    assert meta["destinations"]
    assert {d["data_status"] for d in meta["destinations"]} == {"demo"}


def test_mixed_catalog_plan_and_meta_follow_each_destination(client, monkeypatch):
    cat = mixed_catalog()
    monkeypatch.setattr(api_mod, "load_catalog", lambda path=None: cat)
    meta = client.get("/v1/meta").json()
    by_id = {d["id"]: d["data_status"] for d in meta["destinations"]}
    assert by_id["chicago"] == "cited"
    assert by_id["new-york"] == "demo"
    assert _plan("chicago", cat)["demo_data"] is False
    assert _plan("new-york", cat)["demo_data"] is True


def test_type_guess_line_turns_that_plan_back_to_demo():
    cat = mixed_catalog()
    chicago = cat.destination("chicago")
    assert chicago is not None
    flagged = _retarget(chicago, synthetic=False, source=CostSource.TYPE_GUESS)
    cat = cat.model_copy(
        update={
            "destinations": tuple(flagged if d.id == "chicago" else d for d in cat.destinations)
        }
    )
    assert _plan("chicago", cat)["demo_data"] is True


def test_catalog_synthetic_wins_over_a_cited_destination():
    cat = mixed_catalog().model_copy(update={"synthetic": True})
    chicago = cat.destination("chicago")
    assert chicago is not None and chicago.synthetic is False
    assert destination_is_demo(cat, chicago) is True


def test_destination_with_zero_places_is_demo():
    cat = mixed_catalog()
    chicago = cat.destination("chicago")
    assert chicago is not None
    empty = chicago.model_copy(update={"places": (), "synthetic": False})
    assert destination_is_demo(cat, empty) is True


def test_cited_money_sources_do_not_turn_the_banner_on():
    cat = mixed_catalog()
    chicago = cat.destination("chicago")
    assert chicago is not None
    for source in SAFE_SOURCES:
        assert destination_is_demo(cat, chicago, (source,)) is False
    assert show_demo_banner(cat) is True  # NYC is still demo, so the catalog-wide flag stays on


def test_unknown_destination_is_still_unsupported(client):
    res = client.post(
        "/v1/plans",
        json={
            "destination": "atlantis",
            "start_date": "2026-11-14",
            "budget": "300",
            "party": {"adults": 1},
            "interests": ["food"],
        },
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "UNSUPPORTED"


def test_picker_tags_demo_destinations():
    text = (ROOT / "src/voya/web/app.js").read_text()
    assert 'data_status === "demo"' in text
    assert "Demo prices" in text
