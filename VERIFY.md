# Verification log

## MVP ready (partial)

**Branch:** `build/mvp` · **Tests:** 91 offline · **`make verify`:** green

**Deployed URL:** not yet (see `docs/DEPLOY.md` for container build).

**Try first:** `make run` → plan Chicago weekend; set `VOYA_DEV_SIGNIN=0` to exercise magic-link flow in tests.

**Data strategy (2026-11-11):** `voya price-check` CLI, `owner_check` source, `providers/` fakes, coverage on `/v1/ops` (with token).

**Known gaps (honest):**
- Postgres/Alembic not wired (SQLite only).
- Playwright + axe not automated yet (`web/` React scaffold only).
- Full agent package split (`agent/loop.py` etc.) not done; behaviour lives in `agent.py`.
- `make eval` is a stub.
- Planner still uses synthetic **places**; **rules** (tax/transit/park fees) overlay cited `data/` when `VOYA_CITED_RULES=1` (default).

---

## M6 Polish

**Status:** Partial (React scaffold, DEPLOY.md, Dockerfile; E2E/Playwright pending)

## M5 AI helper

**Status:** Partial (`/v1/ops` exists; agent refactor deferred)

## M4 Accounts + spend

**Status:** Partial (magic link + `FakeMailer`, entitlements stub; Postgres deferred)

## M3 Discovery

**Status:** Done (existing `discover.py` + tests; area summaries unchanged)

## M2 Planner

**Status:** Done (cited rules overlay, examples, openapi stub, fare_quote transit)

## M1 Foundations

**Status:** Done · tag `mvp-m1`
