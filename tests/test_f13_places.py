"""The places cache fills from the fake provider and leaves Foursquare blocked."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from voya.ideas import IdeaOption
from voya.providers.base import PlaceStub
from voya.providers.fake import FakePlaces
from voya.providers.foursquare import PlacesUnavailable
from voya.providers.import_places import import_search
from voya.store import Store

_NOW = datetime(2026, 11, 27, 18, 0, tzinfo=UTC)


def _stub(external_id: str, name: str, *, observed_at: datetime = _NOW) -> PlaceStub:
    return PlaceStub(
        provider="fake",
        external_id=external_id,
        name=name,
        lat=40.713,
        lng=-74.006,
        category="walk",
        observed_at=observed_at,
        tags=("sample",),
        hours=None,
    )


class _Scripted:
    name = "fake"

    def __init__(self, stubs: list[PlaceStub]) -> None:
        self.stubs = stubs

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]:
        return self.stubs[:limit]


class _Foursquare:
    name = "foursquare"

    def search(
        self, query: str, *, near_lat: float, near_lng: float, limit: int = 5
    ) -> list[PlaceStub]:
        raise AssertionError("live search must not run")


def test_fake_import_updates_without_duplicating(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "t.db"))
    import_search(
        FakePlaces(),
        store,
        query="pier",
        near_lat=40.71281,
        near_lng=-74.00641,
        now=_NOW,
    )
    import_search(
        FakePlaces(),
        store,
        query="bridge",
        near_lat=40.71281,
        near_lng=-74.00641,
        now=_NOW,
    )
    rows = store.places()
    assert len(rows) == 1
    assert rows[0]["id"] == "fake:fake-1"
    assert rows[0]["name"] == "Bridge (demo)"
    assert rows[0]["lat"] == "40.713"
    assert rows[0]["lng"] == "-74.006"
    assert rows[0]["source"] == "fake"
    assert "price" not in rows[0]
    option = IdeaOption(
        "sample-1",
        "Bridge",
        rows[0]["id"],
        ("sample",),
        False,
        60,
        "A sample stop.",
        "sample",
    )
    assert option.place_key() == "fake:fake-1"


def test_expired_rows_refresh_or_drop(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "t.db"))
    both = _Scripted([_stub("a", "First"), _stub("b", "Second")])
    import_search(both, store, query="walk", near_lat=40.713, near_lng=-74.006, now=_NOW)
    assert {row["id"] for row in store.places()} == {"fake:a", "fake:b"}
    kept = _Scripted([_stub("a", "First")])
    import_search(
        kept,
        store,
        query="walk",
        near_lat=40.713,
        near_lng=-74.006,
        now=_NOW + timedelta(hours=1),
    )
    assert {row["id"] for row in store.places()} == {"fake:a", "fake:b"}
    later = _NOW + timedelta(days=2)
    refreshed = _Scripted([_stub("a", "First again", observed_at=later)])
    import_search(refreshed, store, query="walk", near_lat=40.713, near_lng=-74.006, now=later)
    rows = {row["id"]: row for row in store.places()}
    assert list(rows) == ["fake:a"]
    assert rows["fake:a"]["name"] == "First again"
    assert rows["fake:a"]["cache_until"].startswith("2026-11-30")


def test_foursquare_import_stays_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "FOURSQUARE_API_KEY",
        "VOYA_PLACES_BUDGET_USD",
        "VOYA_PLACES_USD_PER_CALL",
        "VOYA_PLACES_LIVE",
    ):
        monkeypatch.delenv(name, raising=False)
    store = Store(str(tmp_path / "t.db"))
    with pytest.raises(PlacesUnavailable, match="FOURSQUARE_API_KEY"):
        import_search(
            _Foursquare(),
            store,
            query="museum",
            near_lat=40.713,
            near_lng=-74.006,
            now=_NOW,
        )
    assert store.places() == []
