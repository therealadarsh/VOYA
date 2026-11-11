from datetime import date
from decimal import Decimal

from voya.catalog import load_catalog
from voya.planner import PlanRequest, priced_for

D = Decimal


def test_chicago_rules_use_cited_sales_tax_and_transit(monkeypatch):
    monkeypatch.setenv("VOYA_CITED_RULES", "1")
    load_catalog.cache_clear()
    dest = load_catalog().destination("chicago")
    assert dest is not None
    assert dest.rules.sales_tax_pct == D("10.25")
    assert dest.rules.transit_fare == D("2.50")
    load_catalog.cache_clear()


def test_transit_lines_are_fare_quote():
    req = PlanRequest(
        destination="chicago",
        start_date=date(2026, 12, 5),
        budget=D(350),
        firmness="wiggle",
        party={"adults": 2},
        interests=["food"],
        pace="packed",
    )
    _dest, _cat, priced = priced_for(req)
    transit = [ln for ln in priced.lines if ln.kind == "transit"]
    assert transit
    assert all(ln.cost.source is not None for ln in transit)
    from voya.cost.model import CostSource

    assert all(ln.cost.source == CostSource.FARE_QUOTE for ln in transit)
