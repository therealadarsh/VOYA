"""Load cited tax, tip and product-setting rules from `data/`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field


class CitedRecord(BaseModel):
    """Every top-level value file in `data/` includes provenance."""

    synthetic: bool = False
    source: str = Field(min_length=1)
    observed_at: datetime
    quote: str = Field(min_length=1)
    url: str | None = None


class SalesTaxRule(CitedRecord):
    jurisdiction: str
    combined_rate: Decimal = Field(description="Combined sales tax rate as a decimal fraction")


class TransitFare(CitedRecord):
    agency: str
    mode: str
    full_fare_usd: Decimal
    label: str


class ParkFee(CitedRecord):
    park_code: str
    park_name: str
    fee_type: str
    amount_usd: Decimal
    unit: str


@dataclass(frozen=True)
class RuleTable:
    sales_tax: dict[str, SalesTaxRule]
    transit_fares: dict[str, TransitFare]
    park_fees: dict[str, ParkFee]


_CITATION_KEYS = ("synthetic", "source", "observed_at", "quote", "url")


def _repo_data() -> Path:
    return Path(__file__).resolve().parents[3] / "data"


def _citation_blob(raw: dict[str, object]) -> dict[str, object]:
    return {k: raw[k] for k in _CITATION_KEYS if k in raw}


def load_rule_tables(root: Path | None = None) -> RuleTable:
    base = root or _repo_data()
    sales: dict[str, SalesTaxRule] = {}
    for path in sorted((base / "rules" / "us" / "sales_tax").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        rule = SalesTaxRule.model_validate(raw)
        sales[rule.jurisdiction] = rule

    transit: dict[str, TransitFare] = {}
    for path in sorted((base / "cities").rglob("transit_fares.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        cite = _citation_blob(raw)
        for entry in raw.get("fares", []):
            fare = TransitFare.model_validate({**cite, **entry})
            key = f"{fare.agency}:{fare.mode}:{fare.label}".lower().replace(" ", "_")
            transit[key] = fare

    parks: dict[str, ParkFee] = {}
    for path in sorted((base / "parks").rglob("fees.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        cite = _citation_blob(raw)
        for entry in raw.get("fees", []):
            fee = ParkFee.model_validate({**cite, **entry})
            parks[fee.park_code] = fee

    return RuleTable(sales_tax=sales, transit_fares=transit, park_fees=parks)


def assert_all_cited(root: Path | None = None) -> int:
    """Return count of non-synthetic JSON roots; raise if provenance is missing."""
    base = root or _repo_data()
    count = 0
    seen: set[Path] = set()
    for path in sorted(base.rglob("*.json")):
        if path in seen:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("synthetic") is True:
            continue
        if "fares" in raw or "fees" in raw:
            for field in ("source", "observed_at", "quote"):
                if field not in raw:
                    raise ValueError(f"missing {field} in {path}")
            count += 1
            seen.add(path)
            continue
        for field in ("source", "observed_at", "quote"):
            if field not in raw:
                raise ValueError(f"missing {field} in {path}")
        count += 1
        seen.add(path)
    return count
