"""Deterministic trip planner (the core; no AI).

Owner logic implemented here:
- Budget fit: "hard limit" means the sum of every line's high end fits;
  "wiggle room" means the plan fits in about 9 of 10 simulated price outcomes.
- Savings first: the first plan is a value plan. Then up to 3 "worth it"
  upgrades that still fit. A gifts & souvenirs allowance is always included.
- Ranking: interests first, then value (rating per dollar, quality floor 4.0),
  then distance. One hidden gem per day.
- Hidden costs in the total by default: sales tax, tips, transit between stops,
  water/snacks/extras. Getting there and back is an optional add-on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from voya.catalog import Catalog, Destination, Place, Route, haversine_km, load_catalog
from voya.cost.model import CostLine, CostSource, summarize
from voya.uncertainty import SimLine, p_under, quantile, seed_from, simulate

D = Decimal
WALK_KM = 1.2  # legs longer than this use transit where the city has a fare
QUALITY_FLOOR = 4.0
WIGGLE_QUANTILE = 0.90
HARD_QUANTILE = 0.97
MIN_UPGRADE = D(5)  # smaller deltas are swaps, not upgrades

SLOTS: dict[str, list[tuple[str, str]]] = {
    "relaxed": [("sight", "10:00"), ("lunch", "12:30"), ("sight", "14:30"), ("dinner", "18:30")],
    "balanced": [
        ("sight", "10:00"),
        ("lunch", "12:30"),
        ("sight", "14:00"),
        ("sight", "16:00"),
        ("dinner", "18:30"),
    ],
    "packed": [
        ("sight", "09:00"),
        ("sight", "10:45"),
        ("lunch", "12:30"),
        ("sight", "14:00"),
        ("sight", "15:45"),
        ("dinner", "18:30"),
        ("evening", "20:30"),
    ],
}


# ----------------------------------------------------------------- inputs ---


class PartyIn(BaseModel):
    adults: int = Field(1, ge=1, le=12)
    children: list[Literal["0-5", "6-12", "13-17"]] = Field(default_factory=list, max_length=11)

    @property
    def size(self) -> int:
        return self.adults + len(self.children)


class LodgingIn(BaseModel):
    status: Literal["auto", "none", "booked", "estimate"] = "auto"
    amount: Decimal | None = Field(None, ge=0)


class GettingThereIn(BaseModel):
    from_id: str | None = None
    mode: Literal["drive", "train"] = "drive"
    include_in_total: bool = False


class AnchorIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    day: int = Field(0, ge=0, le=29)
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_min: int = Field(120, ge=15, le=720)
    cost: Decimal = Field(D(0), ge=0)  # exact total for the party
    near_place_id: str | None = None


class PlanRequest(BaseModel):
    destination: str
    start_date: date
    days: int = Field(1, ge=1, le=30)
    budget: Decimal = Field(gt=0, le=1_000_000)
    firmness: Literal["hard", "wiggle"] = "wiggle"
    party: PartyIn = Field(default_factory=PartyIn)
    interests: list[str] = Field(default_factory=list, max_length=8)
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    lodging: LodgingIn = Field(default_factory=LodgingIn)
    getting_there: GettingThereIn = Field(default_factory=GettingThereIn)
    anchor: AnchorIn | None = None
    tip_pct: Decimal = Field(D(18), ge=0, le=50)
    gifts_pct: Decimal = Field(D(5), ge=0, le=50)
    gifts_amount: Decimal | None = Field(None, ge=0)
    overrides: dict[str, str] = Field(default_factory=dict)  # slot_id -> place_id
    skips: list[str] = Field(default_factory=list)  # slot ids the user removed
    exclude: list[str] = Field(default_factory=list)  # place ids never to use
    raining: bool = False

    @model_validator(mode="after")
    def _anchor_day(self) -> PlanRequest:
        if self.anchor and self.anchor.day >= self.days:
            raise ValueError("anchor.day must be within the trip")
        return self


# ------------------------------------------------------------ plan pieces ---


@dataclass
class Pick:
    slot_id: str
    day: int
    kind: str  # sight | lunch | dinner | evening | anchor
    time: str
    place: Place | None = None
    locked: bool = False  # chosen by the user (override) or the anchor
    gem_enforced: bool = False


@dataclass
class PlanLine:
    line_id: str
    day: int | None
    kind: str
    cost: CostLine
    parent_id: str | None = None
    rate: float = 0.0


@dataclass
class Fit:
    point: Decimal
    low: Decimal
    high: Decimal
    metric: Decimal
    p_under: float
    ok: bool


@dataclass
class Priced:
    picks: list[Pick]
    lines: list[PlanLine]
    fit: Fit
    getting_there: dict | None = None
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- helpers ---


def _minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _is_open(p: Place, start: str) -> bool:
    s = _minutes(start)
    return _minutes(p.open) <= s and s + p.duration_min <= _minutes(p.close) + 1


def _interest(p: Place, interests: set[str]) -> int:
    return min(len(set(p.tags) & interests), 2)


def _value(p: Place) -> float:
    return (p.rating or QUALITY_FLOOR) / max(float(p.price.point), 5.0)


def _rank_key(p: Place, interests: set[str], prev: tuple[float, float]) -> tuple:
    dist = haversine_km(prev, (p.lat, p.lng))
    return (-_interest(p, interests), -round(_value(p), 1), round(dist, 1), p.id)


def _passes_floor(p: Place) -> bool:
    return p.rating is None or p.rating >= QUALITY_FLOOR


def _slot_fits(p: Place, kind: str, time: str, raining: bool) -> bool:
    if not _is_open(p, time) or not _passes_floor(p):
        return False
    if raining and not p.indoor and kind in ("sight", "evening") and p.category != "food":
        return False
    if kind in ("lunch", "dinner"):
        return p.category == "food" and kind in p.meals
    if kind == "evening":
        return p.category != "food" and p.evening
    return p.category in ("attraction", "activity") and not p.evening


def _taken(p: Place, day: int, picks: list[Pick], skip: Pick | None = None) -> bool:
    """Sights are never repeated; restaurants may repeat on a different day."""
    for other in picks:
        if other is skip or other.place is None or other.place.id != p.id:
            continue
        if p.category != "food" or other.day == day:
            return True
    return False


def _observed(cat: Catalog) -> datetime:
    return datetime(2026, 11, 11, tzinfo=UTC) if cat.synthetic else datetime.now(UTC)


def _money(x: Decimal | float) -> Decimal:
    return D(str(x)).quantize(D("0.01"))


# --------------------------------------------------------------- choosing ---


def _anchor_loc(req: PlanRequest, dest: Destination) -> tuple[float, float]:
    if req.anchor and req.anchor.near_place_id:
        p = dest.place(req.anchor.near_place_id)
        if p:
            return (p.lat, p.lng)
    return dest.center


def _overlaps_anchor(req: PlanRequest, day: int, time: str, duration: int) -> bool:
    a = req.anchor
    if not a or a.day != day:
        return False
    s, e = _minutes(time), _minutes(time) + duration
    a_s, a_e = _minutes(a.start), _minutes(a.start) + a.duration_min
    return s < a_e and a_s < e


def choose(req: PlanRequest, dest: Destination) -> list[Pick]:
    interests = set(req.interests)
    excluded = set(req.exclude)
    picks: list[Pick] = []
    for day in range(req.days):
        prev = _anchor_loc(req, dest) if (req.anchor and req.anchor.day == day) else dest.center
        day_picks: list[Pick] = []
        for i, (kind, time) in enumerate(SLOTS[req.pace]):
            sid = f"d{day}-s{i}"
            pick = Pick(slot_id=sid, day=day, kind=kind, time=time)
            if sid in req.skips or _overlaps_anchor(req, day, time, 90):
                if sid not in req.skips:
                    continue  # the anchor occupies this time
                day_picks.append(pick)
                continue
            so_far = picks + day_picks
            forced = req.overrides.get(sid)
            if forced:
                p = dest.place(forced)
                if p and not _taken(p, day, so_far) and _slot_fits(p, kind, time, False):
                    pick.place, pick.locked = p, True
            if pick.place is None:
                cands = [
                    p
                    for p in dest.places
                    if p.id not in excluded
                    and not _taken(p, day, so_far)
                    and _slot_fits(p, kind, time, req.raining)
                ]
                if cands:
                    seen = {q.place.id for q in so_far if q.place}
                    pick.place = min(
                        cands, key=lambda p: (p.id in seen, *_rank_key(p, interests, prev))
                    )
            if pick.place:
                prev = (pick.place.lat, pick.place.lng)
            day_picks.append(pick)
        _enforce_gem(day_picks, picks, dest, excluded, interests, req.raining)
        if req.anchor and req.anchor.day == day:
            day_picks.append(Pick(f"d{day}-anchor", day, "anchor", req.anchor.start, locked=True))
        day_picks.sort(key=lambda p: _minutes(p.time))
        picks.extend(day_picks)
    return picks


def _enforce_gem(
    day: list[Pick],
    earlier: list[Pick],
    dest: Destination,
    excluded: set[str],
    interests: set[str],
    raining: bool,
) -> None:
    sights = [p for p in day if p.kind == "sight" and p.place]
    if not sights or any(p.place and p.place.hidden_gem for p in sights):
        return
    for pick in reversed(sights):
        if pick.locked:
            continue
        gems = [
            g
            for g in dest.places
            if g.hidden_gem
            and g.id not in excluded
            and not _taken(g, pick.day, earlier + day, skip=pick)
            and _slot_fits(g, "sight", pick.time, raining)
        ]
        if gems:
            g = min(gems, key=lambda p: _rank_key(p, interests, (p.lat, p.lng)))
            pick.place, pick.gem_enforced = g, True
            return


# ---------------------------------------------------------------- pricing ---


def _place_line(pick: Pick, size: int, obs: datetime) -> CostLine:
    p = pick.place
    assert p is not None
    qty = D(size) if p.price.unit == "person" else D(1)
    cat = "food" if p.category == "food" else p.category
    return CostLine(
        label=p.name,
        category=cat,  # type: ignore[arg-type]  # narrowed by Place.category
        amount=p.price.point * qty,
        low=p.price.low * qty,
        high=p.price.high * qty,
        currency="USD",
        source=p.price.source,
        observed_at=obs,
        confidence=p.price.confidence,
    )


def _derived(parent: CostLine, rate: Decimal, label: str, cat: str, src: CostSource) -> CostLine:
    return CostLine(
        label=label,
        category=cat,  # type: ignore[arg-type]
        amount=parent.amount * rate,
        low=parent.low * rate,
        high=parent.high * rate,
        currency="USD",
        source=src,
        observed_at=parent.observed_at,
        confidence=parent.confidence,
    )


def _exact(
    label: str, cat: str, amount: Decimal, src: CostSource, obs: datetime, conf: float = 1.0
) -> CostLine:
    if src is CostSource.USER_ACTUAL:
        return CostLine.actual(label, cat, amount, "USD", obs)  # type: ignore[arg-type]
    return CostLine(
        label=label,
        category=cat,
        amount=amount,
        low=amount,
        high=amount,  # type: ignore[arg-type]
        currency="USD",
        source=src,
        observed_at=obs,
        confidence=conf,
    )


def getting_there(
    req: PlanRequest, cat: Catalog, dest: Destination
) -> tuple[dict | None, CostLine | None]:
    g = req.getting_there
    if not g.from_id:
        return None, None
    route: Route | None = cat.route(g.from_id, dest.id)
    if route is None:
        return {"available": False, "note": "No route data from that place yet."}, None
    obs = _observed(cat)
    origin = cat.destination(g.from_id)
    if g.mode == "train" and route.train_fare is not None:
        amount = route.train_fare * req.party.size * 2
        line = _exact(
            "Train there and back", "getting_there", amount, CostSource.FARE_QUOTE, obs, 0.95
        )
        minutes = route.train_min
    else:
        state = origin.state if origin else dest.state
        fuel_price = cat.fuel_price_per_gallon.get(state, D("4.00"))
        gallons = D(str(2 * route.drive_km / (cat.default_mpg * 1.609)))
        vehicles = math.ceil(req.party.size / 5)
        amount = gallons * fuel_price * vehicles + route.parking_per_day * req.days * vehicles
        line = CostLine(
            label="Drive there and back (fuel, parking)",
            category="getting_there",
            amount=amount,
            low=amount * D("0.85"),
            high=amount * D("1.25"),
            currency="USD",
            source=CostSource.RULE,
            observed_at=obs,
            confidence=0.7,
        )
        minutes = route.drive_min
    info = {
        "available": True,
        "mode": g.mode if (g.mode == "train" and route.train_fare) else "drive",
        "est": str(line.amount),
        "low": str(line.low),
        "high": str(line.high),
        "minutes_one_way": minutes,
        "source": line.source.value,
        "included": g.include_in_total,
        "label": f"est. ${line.amount:,.0f} to get there and back",
    }
    return info, line


def price(req: PlanRequest, picks: list[Pick], dest: Destination, cat: Catalog) -> Priced:
    obs = _observed(cat)
    size = req.party.size
    rules = dest.rules
    lines: list[PlanLine] = []
    for day in range(req.days):
        prev: Pick | None = None
        prev_loc: tuple[float, float] | None = None
        legs = 0
        for pick in [p for p in picks if p.day == day]:
            if pick.kind == "anchor" and req.anchor:
                loc = _anchor_loc(req, dest)
                cost = _exact(
                    req.anchor.title, "activity", req.anchor.cost, CostSource.USER_ENTERED, obs
                )
                lines.append(PlanLine(pick.slot_id, day, "anchor", cost))
            elif pick.place:
                loc = (pick.place.lat, pick.place.lng)
                cost = _place_line(pick, size, obs)
                lines.append(PlanLine(pick.slot_id, day, "place", cost))
                if pick.place.category == "food" and rules.sales_tax_pct > 0:
                    rate = rules.sales_tax_pct / 100
                    lines.append(
                        PlanLine(
                            f"{pick.slot_id}-tax",
                            day,
                            "tax",
                            _derived(
                                cost,
                                rate,
                                f"est. sales tax ({rules.sales_tax_pct}%)",
                                "tax",
                                CostSource.RULE,
                            ),
                            parent_id=pick.slot_id,
                            rate=float(rate),
                        )
                    )
                if pick.place.sit_down and req.tip_pct > 0:
                    rate = req.tip_pct / 100
                    lines.append(
                        PlanLine(
                            f"{pick.slot_id}-tip",
                            day,
                            "tip",
                            _derived(
                                cost, rate, f"est. tip ({req.tip_pct}%)", "tip", CostSource.SETTING
                            ),
                            parent_id=pick.slot_id,
                            rate=float(rate),
                        )
                    )
            else:
                continue
            if (
                prev_loc is not None
                and rules.transit_fare > 0
                and haversine_km(prev_loc, loc) > WALK_KM
            ):
                legs += 1
                fare = rules.transit_fare * size
                lines.append(
                    PlanLine(
                        f"d{day}-t{legs}",
                        day,
                        "transit",
                        _exact(
                            f"Transit to {pick.place.name if pick.place else req.anchor.title if req.anchor else 'next stop'}",
                            "transit",
                            fare,
                            CostSource.FARE_QUOTE,
                            obs,
                            0.95,
                        ),
                    )
                )
            prev, prev_loc = pick, loc
        if rules.extras_per_person_day > 0:
            lines.append(
                PlanLine(
                    f"d{day}-extras",
                    day,
                    "extras",
                    _exact(
                        "Water, snacks, lockers (est.)",
                        "extras",
                        rules.extras_per_person_day * size,
                        CostSource.SETTING,
                        obs,
                    ),
                )
            )
    if rules.park_fee_vehicle > 0:
        vehicles = math.ceil(size / 5)
        lines.append(
            PlanLine(
                "park-fee",
                0,
                "park_fee",
                _exact(
                    f"Park entrance ({vehicles} vehicle{'s' if vehicles > 1 else ''})",
                    "park_fee",
                    rules.park_fee_vehicle * vehicles,
                    CostSource.FARE_QUOTE,
                    obs,
                    0.95,
                ),
            )
        )
    nights = req.days - 1
    status = req.lodging.status
    if status == "auto":
        status = "estimate" if nights > 0 else "none"
    if nights > 0 and status == "booked" and req.lodging.amount is not None:
        lines.append(
            PlanLine(
                "lodging",
                None,
                "lodging",
                _exact(
                    "Lodging (booked)", "lodging", req.lodging.amount, CostSource.USER_ENTERED, obs
                ),
            )
        )
    elif nights > 0 and status == "estimate":
        rooms = math.ceil(size / 4)
        n = D(nights * rooms)
        ln = rules.lodging_night
        lodge = CostLine(
            label=f"Lodging estimate ({nights} night{'s' if nights > 1 else ''})",
            category="lodging",
            amount=ln.point * n,
            low=ln.low * n,
            high=ln.high * n,
            currency="USD",
            # A planning range for a place the traveller will choose, not a random
            # price: the range comes from the city's lodging rule at 80% confidence.
            source=CostSource.RULE,
            observed_at=obs,
            confidence=0.8,
        )
        lines.append(PlanLine("lodging", None, "lodging", lodge))
        if rules.occupancy_tax_pct > 0:
            rate = rules.occupancy_tax_pct / 100
            lines.append(
                PlanLine(
                    "lodging-tax",
                    None,
                    "tax",
                    _derived(
                        lodge,
                        rate,
                        f"est. lodging tax ({rules.occupancy_tax_pct}%)",
                        "tax",
                        CostSource.RULE,
                    ),
                    parent_id="lodging",
                    rate=float(rate),
                )
            )
    gifts = req.gifts_amount if req.gifts_amount is not None else req.budget * req.gifts_pct / 100
    if gifts > 0:
        lines.append(
            PlanLine(
                "gifts",
                None,
                "gifts",
                _exact(
                    "Gifts & souvenirs (est. allowance)", "gifts", gifts, CostSource.SETTING, obs
                ),
            )
        )
    gt_info, gt_line = getting_there(req, cat, dest)
    if gt_line is not None and req.getting_there.include_in_total:
        lines.append(PlanLine("getting-there", None, "getting_there", gt_line))
    fit = evaluate(lines, req, cat)
    notes = []
    if req.party.children:
        notes.append(
            "Children are priced at adult rates unless a child price is known; many places are cheaper for kids."
        )
    return Priced(picks, lines, fit, gt_info, notes)


def evaluate(lines: list[PlanLine], req: PlanRequest, cat: Catalog) -> Fit:
    s = summarize([ln.cost for ln in lines], currency="USD")
    index = {ln.line_id: i for i, ln in enumerate(lines)}
    sims = [
        SimLine(
            low=float(ln.cost.low),
            high=float(ln.cost.high),
            confidence=ln.cost.confidence,
            category=ln.cost.category,
            parent=index.get(ln.parent_id) if ln.parent_id else None,
            rate=ln.rate,
        )
        for ln in lines
    ]
    totals = simulate(sims, seed_from(req.model_dump_json(), cat.version, len(lines)))
    # Hard limit: every line at its high end AND the 97th percentile must fit, so
    # low-confidence guesses (whose tails reach past their stated high) can't make
    # "hard" looser than "wiggle room".
    if req.firmness == "hard":
        metric = max(s.high_total, quantile(totals, HARD_QUANTILE))
    else:
        metric = quantile(totals, WIGGLE_QUANTILE)
    return Fit(
        point=s.point_total,
        low=s.low_total,
        high=s.high_total,
        metric=metric,
        p_under=p_under(totals, req.budget),
        ok=metric <= req.budget,
    )


# ------------------------------------------------------------- repair/upgr ---


def _per_person_high(p: Place) -> Decimal:
    return p.price.high


def repair(req: PlanRequest, priced: Priced, dest: Destination, cat: Catalog) -> Priced:
    """Swap or drop the costliest unlocked stops until the plan fits (or can't)."""
    for _ in range(60):
        if priced.fit.ok:
            return priced
        picks = priced.picks
        best: tuple[Decimal, int, Place | None] | None = None
        for i, pk in enumerate(picks):
            if pk.locked or not pk.place or pk.place.price.high == 0:
                continue
            cands = [
                p
                for p in dest.places
                if not _taken(p, pk.day, picks, skip=pk)
                and p.id not in req.exclude
                and _slot_fits(p, pk.kind, pk.time, req.raining)
                and _per_person_high(p) < _per_person_high(pk.place)
            ]
            if cands:
                alt = min(cands, key=lambda p: (_per_person_high(p), -(p.rating or 0)))
                saving = _per_person_high(pk.place) - _per_person_high(alt)
                choice: Place | None = alt
            elif pk.kind in ("sight", "evening"):
                saving, choice = _per_person_high(pk.place), None
            else:
                continue
            if best is None or saving > best[0]:
                best = (saving, i, choice)
        if best is None:
            return priced
        _, i, choice = best
        new_picks = [replace(p) for p in picks]
        new_picks[i].place = choice
        priced = price(req, new_picks, dest, cat)
    return priced


def worth_it(req: PlanRequest, priced: Priced, dest: Destination, cat: Catalog) -> list[dict]:
    if not priced.fit.ok:
        return []
    interests = set(req.interests)
    found: list[tuple[tuple, dict]] = []
    for i, pk in enumerate(priced.picks):
        if pk.locked or not pk.place:
            continue
        cur = pk.place
        best: tuple[tuple, dict] | None = None
        for alt in dest.places:
            if alt.id in req.exclude or alt.price.point <= cur.price.point:
                continue
            if _taken(alt, pk.day, priced.picks, skip=pk):
                continue
            if not _slot_fits(alt, pk.kind, pk.time, req.raining):
                continue
            if _interest(alt, interests) < _interest(cur, interests):
                continue
            if (alt.rating or 0) < (cur.rating or 0) - 0.2:
                continue
            trial = [replace(p) for p in priced.picks]
            trial[i].place, trial[i].locked = alt, True
            tp = price(req, trial, dest, cat)
            if not tp.fit.ok:
                continue
            delta = tp.fit.point - priced.fit.point
            if delta < MIN_UPGRADE:
                continue  # not a real upgrade, just a swap
            matched = sorted(set(alt.tags) & interests)
            why = (f"Matches {', '.join(matched)} · " if matched else "") + f"rated {alt.rating}"
            if alt.reviews and alt.reviews >= 5000:
                why += " · a local favourite"
            # Worth it = matches interests, clearly better rated, well loved.
            score = (
                _interest(alt, interests)
                + 2 * ((alt.rating or 0) - (cur.rating or 0))
                + math.log10(max(alt.reviews or 1, 1)) / 2
            )
            key = (-round(score, 3), delta)
            item = {
                "upgrade_id": f"{pk.slot_id}:{alt.id}",
                "slot_id": pk.slot_id,
                "slot_kind": pk.kind,
                "title": alt.name,
                "replaces": cur.name,
                "delta": str(_money(delta)),
                "new_total": str(tp.fit.point),
                "why": why,
                "fits": True,
            }
            if best is None or key < best[0]:
                best = (key, item)
        if best:
            found.append(best)
    found.sort(key=lambda kv: kv[0])
    out: list[dict] = []
    food = 0
    for _, item in found:
        is_food = item["slot_kind"] in ("lunch", "dinner")
        if is_food and food >= 2:
            continue  # keep the list varied: at most 2 meal upgrades
        food += is_food
        out.append(item)
        if len(out) == 3:
            break
    return out


# ------------------------------------------------------------------ public ---


class PlanError(ValueError):
    pass


def build(req: PlanRequest, cat: Catalog | None = None) -> dict:
    cat = cat or load_catalog()
    dest = cat.destination(req.destination)
    if dest is None:
        raise PlanError(f"'{req.destination}' isn't supported yet.")
    picks = choose(req, dest)
    priced = repair(req, price(req, picks, dest, cat), dest, cat)
    return render(req, priced, dest, cat, worth_it(req, priced, dest, cat))


def _line_dict(ln: PlanLine) -> dict:
    c = ln.cost
    return {
        "line_id": ln.line_id,
        "label": c.label,
        "category": c.category,
        "amount": str(c.amount),
        "low": str(c.low),
        "high": str(c.high),
        "source": c.source.value,
        "confidence": c.confidence,
        "is_estimate": c.is_estimate,
    }


def _why(pick: Pick, req: PlanRequest, prev: tuple[float, float] | None) -> str:
    p = pick.place
    if p is None:
        return ""
    bits = []
    matched = sorted(set(p.tags) & set(req.interests))
    if matched:
        bits.append("matches " + ", ".join(matched))
    if p.is_free:
        bits.append("free")
    if p.rating:
        bits.append(f"rated {p.rating}")
    if p.hidden_gem:
        bits.append("hidden gem")
    if prev:
        bits.append(f"{haversine_km(prev, (p.lat, p.lng)):.1f} km from last stop")
    if pick.locked:
        bits.append("your choice")
    return " · ".join(bits).capitalize()


def render(
    req: PlanRequest, priced: Priced, dest: Destination, cat: Catalog, upgrades: list[dict]
) -> dict:
    fit = priced.fit
    by_parent: dict[str, list[PlanLine]] = {}
    for ln in priced.lines:
        if ln.parent_id:
            by_parent.setdefault(ln.parent_id, []).append(ln)
    line_by_id = {ln.line_id: ln for ln in priced.lines}
    days = []
    for d in range(req.days):
        items = []
        prev = None
        for pick in [p for p in priced.picks if p.day == d]:
            ln = line_by_id.get(pick.slot_id)
            if pick.kind == "anchor" and req.anchor and ln:
                items.append(
                    {
                        "line_id": pick.slot_id,
                        "time": pick.time,
                        "kind": "anchor",
                        "title": req.anchor.title,
                        "category": "activity",
                        "why": "Your fixed plan",
                        "cost": _line_dict(ln),
                        "children": [],
                        "item_total": str(ln.cost.amount),
                    }
                )
                prev = _anchor_loc(req, dest)
                continue
            if not pick.place or not ln:
                if pick.slot_id in req.skips:
                    items.append(
                        {
                            "line_id": pick.slot_id,
                            "time": pick.time,
                            "kind": pick.kind,
                            "title": "Free time",
                            "category": "other",
                            "why": "You removed this stop",
                            "cost": None,
                            "children": [],
                            "item_total": "0.00",
                        }
                    )
                continue
            kids = by_parent.get(pick.slot_id, [])
            total = ln.cost.amount + sum((k.cost.amount for k in kids), D(0))
            p = pick.place
            items.append(
                {
                    "line_id": pick.slot_id,
                    "time": pick.time,
                    "kind": pick.kind,
                    "place_id": p.id,
                    "title": p.name,
                    "category": p.category,
                    "indoor": p.indoor,
                    "hidden_gem": p.hidden_gem,
                    "lat": p.lat,
                    "lng": p.lng,
                    "duration_min": p.duration_min,
                    "why": _why(pick, req, prev),
                    "cost": _line_dict(ln),
                    "children": [_line_dict(k) for k in kids],
                    "item_total": str(_money(total)),
                }
            )
            prev = (p.lat, p.lng)
        transit = [_line_dict(ln) for ln in priced.lines if ln.day == d and ln.kind == "transit"]
        day_total = sum((ln.cost.amount for ln in priced.lines if ln.day == d), D(0))
        days.append(
            {
                "day": d,
                "date": str(req.start_date + timedelta(days=d)),
                "items": items,
                "transit": transit,
                "day_total": str(_money(day_total)),
            }
        )
    s = summarize([ln.cost for ln in priced.lines], currency="USD")
    hidden = sum(
        (
            ln.cost.amount
            for ln in priced.lines
            if ln.cost.category in ("tax", "tip", "transit", "extras", "fee")
        ),
        D(0),
    )
    trip_lines = [
        _line_dict(ln) for ln in priced.lines if ln.day is None or ln.kind in ("extras", "park_fee")
    ]
    status = "ready" if fit.ok else "infeasible"
    out = {
        "status": status,
        "destination": {"id": dest.id, "name": dest.name, "kind": dest.kind},
        "demo_data": cat.synthetic,
        "data_notice": cat.notice if cat.synthetic else None,
        "headline": {
            "label": "Estimated total",
            "point": str(fit.point),
            "low": str(fit.low),
            "high": str(fit.high),
            "budget": str(_money(req.budget)),
            "firmness": req.firmness,
            "fit_value": str(fit.metric),
            "p_under_budget_est": fit.p_under,
            "you_could_keep": str(_money(max(req.budget - fit.point, D(0)))),
            "hidden_costs": str(_money(hidden)),
            "data_backed_share": s.data_backed_share,
            "is_estimate": s.is_estimate,
        },
        "worth_it": upgrades,
        "getting_there_optional": priced.getting_there,
        "days": days,
        "trip_lines": trip_lines,
        "notes": priced.notes,
    }
    if not fit.ok:
        out["gap"] = str(_money(fit.metric - req.budget))
        out["free_alternatives"] = [p.name for p in dest.places if p.is_free][:6]
    return out


def apply_upgrade(req: PlanRequest, upgrade_id: str) -> PlanRequest:
    slot_id, place_id = upgrade_id.split(":", 1)
    overrides = dict(req.overrides)
    overrides[slot_id] = place_id
    return req.model_copy(update={"overrides": overrides})


def priced_for(req: PlanRequest, cat: Catalog | None = None) -> tuple[Destination, Catalog, Priced]:
    """The repaired, priced plan for a request (used by tracking and the helper)."""
    cat = cat or load_catalog()
    dest = cat.destination(req.destination)
    if dest is None:
        raise PlanError(f"'{req.destination}' isn't supported yet.")
    return dest, cat, repair(req, price(req, choose(req, dest), dest, cat), dest, cat)


def slot_alternatives(
    req: PlanRequest,
    priced: Priced,
    dest: Destination,
    slot_id: str,
    *,
    cheaper: bool = False,
    tag: str | None = None,
    indoor: bool | None = None,
) -> list[Place]:
    """Places that could fill a slot instead of its current pick, best-ranked first."""
    pick = next((p for p in priced.picks if p.slot_id == slot_id), None)
    if pick is None or pick.kind == "anchor":
        return []
    cur = pick.place
    out = []
    for p in dest.places:
        if cur and p.id == cur.id or p.id in req.exclude:
            continue
        if _taken(p, pick.day, priced.picks, skip=pick) or not _slot_fits(
            p, pick.kind, pick.time, False
        ):
            continue
        if cheaper and cur and p.price.point >= cur.price.point:
            continue
        if tag and tag not in p.tags:
            continue
        if indoor is not None and p.indoor != indoor:
            continue
        out.append(p)
    prev = (cur.lat, cur.lng) if cur else dest.center
    return sorted(out, key=lambda p: _rank_key(p, set(req.interests), prev))
