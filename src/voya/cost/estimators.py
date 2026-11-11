"""Build CostLines from whatever price evidence a place has.

Every number in the PRIORS section is an assumption, not a measurement. Phase 5
(eval harness) measures how often each source's range really contains the
price, and Phase 6 (actuals) recalibrates them per city and category.

The point values for price buckets and type guesses are taken from Daytrip's
`estimateCost` (MIT, ArabotHXL/trip-planner @ 74610afb, see
THIRD_PARTY_NOTICES.md). The low/high bands and confidences are VOYA's.

Phase 1 is single-currency: bucket and type tables are in USD. Phase 2 adds
FX and the per-city price index. Price ranges keep their own currency, so a
JPY range is never discarded the way Daytrip discards it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import IntEnum

from voya.cost.model import Category, CostLine, CostSource

D = Decimal

# ---------------------------------------------------------------- PRIORS ---

# Stated probability that the real price lands in [low, high], per source.
CONFIDENCE = {
    "range_closed": 0.80,  # provider gave both ends
    "range_open": 0.60,  # "more than X" or "under Y"
    CostSource.PRICE_BUCKET: 0.70,
    CostSource.TYPE_GUESS: 0.50,
}

# Open-ended ranges: point and the missing end, as multiples of the given end.
OPEN_LOW_POINT, OPEN_LOW_HIGH = D("1.25"), D("2")  # "more than X"
OPEN_HIGH_POINT, OPEN_HIGH_LOW = D("0.85"), D("0.5")  # "under Y"


class PriceLevel(IntEnum):
    """Provider-neutral $ level (Google's PRICE_LEVEL_* maps 1:1)."""

    FREE = 0
    INEXPENSIVE = 1
    MODERATE = 2
    EXPENSIVE = 3
    VERY_EXPENSIVE = 4


# (low, point, high) in USD per person.
FOOD_BUCKETS_USD: dict[PriceLevel, tuple[Decimal, Decimal, Decimal]] = {
    # Daytrip treats a "free" restaurant like an inexpensive one; so do we.
    PriceLevel.FREE: (D(6), D(12), D(20)),
    PriceLevel.INEXPENSIVE: (D(6), D(12), D(20)),
    PriceLevel.MODERATE: (D(15), D(26), D(40)),
    PriceLevel.EXPENSIVE: (D(28), D(40), D(70)),
    PriceLevel.VERY_EXPENSIVE: (D(45), D(70), D(150)),
}
OTHER_BUCKETS_USD: dict[PriceLevel, tuple[Decimal, Decimal, Decimal]] = {
    PriceLevel.FREE: (D(0), D(0), D(0)),
    PriceLevel.INEXPENSIVE: (D(0), D(8), D(15)),
    PriceLevel.MODERATE: (D(8), D(15), D(25)),
    PriceLevel.EXPENSIVE: (D(15), D(25), D(45)),
    PriceLevel.VERY_EXPENSIVE: (D(25), D(40), D(80)),
}

# Point guess in USD by place type when there is no price data at all.
TYPE_GUESS_USD: dict[str, Decimal] = {
    "cafe": D(9),
    "coffee_shop": D(9),
    "bakery": D(9),
    "restaurant": D(24),
    "museum": D(18),
    "art_museum": D(18),
    "history_museum": D(18),
    "art_gallery": D(0),
    "amusement_park": D(30),
    "zoo": D(30),
    "water_park": D(45),
    "aquarium": D(28),
    "observation_deck": D(30),
    "performing_arts_theater": D(22),
    "movie_theater": D(22),
    "night_club": D(20),
    "shopping_mall": D(0),
    "market": D(0),
    "monument": D(0),
    "historical_landmark": D(0),
    "plaza": D(0),
}
TYPE_GUESS_DEFAULT_USD = {"food": D(24), "activity": D(20)}  # else 12
TYPE_GUESS_FALLBACK_USD = D(12)
# A type guess is wide: half to double the point. "Free" things can still
# cost something (a donation, a special exhibit), so they get a small high.
TYPE_GUESS_LOW_MULT, TYPE_GUESS_HIGH_MULT = D("0.5"), D(2)
TYPE_GUESS_FREE_HIGH_USD = D(10)

# ---------------------------------------------------------------- BUILDERS ---


def from_price_range(
    label: str,
    category: Category,
    start: Decimal | None,
    end: Decimal | None,
    currency: str,
    observed_at: datetime,
) -> CostLine:
    """A provider price range, kept in its own currency."""
    if start is None and end is None:
        raise ValueError("a price range needs at least one end")
    if start is not None and end is not None:
        lo, hi = min(start, end), max(start, end)
        point, conf = (lo + hi) / 2, CONFIDENCE["range_closed"]
    elif start is not None:  # "more than X"
        lo, hi, point = start, start * OPEN_LOW_HIGH, start * OPEN_LOW_POINT
        conf = CONFIDENCE["range_open"]
    else:  # "under Y"
        assert end is not None
        lo, hi, point = end * OPEN_HIGH_LOW, end, end * OPEN_HIGH_POINT
        conf = CONFIDENCE["range_open"]
    return CostLine(
        label=label,
        category=category,
        amount=point,
        low=lo,
        high=hi,
        currency=currency,
        source=CostSource.PRICE_RANGE,
        observed_at=observed_at,
        confidence=conf,
    )


def from_price_bucket(
    label: str, category: Category, level: PriceLevel, observed_at: datetime
) -> CostLine:
    """A provider $-level mapped to a USD band."""
    table = FOOD_BUCKETS_USD if category == "food" else OTHER_BUCKETS_USD
    lo, point, hi = table[level]
    return CostLine(
        label=label,
        category=category,
        amount=point,
        low=lo,
        high=hi,
        currency="USD",
        source=CostSource.PRICE_BUCKET,
        observed_at=observed_at,
        confidence=CONFIDENCE[CostSource.PRICE_BUCKET],
    )


def from_type_guess(
    label: str, category: Category, place_type: str | None, observed_at: datetime
) -> CostLine:
    """Our per-type guess when the place has no price data."""
    point = TYPE_GUESS_USD.get(
        place_type or "", TYPE_GUESS_DEFAULT_USD.get(category, TYPE_GUESS_FALLBACK_USD)
    )
    if point == 0:
        lo, hi = D(0), TYPE_GUESS_FREE_HIGH_USD
    else:
        lo, hi = point * TYPE_GUESS_LOW_MULT, point * TYPE_GUESS_HIGH_MULT
    return CostLine(
        label=label,
        category=category,
        amount=point,
        low=lo,
        high=hi,
        currency="USD",
        source=CostSource.TYPE_GUESS,
        observed_at=observed_at,
        confidence=CONFIDENCE[CostSource.TYPE_GUESS],
    )


def estimate(
    label: str,
    category: Category,
    observed_at: datetime,
    *,
    range_start: Decimal | None = None,
    range_end: Decimal | None = None,
    range_currency: str | None = None,
    level: PriceLevel | None = None,
    place_type: str | None = None,
) -> CostLine:
    """Use the best evidence available: price range, then bucket, then type."""
    if range_start is not None or range_end is not None:
        if range_currency is None:
            raise ValueError("a price range needs its currency")
        return from_price_range(
            label, category, range_start, range_end, range_currency, observed_at
        )
    if level is not None:
        return from_price_bucket(label, category, level, observed_at)
    return from_type_guess(label, category, place_type, observed_at)
