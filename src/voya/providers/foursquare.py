"""Foursquare Places search. Live calls stay off until a key and a budget exist.

Price levels are kept as levels. This module does not turn them into dollars.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from voya.providers.base import PlaceStub

SEARCH_URL = "https://places-api.foursquare.com/places/search"
API_VERSION = "2025-06-17"
_BLOCKED = (
    "What is the Foursquare API key, the monthly budget in USD, and the USD to count "
    "per search? Set FOURSQUARE_API_KEY, VOYA_PLACES_BUDGET_USD, and "
    "VOYA_PLACES_USD_PER_CALL, and set VOYA_PLACES_LIVE=1. Live place search stays off "
    "until those are set."
)


class PlacesUnavailable(RuntimeError):
    pass


class HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> Any: ...


def round_coord(value: float) -> float:
    return round(float(value), 3)


def dollars_from_level(_level: int | None) -> None:
    """A provider price level is not a dollar amount."""
    return


def live_blockers(environ: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    key = (env.get("FOURSQUARE_API_KEY") or "").strip()
    budget = (env.get("VOYA_PLACES_BUDGET_USD") or "").strip()
    per_call = (env.get("VOYA_PLACES_USD_PER_CALL") or "").strip()
    live = (env.get("VOYA_PLACES_LIVE") or "").strip().lower() in {"1", "true", "yes"}
    if key and budget and per_call and live:
        return []
    return [_BLOCKED]


@dataclass
class FoursquarePlaces:
    api_key: str
    budget_usd: Decimal
    usd_per_call: Decimal
    live: bool = False
    client: HttpClient | None = None
    spent: Decimal = field(default_factory=lambda: Decimal(0))
    name: str = "foursquare"

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]:
        if not self.live or not self.api_key:
            raise PlacesUnavailable(_BLOCKED)
        if self.spent + self.usd_per_call > self.budget_usd:
            raise PlacesUnavailable("The places budget for this period is used up.")
        if self.client is None:
            import httpx

            self.client = httpx.Client(timeout=10)
        response = self.client.get(
            SEARCH_URL,
            params={
                "query": query,
                "ll": f"{round_coord(near_lat):.3f},{round_coord(near_lng):.3f}",
                "limit": str(min(limit, 50)),
            },
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Places-Api-Version": API_VERSION,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        self.spent += self.usd_per_call
        observed = datetime.now(UTC)
        stubs: list[PlaceStub] = []
        for item in response.json().get("results", []):
            categories = item.get("categories") or []
            category = categories[0].get("name", "place") if categories else "place"
            level = item.get("price")
            stubs.append(
                PlaceStub(
                    provider=self.name,
                    external_id=str(item["fsq_place_id"]),
                    name=str(item.get("name") or "Place"),
                    lat=round_coord(float(item["latitude"])),
                    lng=round_coord(float(item["longitude"])),
                    category=str(category),
                    price_level=int(level) if isinstance(level, int) else None,
                    observed_at=observed,
                )
            )
        return stubs

    def spend_usd(self) -> Decimal:
        return self.spent


def from_env(environ: Mapping[str, str] | None = None) -> FoursquarePlaces:
    env = os.environ if environ is None else environ
    blockers = live_blockers(env)
    budget = Decimal((env.get("VOYA_PLACES_BUDGET_USD") or "0").strip() or "0")
    per_call = Decimal((env.get("VOYA_PLACES_USD_PER_CALL") or "0").strip() or "0")
    return FoursquarePlaces(
        api_key=(env.get("FOURSQUARE_API_KEY") or "").strip(),
        budget_usd=budget,
        usd_per_call=per_call,
        live=not blockers,
    )
