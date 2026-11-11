"""`voya price-check` — owned price evidence (plan: no scraping)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Method = Literal["official_page", "phone", "visit", "receipt", "other"]


class PriceCheckEntry(BaseModel):
    """One approved or pending owned-price record."""

    id: str
    place_name: str
    city: str
    item: str
    amount: Decimal
    currency: str = "USD"
    low: Decimal | None = None
    high: Decimal | None = None
    method: Method
    source_url: str | None = None
    note: str | None = Field(None, max_length=500)
    observed_at: datetime
    status: Literal["pending", "approved"] = "pending"
    synthetic: bool = False

    def to_evidence_quote(self) -> str:
        bits = [self.item, f"${self.amount}"]
        if self.note:
            bits.append(self.note[:120])
        return " · ".join(bits)


def _store_path() -> Path:
    root = Path(__file__).resolve().parents[3] / "data" / "owner_checks"
    root.mkdir(parents=True, exist_ok=True)
    return root / "entries.jsonl"


def submit_price_check(entry: PriceCheckEntry) -> None:
    path = _store_path()
    line = entry.model_dump(mode="json")
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, default=str) + "\n")


def load_pending(city: str | None = None) -> list[PriceCheckEntry]:
    path = _store_path()
    if not path.exists():
        return []
    out: list[PriceCheckEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        e = PriceCheckEntry.model_validate(json.loads(raw))
        if e.status != "pending":
            continue
        if city and e.city.lower() != city.lower():
            continue
        out.append(e)
    return out


def approve_price_check(entry_id: str) -> bool:
    path = _store_path()
    if not path.exists():
        return False
    rows: list[dict] = []
    found = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        if obj.get("id") == entry_id and obj.get("status") == "pending":
            obj["status"] = "approved"
            found = True
        rows.append(obj)
    if found:
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return found


def approved_for_city(city: str) -> list[PriceCheckEntry]:
    path = _store_path()
    if not path.exists():
        return []
    out: list[PriceCheckEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        e = PriceCheckEntry.model_validate(json.loads(raw))
        if e.status == "approved" and e.city.lower() == city.lower():
            out.append(e)
    return out


def coverage_ratio(*, city: str, planned_place_names: list[str]) -> float | None:
    """Share of planned stops with approved owner_check evidence (by name match)."""
    if not planned_place_names:
        return None
    approved = approved_for_city(city)
    if not approved:
        return 0.0
    names = {a.place_name.lower() for a in approved}
    hits = sum(1 for p in planned_place_names if any(p.lower() in n or n in p.lower() for n in names))
    return hits / len(planned_place_names)
