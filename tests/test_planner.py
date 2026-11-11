"""Owner logic: budget fit, savings first, worth-it, gifts, ranking, hidden costs."""

import random
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pytest

from voya.catalog import load_catalog
from voya.planner import (
    PlanRequest,
    apply_upgrade,
    build,
    priced_for,
)
from voya.uncertainty import SimLine, quantile, simulate

D = Decimal
DAY = date(2026, 11, 14)


def req(**kw) -> PlanRequest:
    base = dict(
        destination="chicago",
        start_date=DAY,
        budget=150,
        party={"adults": 2},
        interests=["food", "architecture"],
    )
    base.update(kw)
    return PlanRequest(**base)


# ---------------------------------------------------------------- uncertainty


def test_lognormal_matches_stated_coverage():
    line = SimLine(low=20, high=40, confidence=0.8, category="food")
    t = simulate([line], seed=1, n=40_000, rho_city=0, rho_cat=0)
    inside = np.mean((t >= 20) & (t <= 40))
    assert abs(inside - 0.8) < 0.01


def test_simulation_is_deterministic_and_derived_lines_follow_parent():
    lines = [SimLine(10, 30, 0.8, "food"), SimLine(0, 0, 1, "tax", parent=0, rate=0.1)]
    a = simulate(lines, seed=7)
    assert np.array_equal(a, simulate(lines, seed=7))
    no_tax = [lines[0], SimLine(0, 0, 1, "tax", parent=0, rate=0.0)]
    assert np.allclose(a, simulate(no_tax, seed=7) * 1.1)


def test_fixed_lines_have_no_spread():
    t = simulate([SimLine(12, 12, 1.0, "transit")], seed=3)
    assert quantile(t, 0.9) == D("12.00")


# --------------------------------------------------------------- budget fit


def test_value_plan_fits_and_shows_what_you_keep():
    p = build(req())
    h = p["headline"]
    assert p["status"] == "ready"
    assert D(h["fit_value"]) <= D(h["budget"])
    assert D(h["you_could_keep"]) == D(h["budget"]) - D(h["point"])
    assert h["is_estimate"] is True


def test_hard_limit_is_never_looser_than_wiggle_room():
    for dest in ("new-york", "chicago", "yosemite"):
        for days in (1, 2):
            w = build(req(destination=dest, days=days, budget=10_000, firmness="wiggle"))
            h = build(req(destination=dest, days=days, budget=10_000, firmness="hard"))
            assert D(h["headline"]["fit_value"]) >= D(w["headline"]["fit_value"])
            assert D(h["headline"]["fit_value"]) >= D(h["headline"]["high"])


def test_infeasible_budget_explains_gap_and_free_options():
    p = build(req(destination="new-york", days=2, budget=60))
    assert p["status"] == "infeasible"
    assert D(p["gap"]) > 0
    assert p["free_alternatives"]
    assert p["worth_it"] == []


def test_upgrades_always_fit_and_cost_more():
    r = req(
        destination="new-york",
        days=2,
        budget=700,
        party={"adults": 2},
        lodging={"status": "booked", "amount": "0"},
        interests=["art", "views"],
    )
    p = build(r)
    assert p["worth_it"], "a generous budget should offer worth-it upgrades"
    assert len(p["worth_it"]) <= 3
    for u in p["worth_it"]:
        assert D(u["delta"]) >= 5
        up = build(apply_upgrade(r, u["upgrade_id"]))
        assert up["status"] == "ready"
        assert D(up["headline"]["point"]) > D(p["headline"]["point"])


def test_gifts_allowance_is_five_percent_and_editable():
    p = build(req(budget=200))
    gifts = next(l for l in p["trip_lines"] if l["line_id"] == "gifts")
    assert D(gifts["amount"]) == D("10.00")
    assert "est." in gifts["label"]
    p2 = build(req(budget=200, gifts_amount=0))
    assert not any(l["line_id"] == "gifts" for l in p2["trip_lines"])


# ------------------------------------------------------------- hidden costs


def _lines(r):
    _, _, priced = priced_for(r)
    return priced.lines


def test_sales_tax_and_tip_are_separate_labeled_lines():
    lines = _lines(req(budget=400))
    tax = [l for l in lines if l.kind == "tax"]
    tip = [l for l in lines if l.kind == "tip"]
    assert tax and tip
    rate = load_catalog().destination("chicago").rules.sales_tax_pct / D(100)
    for t in tax:
        parent = next(l for l in lines if l.line_id == t.parent_id)
        expected = (parent.cost.amount * rate).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        assert t.cost.amount == expected
    assert all("est." in l.cost.label for l in tax + tip)


def test_tip_percent_is_a_user_setting():
    lines = _lines(req(budget=400, tip_pct=D(0)))
    assert not [l for l in lines if l.kind == "tip"]


