"""Curated first-week ideas. Costs are attached only from cited files."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

_IDEAS = Path(__file__).resolve().parents[2] / "data" / "ideas" / "nyc.json"
_NYC_FARE = Path(__file__).resolve().parents[2] / "data" / "cities" / "nyc" / "transit_fares.json"


@lru_cache(maxsize=1)
def _nyc() -> dict[str, Any]:
    raw = json.loads(_IDEAS.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("NYC idea file is not an object")
    return cast(dict[str, Any], raw)


def nyc_transit() -> dict[str, Any] | None:
    """The cited subway fare, or None when that file is missing a fare."""
    if not _NYC_FARE.is_file():
        return None
    raw = json.loads(_NYC_FARE.read_text(encoding="utf-8"))
    fares = raw.get("fares") or []
    if not fares:
        return None
    fare = fares[0]
    return {
        "label": fare["label"],
        "amount": fare["full_fare_usd"],
        "source": raw["source"],
        "url": raw.get("url"),
        "observed_at": raw["observed_at"],
        "quote": raw["quote"],
        "is_estimate": True,
    }


def _sets() -> list[dict[str, Any]]:
    sets = _nyc()["sets"]
    if not isinstance(sets, list):
        raise TypeError("idea sets")
    return cast(list[dict[str, Any]], sets)


def select_set(seed: str) -> dict[str, Any]:
    sets = _sets()
    digest = hashlib.sha256(seed.encode()).digest()
    index = int.from_bytes(digest[:4], "big") % len(sets)
    return sets[index]


def next_set(current_id: str) -> dict[str, Any]:
    sets = _sets()
    ids = [item["id"] for item in sets]
    if current_id not in ids:
        return sets[0]
    return sets[(ids.index(current_id) + 1) % len(sets)]


def _view(chosen: dict[str, Any], days: int) -> dict[str, Any]:
    count = min(max(days, 1), 7)
    return {
        "city": "nyc",
        "set_id": chosen["id"],
        "days": chosen["days"][:count],
        "transit": nyc_transit(),
        "note": "Place names only. A cost is shown only when a cited source is attached.",
    }


def ideas_for(seed: str, days: int = 1) -> dict[str, Any]:
    return _view(select_set(seed), days)


def ideas_after(current_id: str, days: int = 1) -> dict[str, Any]:
    return _view(next_set(current_id), days)
