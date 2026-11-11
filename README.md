# VOYA

**Status:** **94 tests** on **`main`** — cited rules, magic-link,
`voya price-check`, React scaffold in `web/`. Demo places until provider wiring.
[`VERIFY.md`](VERIFY.md) ·
[`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) · history: [`docs/SESSION_LOG.md`](docs/SESSION_LOG.md)

Plan a trip (one day or up to 30) to your budget, door to door. Every cost
carries a range, a source and a stated confidence, and is always labeled as
an estimate. During the trip, VOYA tracks what you spend and helps you get
back under budget.

> **Demo data.** The bundled catalog (`src/voya/catalog/demo.json`) is
> synthetic: made-up place names, prices, taxes and fares for 3 cities and
> 2 national parks. The app shows a "Demo prices" banner while it's in use.
> Real, cited data replaces it before any real use.

## Run it

```sh
uv sync                                   # Python 3.12 + dependencies
make run                                  # http://localhost:8000
make test                                 # 84 tests, no network, no AI tokens
```

Optional: set `OPENROUTER_API_KEY` (and `VOYA_LLM_MODEL_HELPER`) in `.env` to
let a model choose the helper's tools. Without a key, a built-in router does
the same job. Either way, deterministic code computes every number.

## What works

| Feature | Where |
|---|---|
| **Plan a trip** with honest ranges, hidden costs (sales tax, tips, transit, extras), a gifts & souvenirs allowance, multi-day lodging, and kids in the party | `planner.py`, `POST /v1/plans` |
| **Budget fit:** "hard limit" (fits even if prices run high) or "some wiggle room" (fits in about 9 of 10 simulated price scenarios) | `planner.evaluate`, `uncertainty.py` |
| **Savings first, then "Worth it?":** up to 3 upgrades that still fit | `planner.worth_it` |
| **Day trip / plan around a fixed activity** (e.g. a ball game) | `PlanRequest.anchor`, `getting_there` |
| **Getting there** as an optional add-on (drive or train) | `planner.getting_there` |
| **Discover:** "What can my budget do from here?" | `discover.py`, `POST /v1/discover` |
| **Track spend** with live status and ways to get back under | `tracking.py`, `/v1/plans/{id}/spend`, `/budget` |
| **Ask VOYA:** what now / cheaper / swap / ideas / why so expensive | `agent.py`, `/v1/plans/{id}/helper` |
| **Accounts:** plan without one; sign in to save; 18+; export / delete; opt-in memory | `api.py`, `store.py` |
| **Web app:** mobile-first, light and dark, no build step | `src/voya/web/` |

## Docs

- [`docs/CONCEPT_MAP.md`](docs/CONCEPT_MAP.md): where each agent-engineering
  concept lives in the code, the test that proves it, and a hands-on "try it".
- [`docs/MVP_TEST_GUIDE.md`](docs/MVP_TEST_GUIDE.md): what to try, what's
  intentionally missing.
- [`DECISIONS.md`](DECISIONS.md): one line per design choice.
- [`docs/PROGRESS.md`](docs/PROGRESS.md) and
  [`docs/SESSION_LOG.md`](docs/SESSION_LOG.md): what's done and what's next,
  with one summary per working session.
- [`AGENTS.md`](AGENTS.md): rules for AI coding tools working on this repo,
  including session logging.
