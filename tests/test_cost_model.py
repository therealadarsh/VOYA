from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from voya.cost import CostLine, CostSource, summarize
from voya.cost.estimators import (
    PriceLevel,
    estimate,
    from_price_bucket,
    from_price_range,
    from_type_guess,
)

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
D = Decimal


def line(**over) -> CostLine:
    base = dict(
        label="Lunch",
        category="food",
        amount=D(20),
        low=D(15),
        high=D(30),
        currency="USD",
        source=CostSource.PRICE_RANGE,
        observed_at=T0,
        confidence=0.8,
    )
    base.update(over)
    return CostLine(**base)


# ---- CostLine validation ---------------------------------------------------


class TestCostLine:
    def test_valid_line(self):
        l = line()
        assert l.amount == D("20.00")
        assert l.is_estimate and l.is_data_backed

    @pytest.mark.parametrize(
        "over",
        [
            {"low": D(25)},  # low above amount
            {"high": D(10)},  # high below amount
            {"amount": D(-1), "low": D(-2)},  # negative money
            {"confidence": 1.5},
            {"confidence": -0.1},
            {"currency": "usd"},
            {"currency": "US"},
            {"label": ""},
            {"observed_at": datetime(2026, 11, 1)},  # naive datetime
            {"source": "vibes"},
            {"amount": D("NaN")},
        ],
    )
    def test_rejects_bad_input(self, over):
        with pytest.raises(ValidationError):
            line(**over)

    def test_amounts_rounded_to_cents(self):
        l = line(amount=D("20.005"), low=D("15.004"), high=D("30"))
        assert l.amount == D("20.01")
        assert l.low == D("15.00")

    def test_frozen(self):
        with pytest.raises(ValidationError):
            line().amount = D(1)  # type: ignore[misc]

    def test_actual_is_exact(self):
        a = CostLine.actual("Ramen", "food", "14.50", "USD", T0)
        assert a.low == a.amount == a.high == D("14.50")
        assert a.confidence == 1.0
        assert not a.is_estimate and a.is_data_backed

    def test_user_actual_must_be_exact(self):
        with pytest.raises(ValidationError):
            line(source=CostSource.USER_ACTUAL, confidence=1.0)  # low != high
        with pytest.raises(ValidationError):
            line(source=CostSource.USER_ACTUAL, low=D(20), high=D(20), confidence=0.9)

    def test_estimates_are_labeled(self):
        assert "est." in str(line())
        assert "80% confidence" in str(line())
        actual = CostLine.actual("Ramen", "food", 14, "USD", T0)
        assert "est." not in str(actual) and "actual" in str(actual)


# ---- plan totals -------------------------------------------------------------


class TestSummarize:
    def plan(self):
        return [
            line(label="Lunch", amount=D(20), low=D(15), high=D(30)),  # range, backed
            line(  # bucket, not backed
                label="Museum",
                category="attraction",
                amount=D(15),
                low=D(8),
                high=D(25),
                source=CostSource.PRICE_BUCKET,
                confidence=0.7,
                observed_at=T0 - timedelta(days=10),
            ),
            line(  # guess, not backed
                label="Taxi",
                category="transport",
                amount=D(5),
                low=D(2),
                high=D(10),
                source=CostSource.TYPE_GUESS,
                confidence=0.5,
            ),
            CostLine.actual("Coffee", "food", 10, "USD", T0 + timedelta(hours=1)),
        ]

    def test_point_low_high_totals(self):
        s = summarize(self.plan())
        assert s.point_total == D(50)
        assert s.low_total == D(35)
        assert s.high_total == D(75)
        assert s.low_total <= s.point_total <= s.high_total
        assert s.line_count == 4

    def test_data_backed_share(self):
        s = summarize(self.plan())
        # price_range 20 + user_actual 10 out of 50
        assert s.data_backed_total == D(30)
        assert s.data_backed_share == pytest.approx(0.6)

    def test_breakdowns(self):
        s = summarize(self.plan())
        assert s.by_source == {
            CostSource.PRICE_RANGE: D(20),
            CostSource.PRICE_BUCKET: D(15),
            CostSource.TYPE_GUESS: D(5),
            CostSource.USER_ACTUAL: D(10),
        }
        assert s.by_category == {"food": D(30), "attraction": D(15), "transport": D(5)}
        assert sum(s.by_source.values()) == s.point_total
        assert sum(s.by_category.values()) == s.point_total

    def test_oldest_observation(self):
        assert summarize(self.plan()).oldest_observed_at == T0 - timedelta(days=10)

    def test_is_estimate_unless_all_actual(self):
        assert summarize(self.plan()).is_estimate
        actuals = [CostLine.actual("A", "food", 5, "USD", T0)]
        assert not summarize(actuals).is_estimate

    def test_no_float_drift(self):
        lines = [line(amount=D("0.10"), low=D("0.10"), high=D("0.10"))] * 3
        assert summarize(lines).point_total == D("0.30")

    def test_free_plan_share_is_none(self):
        free = [line(amount=D(0), low=D(0), high=D(5))]
        s = summarize(free)
        assert s.point_total == 0 and s.data_backed_share is None

    def test_empty_plan_needs_currency(self):
        with pytest.raises(ValueError):
            summarize([])
        s = summarize([], currency="EUR")
        assert s.point_total == 0 and s.currency == "EUR" and s.oldest_observed_at is None

    def test_mixed_currencies_rejected(self):
        with pytest.raises(ValueError, match="mixed currencies"):
            summarize([line(), line(currency="JPY")])
        with pytest.raises(ValueError, match="mixed currencies"):
            summarize([line()], currency="EUR")


