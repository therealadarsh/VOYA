from datetime import UTC, datetime, timedelta
from decimal import Decimal

from voya.cost import CostLine, CostSource, summarize
from voya.data.loaders import load_data_bundle
from voya.pricing.freshness import is_stale, widen_range
from voya.pricing.rules import load_rule_tables

D = Decimal
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def test_load_data_bundle_covers_launch_area():
    bundle = load_data_bundle()
    assert bundle.cities == frozenset({"chicago", "nyc", "sf"})
    assert bundle.parks == frozenset({"indiana_dunes", "yosemite"})
    assert bundle.cited_file_count >= 7
    assert "chicago" in bundle.rules.sales_tax
    assert any("cta" in k for k in bundle.rules.transit_fares)
    assert bundle.rules.park_fees["YOSE"].amount_usd == D("35.00")
    assert bundle.rules.park_fees["INDU"].amount_usd == D("0.00")


def test_sales_tax_rates_are_fractions():
    rules = load_rule_tables()
    chi = rules.sales_tax["chicago"]
    assert D("0.05") < chi.combined_rate < D("0.15")


def test_freshness_widens_with_age():
    line = CostLine(
        label="Lunch",
        category="food",
        amount=D(20),
        low=D(15),
        high=D(30),
        currency="USD",
        source=CostSource.PRICE_RANGE,
        observed_at=T0 - timedelta(days=200),
        confidence=0.8,
        half_life_days=180,
    )
    aged = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    w = widen_range(line, now=aged)
    assert w.low < line.low and w.high > line.high
    assert is_stale(line, now=aged)


def test_summarize_hidden_and_keep():
    lines = [
        CostLine(
            label="Tax",
            category="tax",
            amount=D(3),
            low=D(3),
            high=D(3),
            currency="USD",
            source=CostSource.RULE,
            observed_at=T0,
            confidence=0.95,
        ),
        CostLine(
            label="Meal",
            category="food",
            amount=D(20),
            low=D(15),
            high=D(25),
            currency="USD",
            source=CostSource.PRICE_RANGE,
            observed_at=T0,
            confidence=0.8,
        ),
    ]
    s = summarize(lines, budget=D(50))
    assert s.hidden_costs == D(3)
    assert s.you_could_keep == D(27)
