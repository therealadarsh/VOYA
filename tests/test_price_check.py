from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from voya.cost import CostLine, CostSource
from voya.curate.price_check import (
    PriceCheckEntry,
    approve_price_check,
    coverage_ratio,
    load_pending,
    submit_price_check,
)

T0 = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def checks_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("voya.curate.price_check._store_path", lambda: tmp_path / "entries.jsonl")
    return tmp_path / "entries.jsonl"


def test_submit_and_approve(checks_file):
    e = PriceCheckEntry(
        id="pc_test1",
        place_name="Pilsen Taqueria",
        city="Chicago",
        item="taco plate",
        amount=Decimal("12"),
        method="visit",
        observed_at=T0,
    )
    submit_price_check(e)
    assert len(load_pending("Chicago")) == 1
    assert approve_price_check("pc_test1")
    assert load_pending("Chicago") == []


def test_owner_check_counts_as_data_backed():
    line = CostLine(
        label="Lunch",
        category="food",
        amount=Decimal("12"),
        low=Decimal("12"),
        high=Decimal("14"),
        currency="USD",
        source=CostSource.OWNER_CHECK,
        observed_at=T0,
        confidence=0.9,
    )
    assert line.is_data_backed


def test_coverage_ratio(checks_file):
    e = PriceCheckEntry(
        id="pc_a",
        place_name="Art Institute",
        city="Chicago",
        item="admission",
        amount=Decimal("30"),
        method="official_page",
        source_url="https://example.org/admission",
        observed_at=T0,
    )
    submit_price_check(e)
    assert approve_price_check("pc_a")
    cov = coverage_ratio(
        city="Chicago",
        planned_place_names=["Art Institute of Illinois", "Lunch spot"],
    )
    assert cov == pytest.approx(0.5)
