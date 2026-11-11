# Build plan (M1–M6)

Source of truth for milestones: `.voya-private/PLAN.md` (owner). This file is the
engineer's execution checklist: ~10 lines per milestone, plus provider choices.

**Branch:** `build/mvp` · tags: `mvp-m1` … `mvp-m6`

## Providers (recorded in `DECISIONS.md` and `docs/DATA_SOURCES.md`)

| Role | Choice | Why |
|---|---|---|
| **Places (commercial, ≤$50 one-time)** | **Foursquare Places API** | Fits a small launch-enrichment budget; field-level caching documented in their terms; fakes in tests. Google Places deferred if terms or spend don’t fit. |
| **Places (open)** | OpenStreetMap (Overpass), NPS API, RIDB | Free, cited; OSM in its own table when derived DBs appear. |
| **Transit fares** | Official GTFS/fare pages: CTA, MTA, BART, Muni/SF | `fare_quote` lines; no scraping. |
| **Runtime AI** | **OpenRouter** | One key; helper `openrouter/google/gemini-2.5-flash` (capable, low cost); narration `openrouter/openai/gpt-4o-mini` (cheaper copy). Override via `VOYA_LLM_MODEL_*`. |
| **Maps (M6 UI)** | MapLibre GL + compliant tiles | No competitor-map display of Google-only content. |
| **Second launch park** | **Indiana Dunes National Park (INDU)** | Reachable from Chicago; fees/alerts via NPS API. |

## M1 Foundations (days 1–2)

1. `make verify`: uv lock, ruff, mypy (money), pytest (offline), policy/citation/secret scripts.
2. Extend `CostLine` + `CostSummary` (units, evidence, half-life, gifts/hidden hooks).
3. `src/voya/pricing/`: freshness widening, rules loaders (tax, tip setting).
4. `data/`: cited sales tax + transit fares + park fees for NYC, SF, Chicago, Yosemite, Indiana Dunes.
5. `docs/DATA_SOURCES.md` terms matrix + attribution rules.
6. `src/voya/data/loaders.py` loads cited JSON; tests prove no uncited values in `data/`.
7. LLMClient package layout (`llm/`); budgets + tracing unchanged behaviour, tests green.
8. `VERIFY.md` M1 section; tag `mvp-m1` when verify passes.

## M2 Planner (days 3–5)

1. Refactor planner under `planner/`; F1 + F2 contracts vs OpenAPI examples.
2. OR-Tools CP-SAT scheduling slice where needed; keep deterministic golden tests.
3. Guard property test + MC <150 ms; MVP-PLAN-* and S-01..S-05, S-11..S-15, S-23–24.
4. Cited city/park place seeds (not synthetic banner) behind feature flag or env.
5. Tag `mvp-m2`.

## M3 Discovery (day 6)

1. Area summaries; `POST /v1/discover` MVP-DISC-*; ≤3 live provider calls.
2. Getting-there add-on wired; S-21 honest out-of-area.
3. Tag `mvp-m3`.

## M4 Accounts + spend (days 7–8)

1. Magic-link sign-in (fake email in tests); 18+ gate; export/delete.
2. F4 live budget, recovery, idempotent spend; Postgres + Alembic (SQLite dev fallback).
3. Tag `mvp-m4`.

## M5 AI helper (days 9–10)

1. Agent package split: loop, context, tools, approvals; ten concepts in CONCEPT_MAP.
2. F5 helper + `/ops`; S-06..S-08, S-16–17, S-20.
3. Tag `mvp-m5`.

## M6 Polish, evals, deploy (days 11–14)

1. React + Vite + TS web; section 8 screens; Playwright + axe.
2. `make eval`; AWS deploy + $20 budget alarm; `docs/DEPLOY.md`.
3. E2E path discover → plan → worth-it → save → spend → helper → summary.
4. Tag `mvp-m6`; `VERIFY.md` “MVP ready” note.
