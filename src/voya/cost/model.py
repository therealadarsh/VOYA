"""VOYA's cost model: every price is a range with a source, a timestamp and a
stated confidence, never a bare number.

`confidence` has one precise meaning: the probability we claim that the real
price lands inside [low, high]. That makes it testable. The Phase 5 coverage
metric checks whether lines stated at 0.8 really contain the price ~80% of the
time.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

CENT = Decimal("0.01")


def _to_cents(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


# Non-negative money amount, stored to 2 decimal places. Decimal, not float,
# so totals of many lines never drift (0.1 + 0.2 != 0.3 in float).
Money = Annotated[Decimal, Field(ge=0, allow_inf_nan=False), AfterValidator(_to_cents)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Category = Literal[
    "food",
    "attraction",
    "activity",
    "transport",
    "transit",
    "getting_there",
    "lodging",
    "tax",
    "tip",
    "fee",
    "extras",
    "gifts",
    "park_fee",
    "other",
]


class CostSource(StrEnum):
    """Where a number came from, best evidence first."""

    USER_ACTUAL = "user_actual"  # what a traveler reports they paid
    PRICE_RANGE = "price_range"  # provider's per-place price range
    PRICE_BUCKET = "price_bucket"  # provider's $-$$$$ level mapped to money
    TYPE_GUESS = "type_guess"  # our per-category guess, no place data
    FARE_QUOTE = "fare_quote"  # official transit/park fare or fee
    RULE = "rule"  # computed from a rules table (sales tax, occupancy tax)
    SETTING = "setting"  # product default the user can edit (tip %, gifts, extras)
    USER_ENTERED = "user_entered"  # exact amount the user typed (booked lodging, anchor ticket)


# Sources that count as "backed by real data" in plan totals. A price bucket
# is NOT: the level is observed, but the money amount is our mapping.
DATA_BACKED_SOURCES: frozenset[CostSource] = frozenset(
    {
        CostSource.USER_ACTUAL,
        CostSource.PRICE_RANGE,
        CostSource.FARE_QUOTE,
        CostSource.USER_ENTERED,
    }
)


class CostLine(BaseModel):
    """One priced line of a plan, e.g. lunch or a museum ticket."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    category: Category
    amount: Money
    low: Money
    high: Money
    currency: CurrencyCode
    source: CostSource
    observed_at: AwareDatetime
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_range(self) -> CostLine:
        if not (self.low <= self.amount <= self.high):
            raise ValueError(
                f"need low <= amount <= high, got {self.low} / {self.amount} / {self.high}"
            )
        if self.source is CostSource.USER_ACTUAL:
            if not (self.low == self.amount == self.high) or self.confidence != 1.0:
                raise ValueError(
                    "a user_actual line is a known amount: low == amount == high, confidence 1.0"
                )
        return self

    @classmethod
    def actual(
        cls,
        label: str,
        category: Category,
        amount: Decimal | int | str,
        currency: str,
        observed_at: datetime,
    ) -> CostLine:
        """A line for money actually spent (exact, so the range collapses)."""
        a = Decimal(amount)
        return cls(
            label=label,
            category=category,
            amount=a,
            low=a,
            high=a,
            currency=currency,
            source=CostSource.USER_ACTUAL,
            observed_at=observed_at,
            confidence=1.0,
        )

    @property
    def is_estimate(self) -> bool:
        return self.source is not CostSource.USER_ACTUAL

    @property
    def is_data_backed(self) -> bool:
        return self.source in DATA_BACKED_SOURCES

    def __str__(self) -> str:
        if not self.is_estimate:
            return f"{self.label}: {self.amount} {self.currency} (actual)"
        return (
            f"{self.label}: est. {self.amount} {self.currency} "
            f"(range {self.low}-{self.high}, {self.source.value}, "
            f"{self.confidence:.0%} confidence)"
        )


class CostSummary(BaseModel):
    """Plan-level totals. Every total here is an estimate unless all lines are actuals."""

    model_config = ConfigDict(frozen=True)

    currency: CurrencyCode
    line_count: int
    point_total: Decimal
    # Sum of lows / highs. high_total is the pessimistic total the Phase 3
    # optimizer fits under the cap. It is a bound only if every line stays
    # under its own high, so it is NOT an interval with a joint confidence.
    low_total: Decimal
    high_total: Decimal
    data_backed_total: Decimal
    # Share of the point total backed by real data; None when nothing costs money.
    data_backed_share: float | None
    by_source: dict[CostSource, Decimal]
    by_category: dict[str, Decimal]
    # The stalest number the total leans on; None for an empty plan.
    oldest_observed_at: datetime | None

    @property
    def is_estimate(self) -> bool:
        """True if any line is an estimate (only an all-actuals plan is exact)."""
        return any(src is not CostSource.USER_ACTUAL for src in self.by_source)


def summarize(lines: Sequence[CostLine], currency: str | None = None) -> CostSummary:
    """Total a plan's lines. All lines must share one currency (FX is Phase 2)."""
    currencies = {line.currency for line in lines}
    if currency is not None:
        currencies.add(currency)
    if not currencies:
        raise ValueError("pass `currency` to summarize an empty plan")
    if len(currencies) > 1:
        raise ValueError(f"mixed currencies {sorted(currencies)}: convert lines first")
    (cur,) = currencies

    zero = Decimal("0.00")
    point = sum((l.amount for l in lines), zero)
    backed = sum((l.amount for l in lines if l.is_data_backed), zero)

    by_source: dict[CostSource, Decimal] = {}
    by_category: dict[str, Decimal] = {}
    for line in lines:
        by_source[line.source] = by_source.get(line.source, zero) + line.amount
        by_category[line.category] = by_category.get(line.category, zero) + line.amount

    return CostSummary(
        currency=cur,
        line_count=len(lines),
        point_total=point,
        low_total=sum((l.low for l in lines), zero),
        high_total=sum((l.high for l in lines), zero),
        data_backed_total=backed,
        data_backed_share=float(backed / point) if point > 0 else None,
        by_source=by_source,
        by_category=by_category,
        oldest_observed_at=min((l.observed_at for l in lines), default=None),
    )