# ---- estimators ----------------------------------------------------------------


class TestEstimators:
    def test_closed_range_uses_midpoint(self):
        l = from_price_range("Sushi", "food", D(20), D(40), "USD", T0)
        assert (l.low, l.amount, l.high) == (D(20), D(30), D(40))
        assert l.source is CostSource.PRICE_RANGE and l.confidence == 0.8

    def test_reversed_range_is_normalized(self):
        l = from_price_range("Sushi", "food", D(40), D(20), "USD", T0)
        assert (l.low, l.high) == (D(20), D(40))

    def test_non_usd_range_is_kept(self):
        # Daytrip's gap: a JPY range was discarded (pois.ts:514). VOYA keeps it.
        l = from_price_range("Ramen", "food", D(1000), D(2000), "JPY", T0)
        assert l.currency == "JPY" and l.amount == D(1500)
        assert l.is_data_backed

    def test_open_ranges_are_wider_and_less_sure(self):
        more_than = from_price_range("Steak", "food", D(50), None, "USD", T0)
        assert (more_than.low, more_than.amount, more_than.high) == (D(50), D("62.5"), D(100))
        under = from_price_range("Noodles", "food", None, D(20), "USD", T0)
        assert (under.low, under.amount, under.high) == (D(10), D(17), D(20))
        assert more_than.confidence < 0.8 and under.confidence < 0.8

    def test_range_needs_an_end(self):
        with pytest.raises(ValueError):
            from_price_range("X", "food", None, None, "USD", T0)

    def test_bucket_food_vs_attraction(self):
        food = from_price_bucket("Bistro", "food", PriceLevel.MODERATE, T0)
        sight = from_price_bucket("Tower", "attraction", PriceLevel.MODERATE, T0)
        assert food.amount == D(26) and sight.amount == D(15)
        assert not food.is_data_backed
        assert food.low < food.amount < food.high

    def test_free_bucket_attraction_is_exactly_free(self):
        l = from_price_bucket("Park", "attraction", PriceLevel.FREE, T0)
        assert l.low == l.amount == l.high == 0

    def test_type_guess(self):
        museum = from_type_guess("Museum", "attraction", "museum", T0)
        assert (museum.low, museum.amount, museum.high) == (D(9), D(18), D(36))
        unknown = from_type_guess("Thing", "attraction", "mystery_type", T0)
        assert unknown.amount == D(12)
        landmark = from_type_guess("Arch", "attraction", "monument", T0)
        assert landmark.amount == 0 and landmark.high > 0  # free-ish, not certain
        assert museum.confidence < 0.7

    @pytest.mark.parametrize(
        "kwargs, source",
        [
            (
                dict(
                    range_start=D(10),
                    range_end=D(20),
                    range_currency="EUR",
                    level=PriceLevel.EXPENSIVE,
                ),
                CostSource.PRICE_RANGE,
            ),
            (dict(level=PriceLevel.EXPENSIVE, place_type="museum"), CostSource.PRICE_BUCKET),
            (dict(place_type="museum"), CostSource.TYPE_GUESS),
            (dict(), CostSource.TYPE_GUESS),
        ],
    )
    def test_estimate_prefers_best_evidence(self, kwargs, source):
        assert estimate("X", "attraction", T0, **kwargs).source is source

    def test_estimate_range_needs_currency(self):
        with pytest.raises(ValueError):
            estimate("X", "food", T0, range_start=D(10), range_end=D(20))

    def test_confidence_ordering_matches_evidence_strength(self):
        r = estimate("X", "food", T0, range_start=D(10), range_end=D(20), range_currency="USD")
        b = estimate("X", "food", T0, level=PriceLevel.MODERATE)
        g = estimate("X", "food", T0)
        assert r.confidence > b.confidence > g.confidence
