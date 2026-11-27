# Progress

The living status of the build. Update it at the end of every session (see
`AGENTS.md` → "Session logging"). History lives in `docs/SESSION_LOG.md`.

**Last updated:** 2026-11-27 · branch **`feat/github-auto-merge`** (PR pending) · base `dev` (`bd8146b`)

## Done
- **NYC public slice (phase 1b):** Postgres when `DATABASE_URL` is a postgres
  URL (SQLite otherwise). Round trip passed against local Postgres 16.
  Foursquare place search client; live calls stay off until an API key, a
  monthly budget, and a per-call USD amount are set. A price level is not
  turned into dollars. Curated NYC first-week idea bank with seed rotation
  and "Show me another"; the only dollar amount is the cited MTA fare.
  Demo banner stays up when the catalog is synthetic or any cost is a type
  guess or a price-bucket mapping. `/metrics` counters. Static accessibility
  checks (labels, language, contrast, focus). Default suite: 123 passed,
  2 skipped (browser flow and Postgres, both opt-in). Browser flow passed
  with `VOYA_BROWSER=1`, including the idea rotation.
- **Private preview (phase 1a):** production settings that refuse to start
  until invite code, https URL, data directory, and SMTP are set; invite-code
  cookie gate; SMTP magic-link mail (dev sign-in unchanged); SQLite under
  `VOYA_DATA_DIR` plus `python -m voya.backup`; security headers and same-host
  POST check; draft Privacy and Terms pages (legal wording not supplied);
  Preview label and feedback stored in the database; `/healthz`, `/readyz`,
  JSON access logs; production `Dockerfile` and `docker-compose.yml`;
  deployment guide for a single Docker host and for AWS.
  Browser flow (plan, feedback, dev sign-in, save) passes when
  `VOYA_BROWSER=1`. Default suite: 112 passed, browser test skipped.
- **M1 foundations** (`build/mvp`): cited `data/` for 3 cities + 2 parks, `make verify`,
  CostLine extensions, pricing freshness + rules loaders, 88 tests.
- **Cost model** (`src/voya/cost/`): ranged, sourced, timestamped cost
  lines; plan totals; data-backed share.
- **Planner** (`planner.py`):
  - value plan first; ranking by interests → value → distance, with one
    hidden gem per day;
  - hidden costs (sales tax, tips, transit, extras);
  - gifts allowance;
  - multi-day lodging;
  - fixed-activity ("anchor") days;
  - optional getting-there estimate;
  - repair when over budget;
  - worth-it upgrades.
- **Budget fit** (`uncertainty.py`): hard limit, or wiggle room (fits about
  9 in 10 simulated price outcomes).
- **Discovery** (`discover.py`), **live spend tracking** with recovery
  options (`tracking.py`).
- **AI helper** (`agent.py`, `llm.py`):
  - typed tools, a bounded loop, a context digest;
  - budget guard, single-use proposals, output checks;
  - OpenRouter when configured, otherwise a built-in router.
- **Accounts:** dev sign-in, 18+, export, delete, opt-in memory.
- **Tracing** with redaction (`obs.py`).
- **Web app** (`src/voya/web/`): mobile-first, light/dark, no build step.
- **Tests:** 84 tests, no network, no tokens. Mutation-checked: budget fit,
  sales tax, hard-limit rule.
- **Docs:** `docs/AGENTIC_ENGINEERING.md` (living AI/agent register),
  `docs/README.md` (documentation index), `docs/REVIEW_GUIDE.md`,
  `docs/CONCEPT_MAP.md`, `docs/MVP_TEST_GUIDE.md`, `DECISIONS.md`.
- **CI / local verify (P0):** `Makefile` `RUN ?= uv run` (use `make verify RUN=`
  in `snakeenv` without touching `.venv`); `make help`. Ruff + mypy on all of
  `src/voya`, scripts, and tests (`api` / `agent` / `planner` mypy deferred in
  `pyproject.toml` until S03c). GitHub Actions: `verify`, Postgres service job
  for `tests/test_p1_nyc.py`, Docker build; PR triggers include `uat` and `prod`.
  Label `auto-merge` workflow for same-repo PRs into `dev` (`docs/GITHUB_AUTOMATION.md`).

## Known limits
- **Synthetic demo catalog still drives plans:** 3 cities + 2 parks, made-up
  names and prices. The demo banner stays because those costs are not cited.
  The idea bank does not replace plan prices.
- **Dev sign-in still returns a token.** Production sends email only when
  SMTP settings are present. No SMTP account is configured here.
- **Not deployed.** SQLite on a volume is the preview store. The image was
  not built in this environment (no Docker daemon).

## Next (suggested order)
1. **P0 finish:** owner enables ruleset checks `verify` + `postgres` + `docker` and
   **Automatically delete head branches** (see `docs/GITHUB_AUTOMATION.md`).
   **S03c:** strict mypy on `api.py`, `agent.py`, `planner.py`.
2. **P1 real data:** S04 demo banner per area, then cited place catalog (S05+).
3. Owner answers for hosting, SMTP, invite code, public URL, alarm amount, legal
   wording, and Foursquare key plus budget before live places or deploy.
4. UX redesign (React + Vite) stays later. Vectors, rituals, the learner,
   extra regions, Europe, and climate stay out of scope.

## Blocked / needs the owner
- Which hosting account should the private preview be deployed to?
- What SMTP host, port, username, password, and From address should magic-link email use?
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use?
- What is the Foursquare API key, the monthly budget in USD, and the USD to count per search? Live place search stays off until those are set. Real NYC place prices are not in the catalog, so the demo banner stays.
- Choosing the map provider (it depends on the data provider's terms).
