# Progress

The living status of the build. Update it at the end of every session (see
`AGENTS.md` → "Session logging"). History lives in `docs/SESSION_LOG.md`.

**Last updated:** 2026-11-27 · branch **`feat/s04-demo-banner-per-area`** (base `dev` `ca838cb`)

## Done
- **NYC public slice (phase 1b):** Postgres when `DATABASE_URL` is a postgres
  URL (SQLite otherwise). Round trip passed against local Postgres 16.
  Foursquare place search client; live calls stay off until an API key, a
  monthly budget, and a per-call USD amount are set. A price level is not
  turned into dollars. Curated NYC first-week idea bank with seed rotation
  and "Show me another"; the only dollar amount is the cited MTA fare.
  Demo banner stays up when the catalog is synthetic or any cost is a type
  guess or a price-bucket mapping. `/metrics` counters. Static accessibility
  checks (labels, language, contrast, focus). Default suite: 130 passed,
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
- **Magic-link email through Amazon SES (local):** a real sign-in email was
  sent with `VOYA_DEV_SIGNIN=0` and the owner's SES SMTP credentials in a
  gitignored `.env`. Blank database settings now count as unset, and
  `.env.example` runs on SQLite out of the box.
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
  in `snakeenv` without touching `.venv`); `make help`. Ruff + strict mypy on
  all of `src/voya` (39 modules, including `api`, `agent`, and `planner`),
  scripts, and tests. GitHub Actions: `verify`, Postgres service job
  for `tests/test_p1_nyc.py`, Docker build; PR triggers include `uat` and `prod`.
  Label `auto-merge` workflow for same-repo PRs into `dev` (`docs/GITHUB_AUTOMATION.md`).

## Known limits
- **S04 demo banner is per destination:** `Destination.synthetic` (None inherits
  the catalog). A synthetic catalog still forces demo everywhere. `GET /v1/meta`
  adds `data_status` (`demo` or `cited`). A plan's `demo_data` follows only that
  plan's destination. The picker tags demo areas "Demo prices". The bundled
  catalog is still synthetic, so every area is demo until cited data lands.
- **Synthetic demo catalog still drives plans:** 3 cities + 2 parks, made-up
  names and prices. The idea bank does not replace plan prices.
- **Dev sign-in still returns a token** unless `VOYA_DEV_SIGNIN=0`. SES is in
  the sandbox: only verified recipients, 200 emails a day.
- **`make run` does not load `.env`.** Use `uvicorn voya.api:app --reload
  --port 8000 --env-file .env`.
- **Not deployed.** SQLite on a volume is the preview store. The image was
  not built in this environment (no Docker daemon).

## Next (suggested order)
1. **P0 finish:** owner enables ruleset checks `verify` + `postgres` + `docker` and
   **Automatically delete head branches** (see `docs/GITHUB_AUTOMATION.md`).
2. **P1 real data:** S05 cited place catalog, then S06–S10.
3. Owner answers for hosting, invite code, public URL, alarm amount, legal
   wording, and Foursquare key plus budget before live places or deploy.
4. UX redesign (React + Vite) stays later. Vectors, rituals, the learner,
   extra regions, Europe, and climate stay out of scope.

## Blocked / needs the owner
- Which hosting account should the private preview be deployed to?
- Request SES production access before the first tester (sandbox only sends to verified addresses).
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use?
- What is the Foursquare API key, the monthly budget in USD, and the USD to count per search? Live place search stays off until those are set. Real NYC place prices are not in the catalog, so the demo banner stays.
- Choosing the map provider (it depends on the data provider's terms).
