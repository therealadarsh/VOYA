# Verification log

Verifier and builder record milestone results here.

## M1 Foundations

**Status:** Done (core); full §11 coverage gates deferred to M2

**Done:**
- `docs/BUILD_PLAN.md`; branch `build/mvp`.
- `CostLine` extensions (units, evidence, half-life); `CostSummary` hidden/keep fields.
- `src/voya/pricing/` freshness + rules loaders; `src/voya/data/loaders.py`.
- Cited `data/` for Chicago, NYC, SF sales tax + transit; Yosemite + Indiana Dunes park fees.
- `docs/DATA_SOURCES.md`; policy/citation/traceability/secret scripts.
- Tests: `tests/test_m1_data.py` + existing 84 tests.

**Partial:**
- `make verify`: ruff/mypy/coverage gates not fully at plan §11 targets yet.
- `llm/` package split deferred (behaviour unchanged in `llm.py`).
- SF BART minimum fare and NPS dollar amounts flagged for owner spot-check against live pages.

**Owner logic: needs confirmation:**
- Using listed planning values where agencies publish "confirm on web" fares (MTA, BART).

**Commands (last run):**
```text
make test
scripts/check_data_citations.py
scripts/check_policy.py
```
