"""Provider interface for commercial / open places data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PlaceStub:
    """Minimal place record safe to cache per provider terms."""

    provider: str
    external_id: str
    name: str
    lat: float  # ≤3 dp before persist
    lng: float
    category: str
    rating: float | None = None
    price_level: int | None = None
    observed_at: datetime | None = None


class PlacesProvider(Protocol):
    name: str

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]: ...

    def spend_usd(self) -> Decimal: ...