def test_transit_extras_counted_and_getting_there_optional():
    r = req(destination="indiana-dunes", budget=300, getting_there={"from_id": "chicago"})
    p = build(r)
    assert p["getting_there_optional"]["available"] and not p["getting_there_optional"]["included"]
    assert not any(l["category"] == "getting_there" for l in p["trip_lines"])
    r2 = r.model_copy(
        update={"getting_there": r.getting_there.model_copy(update={"include_in_total": True})}
    )
    p2 = build(r2)
    assert D(p2["headline"]["point"]) > D(p["headline"]["point"])
    assert any(l.kind == "extras" for l in _lines(r))
    city = _lines(req(destination="new-york", budget=400))
    assert any(l.kind == "transit" for l in city)


def test_park_fee_is_per_vehicle():
    one = _lines(req(destination="yosemite", budget=500, party={"adults": 4}))
    two = _lines(req(destination="yosemite", budget=900, party={"adults": 6}))
    fee = lambda ls: next(l.cost.amount for l in ls if l.kind == "park_fee")
    assert fee(two) == 2 * fee(one)


# ------------------------------------------------------------------ ranking


def test_interests_first_and_one_hidden_gem_per_day():
    p = build(
        req(
            destination="san-francisco",
            budget=500,
            interests=["art"],
            days=2,
            lodging={"status": "booked", "amount": "0"},
        )
    )
    cat = load_catalog()
    gems = {pl.id for pl in cat.destination("san-francisco").places if pl.hidden_gem}
    used: set[str] = set()
    for d in p["days"]:
        sights = [i for i in d["items"] if i["kind"] == "sight"]
        if gems - used:  # one gem per day while unused gems remain
            assert sum(1 for i in sights if i["hidden_gem"]) >= 1
        used |= {i["place_id"] for i in sights}
    first = p["days"][0]["items"][0]
    assert "art" in first["why"].lower()


def test_quality_floor_and_no_repeated_sights():
    cat = load_catalog()
    p = build(
        req(
            destination="new-york", days=3, budget=2000, lodging={"status": "booked", "amount": "0"}
        )
    )
    sights = [
        i["place_id"]
        for d in p["days"]
        for i in d["items"]
        if i.get("place_id") and i["category"] != "food"
    ]
    assert len(sights) == len(set(sights))
    dest = cat.destination("new-york")
    for pid in sights:
        assert (dest.place(pid).rating or 5) >= 4.0
    for d in p["days"]:
        food = [i["place_id"] for i in d["items"] if i.get("category") == "food"]
        assert len(food) == len(set(food)), "no restaurant twice in one day"


def test_anchor_is_fixed_exact_and_blocks_its_time():
    r = req(
        destination="san-francisco",
        budget=200,
        anchor={"title": "Ball game", "start": "13:00", "duration_min": 180, "cost": "90"},
    )
    p = build(r)
    items = p["days"][0]["items"]
    anchor = next(i for i in items if i["kind"] == "anchor")
    assert anchor["cost"]["amount"] == "90.00" and anchor["cost"]["source"] == "user_entered"
    for i in items:
        if i["kind"] != "anchor":
            t = int(i["time"][:2]) * 60 + int(i["time"][3:])
            assert not (13 * 60 <= t < 16 * 60)


def test_multi_day_lodging_estimate_or_booked():
    est = build(req(days=3, budget=2000))
    labels = [l["label"] for l in est["trip_lines"]]
    assert any("Lodging estimate (2 nights)" in x for x in labels)
    assert any("lodging tax" in x for x in labels)
    booked = build(req(days=3, budget=2000, lodging={"status": "booked", "amount": "250"}))
    line = next(l for l in booked["trip_lines"] if l["category"] == "lodging")
    assert line["amount"] == "250.00" and line["source"] == "user_entered"


def test_unknown_destination_is_honest():
    from voya.planner import PlanError

    with pytest.raises(PlanError):
        build(req(destination="atlantis"))


def test_same_request_same_plan():
    assert build(req()) == build(req())


def test_children_priced_as_adults_with_note():
    p = build(req(party={"adults": 1, "children": ["6-12"]}, budget=300))
    assert any("Children" in n for n in p["notes"])


# --------------------------------------------------------------- guard prop


def test_guard_property_random_proposals_never_produce_unfit_ready_plans():
    rng = random.Random(42)
    cat = load_catalog()
    for _ in range(40):
        dest = rng.choice(cat.destinations)
        r = PlanRequest(
            destination=dest.id,
            start_date=DAY,
            days=rng.randint(1, 3),
            budget=rng.choice([40, 90, 200, 500, 1500]),
            firmness=rng.choice(["hard", "wiggle"]),
            party={"adults": rng.randint(1, 4)},
            interests=rng.sample(["food", "art", "nature", "history"], 2),
        )
        p = build(r)
        if p["status"] == "ready":
            assert D(p["headline"]["fit_value"]) <= r.budget
        for u in p["worth_it"]:
            up = build(apply_upgrade(r, u["upgrade_id"]))
            assert D(up["headline"]["fit_value"]) <= r.budget
