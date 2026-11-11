"""Budget-first discovery: "What can I do with $X from here?"."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from voya.catalog import load_catalog
from voya.planner import PartyIn, PlanRequest, build

MAX_DAY_TRIP_MIN = 180  # one way, door to door


class DiscoverRequest(BaseModel):
    from_id: str | None = None
    start_date: date
    days: int = Field(1, ge=1, le=30)
    budget: Decimal = Field(gt=0, le=1_000_000)
    firmness: Literal["hard", "wiggle"] = "wiggle"
    party: PartyIn = Field(default_factory=PartyIn)
    interests: list[str] = Field(default_factory=list, max_length=8)
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"


def discover(req: DiscoverRequest) -> dict:
    cat = load_catalog()
    options = []
    for dest in cat.destinations:
        if req.from_id and dest.id != req.from_id:
            route = cat.route(req.from_id, dest.id)
            if route is None or (req.days == 1 and route.drive_min > MAX_DAY_TRIP_MIN):
                continue
            kind = "day trip" if req.days == 1 else "trip"
            minutes = route.drive_min
        else:
            if req.from_id and dest.id == req.from_id:
                kind, minutes = ("city day" if req.days == 1 else "stay"), 0
            else:
                kind, minutes = ("city day" if req.days == 1 else "trip"), None
        preq = PlanRequest(
            destination=dest.id, start_date=req.start_date, days=req.days, budget=req.budget,
            firmness=req.firmness, party=req.party, interests=req.interests, pace=req.pace,
            getting_there={"from_id": req.from_id if (req.from_id and req.from_id != dest.id) else None},
        )
        plan = build(preq, cat)
        h = plan["headline"]
        items = [it for d in plan["days"] for it in d["items"] if it.get("place_id")]
        match = sum(1 for it in items if "matches" in (it.get("why") or "").lower())
        options.append({
            "destination": dest.id, "name": dest.name, "kind": kind, "fits": plan["status"] == "ready",
            "est_total": h["point"], "range": [h["low"], h["high"]],
            "p_under_budget_est": h["p_under_budget_est"], "you_could_keep": h["you_could_keep"],
            "gap": plan.get("gap"), "minutes_one_way": minutes,
            "getting_there_optional": plan.get("getting_there_optional"),
            "highlights": [it["title"] for it in items if it["category"] != "food"][:3],
            "interest_matches": match,
            "plan_request": preq.model_dump(mode="json"),
        })
    options.sort(key=lambda o: (not o["fits"], -o["interest_matches"],
                                -Decimal(o["you_could_keep"]), o["minutes_one_way"] or 0))
    return {"options": options[:6], "demo_data": cat.synthetic, "is_estimate": True,
            "empty_note": None if any(o["fits"] for o in options)
            else "Nothing fits this budget yet. Here are the closest options and how far over they are."}
