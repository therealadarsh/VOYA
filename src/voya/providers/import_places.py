"""Import places into the cache. The fake provider runs now. Foursquare stays off."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Protocol

from voya.providers.base import PlaceStub
from voya.providers.foursquare import PlacesUnavailable, live_blockers
from voya.store import Store

# docs/DATA_SOURCES.md: the fake provider keeps a row for one day.
FAKE_CACHE = timedelta(days=1)


class Searcher(Protocol):
    name: str

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]: ...


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def _coord(value: float) -> str:
    return f"{round(float(value), 3):.3f}"


def cache_until(provider: str, observed_at: datetime) -> datetime:
    if provider == "fake":
        return observed_at + FAKE_CACHE
    raise PlacesUnavailable(
        "docs/DATA_SOURCES.md does not state a Foursquare cache window, so live "
        "places are not stored. " + live_blockers({})[0]
    )


def import_search(
    provider: Searcher,
    store: Store,
    *,
    query: str,
    near_lat: float,
    near_lng: float,
    now: datetime,
    limit: int = 5,
) -> list[str]:
    """Upsert this search. Drop this provider's rows only after cache_until."""
    if provider.name == "foursquare":
        blockers = live_blockers()
        if blockers:
            raise PlacesUnavailable(blockers[0])
    seen: list[str] = []
    for stub in provider.search(query, near_lat=near_lat, near_lng=near_lng, limit=limit):
        observed = stub.observed_at or now
        place_id = f"{stub.provider}:{stub.external_id}"
        store.upsert_place(
            {
                "id": place_id,
                "name": stub.name,
                "category": stub.category,
                "tags": json.dumps(list(stub.tags)),
                "lat": _coord(stub.lat),
                "lng": _coord(stub.lng),
                "hours": stub.hours,
                "provider_ids": json.dumps({stub.provider: stub.external_id}),
                "source": stub.provider,
                "observed_at": _stamp(observed),
                "cache_until": _stamp(cache_until(stub.provider, observed)),
            }
        )
        seen.append(place_id)
    for row in store.places():
        if row["source"] != provider.name or row["id"] in seen:
            continue
        if datetime.fromisoformat(str(row["cache_until"])) <= now:
            store.delete_place(str(row["id"]))
    return seen
