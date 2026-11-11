"""Offline places provider for tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from voya.providers.base import PlaceStub

D = Decimal


class FakePlaces:
    name = "fake"

    def __init__(self) -> None:
        self._calls = 0

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]:
        self._calls += 1
        now = datetime.now(tz=UTC)
        return [
            PlaceStub(
                provider="fake",
                external_id="fake-1",
                name=f"{query.title()} (demo)",
                lat=round(near_lat, 3),
                lng=round(near_lng, 3),
                category="attraction",
                rating=4.5,
                price_level=2,
                observed_at=now,
            )
        ][:limit]

    def spend_usd(self) -> D:
        return D(0)
