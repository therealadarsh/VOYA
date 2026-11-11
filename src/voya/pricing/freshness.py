"""Widen price ranges as evidence ages (plan section 4.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from voya.cost.model import CostLine

D = Decimal


def age_days(observed_at: datetime, *, now: datetime | None = None) -> int:
    ref = now or datetime.now(tz=UTC)
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    delta = ref - observed_at.astimezone(UTC)
    return max(0, delta.days)


def widen_range(line: CostLine, *, now: datetime | None = None) -> CostLine:
    """Return a copy with widened low/high when the observation is older."""
    if line.half_life_days is None or line.low == line.high == line.amount:
        return line
    days = age_days(line.observed_at, now=now)
    f = D(1) + D("0.10") * D(days) / D(line.half_life_days)
    low = (line.low / f).quantize(D("0.01"))
    high = (line.high * f).quantize(D("0.01"))
    low = min(low, line.amount)
    high = max(high, line.amount)
    return line.model_copy(update={"low": low, "high": high})


def is_stale(line: CostLine, *, now: datetime | None = None) -> bool:
    if line.half_life_days is None:
        return False
    return age_days(line.observed_at, now=now) > line.half_life_days
