"""Place catalog: destinations, places, local rules and routes.

The bundled catalog (`demo.json`) is SYNTHETIC: made-up names and prices for
demos and tests. `Catalog.synthetic` is True for it, and the API and UI show a
"Demo prices" banner whenever it is in use. Real, cited data replaces it later.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voya.cost.model import CostSource

DEMO_PATH = Path(__file__).with_name("demo.json")


class PriceInfo(BaseModel):
    model_config = ConfigDict(frozen=True)
    low: Decimal
    point: Decimal
    high: Decimal
    source: CostSource
    confidence: float = Field(ge=0, le=1)
    unit: Literal["person", "group"] = "person"


class Place(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    category: Literal["attraction", "activity", "food"]
    tags: tuple[str, ...]
    lat: float
    lng: float
    open: str
    close: str
    duration_min: int
    rating: float | None
    reviews: int | None
    price: PriceInfo
    indoor: bool = False
    sit_down: bool = False
    meals: tuple[str, ...] = ()
    hidden_gem: bool = False
    evening: bool = False

    @property
    def is_free(self) -> bool:
        return self.price.high == 0


class LodgingNight(BaseModel):
    model_config = ConfigDict(frozen=True)
    low: Decimal
    point: Decimal
    high: Decimal


class Rules(BaseModel):
    model_config = ConfigDict(frozen=True)
    sales_tax_pct: Decimal
    occupancy_tax_pct: Decimal
    transit_fare: Decimal
    extras_per_person_day: Decimal
    lodging_night: LodgingNight
    park_fee_vehicle: Decimal


class Destination(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    kind: Literal["city", "park"]
    state: str
    tz: str
    center: tuple[float, float]
    rules: Rules
    places: tuple[Place, ...]

    def place(self, place_id: str) -> Place | None:
        return next((p for p in self.places if p.id == place_id), None)


class Route(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    from_id: str = Field(alias="from")
    to: str
    drive_km: float
    drive_min: int
    train_fare: Decimal | None = None
    train_min: int | None = None
    parking_per_day: Decimal = Decimal(0)


class Catalog(BaseModel):
    model_config = ConfigDict(frozen=True)
    synthetic: bool
    notice: str
    version: str
    destinations: tuple[Destination, ...]
    routes: tuple[Route, ...]
    fuel_price_per_gallon: dict[str, Decimal]
    default_mpg: int

    def destination(self, dest_id: str) -> Destination | None:
        return next((d for d in self.destinations if d.id == dest_id), None)

    def route(self, from_id: str, to_id: str) -> Route | None:
        return next((r for r in self.routes if r.from_id == from_id and r.to == to_id), None)


@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> Catalog:
    data = json.loads(Path(path or DEMO_PATH).read_text())
    cat = Catalog.model_validate(data)
    from voya.pricing.cited_rules import cited_rules_enabled, overlay_rules

    if cited_rules_enabled():
        cat = overlay_rules(cat)
    return cat


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))
