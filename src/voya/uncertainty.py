"""Price uncertainty: simulate plan totals so "wiggle room" budgets can be checked.

Each base line becomes a log-normal whose central `confidence` interval equals
[max(low, 0.05*high), high]. A line with low == high is fixed. Lines share
shocks through a Gaussian copula: one city factor (rho_city) and one factor per
category (rho_cat). Derived lines (tax, tip) are a fixed rate times their parent
line's simulated value, so they move with it.

The defaults for rho are starting assumptions, to be re-estimated from real
spend data. Results are deterministic for a given seed.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from decimal import Decimal
from statistics import NormalDist

import numpy as np

RHO_CITY = 0.25
RHO_CATEGORY = 0.15
N_SAMPLES = 10_000


@dataclass(frozen=True)
class SimLine:
    low: float
    high: float
    confidence: float
    category: str
    parent: int | None = None  # index of the parent line for derived lines
    rate: float = 0.0  # derived value = rate * parent value


def seed_from(*parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:12], 16)


def simulate(
    lines: list[SimLine],
    seed: int,
    n: int = N_SAMPLES,
    rho_city: float = RHO_CITY,
    rho_cat: float = RHO_CATEGORY,
) -> np.ndarray:
    """Return n simulated plan totals."""
    rng = np.random.default_rng(seed)
    if not lines:
        return np.zeros(n)
    z_city = rng.standard_normal(n)
    cats = sorted({ln.category for ln in lines})
    z_cat = {c: rng.standard_normal(n) for c in cats}
    resid = math.sqrt(max(0.0, 1.0 - rho_city - rho_cat))
    values: list[np.ndarray] = [np.zeros(n)] * len(lines)
    totals = np.zeros(n)
    for i, ln in enumerate(lines):
        if ln.parent is not None:
            continue
        if ln.high <= 0 or ln.low >= ln.high:
            values[i] = np.full(n, ln.high if ln.low >= ln.high else 0.0)
        else:
            lo = max(ln.low, 0.05 * ln.high)
            z = NormalDist().inv_cdf((1 + min(ln.confidence, 0.999)) / 2)
            mu = (math.log(lo) + math.log(ln.high)) / 2
            sigma = (math.log(ln.high) - math.log(lo)) / (2 * z)
            shock = (
                math.sqrt(rho_city) * z_city
                + math.sqrt(rho_cat) * z_cat[ln.category]
                + resid * rng.standard_normal(n)
            )
            values[i] = np.exp(mu + sigma * shock)
        totals += values[i]
    for ln in lines:
        if ln.parent is not None:
            totals += ln.rate * values[ln.parent]
    return totals


def quantile(totals: np.ndarray, q: float) -> Decimal:
    return Decimal(str(round(float(np.quantile(totals, q)), 2)))


def p_under(totals: np.ndarray, budget: Decimal) -> float:
    return round(float(np.mean(totals <= float(budget))), 3)
