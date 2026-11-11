"""Load launch-area cited data from `data/` (M1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voya.pricing.rules import RuleTable, assert_all_cited, load_rule_tables

LAUNCH_CITIES = frozenset({"nyc", "sf", "chicago"})
LAUNCH_PARKS = frozenset({"yosemite", "indiana_dunes"})


@dataclass(frozen=True)
class DataBundle:
    rules: RuleTable
    cited_file_count: int
    cities: frozenset[str]
    parks: frozenset[str]


def load_data_bundle(root: Path | None = None) -> DataBundle:
    cited = assert_all_cited(root)
    rules = load_rule_tables(root)
    base = root or Path(__file__).resolve().parents[3] / "data"
    cities = frozenset(p.name for p in (base / "cities").iterdir() if p.is_dir())
    parks = frozenset(p.name for p in (base / "parks").iterdir() if p.is_dir())
    missing_cities = LAUNCH_CITIES - cities
    missing_parks = LAUNCH_PARKS - parks
    if missing_cities or missing_parks:
        raise FileNotFoundError(f"missing data dirs: cities={missing_cities} parks={missing_parks}")
    return DataBundle(rules=rules, cited_file_count=cited, cities=cities, parks=parks)
