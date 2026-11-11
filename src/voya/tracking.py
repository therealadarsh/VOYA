"""Live budget during a trip: what's spent, what's left, and how to get back under."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from voya.catalog import Catalog
from voya.planner import (
    WIGGLE_QUANTILE,
    HARD_QUANTILE,
    PlanLine,
    PlanRequest,
    Priced,
    priced_for,
    slot_alternatives,
)
from voya.uncertainty import SimLine, quantile, seed_from, simulate

D = Decimal
CATEGORIES = ("food", "attraction", "activity", "transit", "lodging", "gifts", "extras", "other")
_CAT_WORDS = {
    "food": r"lunch|dinner|breakfast|coffee|food|snack|drink|meal|pizza|burger|tacos?|ramen",
    "transit": r"train|subway|bus|uber|lyft|taxi|metro|fare|ride|transit|parking|gas|fuel",
    "attraction": r"ticket|museum|entry|admission|tour|park",
    "gifts": r"gift|souvenir|shirt|magnet|present",
    "lodging": r"hotel|hostel|airbnb|motel|room|lodging",
}


def parse_spend_text(text: str) -> tuple[Decimal, str] | None:
    """'lunch was 23.40' -> (23.40, 'food'). Deterministic; returns None if no amount."""
    m = re.search(r"\$?\s*(\d{1,6}(?:[.,]\d{1,2})?)", text)
    if not m:
        return None
    try:
        amount = D(m.group(1).replace(",", "."))
    except InvalidOperation:
        return None
    low = text.lower()
    cat = next((c for c, pat in _CAT_WORDS.items() if re.search(pat, low)), "other")
    return amount, cat


def _remaining(priced: Priced, done: set[str]) -> list[PlanLine]:
    return [
        ln for ln in priced.lines if ln.line_id not in done and (ln.parent_id or "") not in done
    ]


def _metric(lines: list[PlanLine], req: PlanRequest, cat: Catalog) -> tuple[Decimal, Decimal]:
    """(point, budget-fit metric) for the remaining lines."""
    point = sum((ln.cost.amount for ln in lines), D(0))
    high = sum((ln.cost.high for ln in lines), D(0))
    index = {ln.line_id: i for i, ln in enumerate(lines)}
    sims = [
        SimLine(
            float(ln.cost.low),
            float(ln.cost.high),
            ln.cost.confidence,
            ln.cost.category,
            index.get(ln.parent_id) if ln.parent_id else None,
            ln.rate,
        )
        for ln in lines
    ]
    totals = simulate(sims, seed_from(req.model_dump_json(), cat.version, "live", len(lines)))
    if req.firmness == "hard":
        return point, max(high, quantile(totals, HARD_QUANTILE))
    return point, quantile(totals, WIGGLE_QUANTILE)


def budget_status(req: PlanRequest, spends: list[dict]) -> dict:
    dest, cat, priced = priced_for(req)
    spent = sum((D(s["amount"]) for s in spends), D(0))
    done = {s["line_id"] for s in spends if s.get("line_id")}
    remaining = _remaining(priced, done)
    point, metric = _metric(remaining, req, cat)
    projected_point = spent + point
    projected_fit = spent + metric
    over_lines = [
        s["line_id"]
        for s in spends
        if s.get("line_id")
        and any(
            ln.line_id == s["line_id"]
            and D(s["amount"])
            > ln.cost.high
            + sum((k.cost.high for k in priced.lines if k.parent_id == ln.line_id), D(0))
            for ln in priced.lines
        )
    ]
    at_risk = projected_fit > req.budget or bool(over_lines)
    out = {
        "budget": str(req.budget),
        "spent": str(spent),
        "planned_remaining_est": str(point.quantize(D("0.01"))),
        "projected_total_est": str(projected_point.quantize(D("0.01"))),
        "projected_fit_value": str(projected_fit.quantize(D("0.01"))),
        "you_could_keep": str(max(req.budget - projected_point, D(0)).quantize(D("0.01"))),
        "status": "at_risk" if at_risk else "on_track",
        "over_estimate_lines": over_lines,
        "recovery": [],
        "is_estimate": True,
    }
    if at_risk:
        out["recovery"] = recovery_options(req, priced, dest, done)
        if not out["recovery"]:
            out["recovery_note"] = (
                "Everything left is already at its cheapest. Free stops or a "
                "cheaper meal you pick yourself are the remaining ways to save."
            )
    return out


def recovery_options(req: PlanRequest, priced: Priced, dest, done: set[str]) -> list[dict]:
    """Up to 3 changes to remaining stops that save the most money."""
    opts = []
    for pick in priced.picks:
        if pick.slot_id in done or pick.locked or not pick.place or pick.place.price.point == 0:
            continue
        alts = slot_alternatives(req, priced, dest, pick.slot_id, cheaper=True)
        size = req.party.size
        if alts:
            alt = min(alts, key=lambda p: (p.price.point, -(p.rating or 0)))
            saving = (pick.place.price.point - alt.price.point) * size
            opts.append(
                {
                    "slot_id": pick.slot_id,
                    "action": "swap",
                    "to_place_id": alt.id,
                    "summary": f"Swap {pick.place.name} for {alt.name}",
                    "saving_est": str(saving.quantize(D("0.01"))),
                }
            )
        elif pick.kind in ("sight", "evening"):
            saving = pick.place.price.point * size
            opts.append(
                {
                    "slot_id": pick.slot_id,
                    "action": "skip",
                    "to_place_id": None,
                    "summary": f"Skip {pick.place.name}",
                    "saving_est": str(saving.quantize(D("0.01"))),
                }
            )
    gifts = next((ln.cost.amount for ln in priced.lines if ln.line_id == "gifts"), D(0))
    if gifts > 0:
        opts.append(
            {
                "slot_id": "gifts",
                "action": "gifts",
                "to_place_id": None,
                "summary": "Drop the gifts & souvenirs allowance",
                "saving_est": str(gifts.quantize(D("0.01"))),
            }
        )
    opts.sort(key=lambda o: -D(o["saving_est"]))
    return opts[:3]


def apply_recovery(
    req: PlanRequest, slot_id: str, action: str, to_place_id: str | None
) -> PlanRequest:
    if action == "gifts":
        return req.model_copy(update={"gifts_amount": D(0)})
    if action == "skip":
        return req.model_copy(update={"skips": sorted({*req.skips, slot_id})})
    overrides = dict(req.overrides)
    if to_place_id:
        overrides[slot_id] = to_place_id
    return req.model_copy(update={"overrides": overrides})
