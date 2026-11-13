# Progress

The living status of the build. Update it at the end of every session (see
`AGENTS.md` → "Session logging"). History lives in `docs/SESSION_LOG.md`.

**Last updated:** 2026-11-13 · branch **`cursor/phase-1a-private-preview-3eef`** · private preview

## Done
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
- **Docs:** `docs/CONCEPT_MAP.md`, `docs/MVP_TEST_GUIDE.md`, `DECISIONS.md`.

## Known limits
- **Synthetic demo catalog only:** 3 cities + 2 parks, made-up names and
  prices, with a "Demo prices" banner.
- **Dev sign-in still returns a token.** Production sends email only when
  SMTP settings are present. No SMTP account is configured here.
- **Not deployed.** SQLite on a volume is the preview store. The image was
  not built in this environment (no Docker daemon).

## Next (suggested order)
1. **Phase 1b, public MVP for NYC:** Postgres, places pipeline, curated
   first-week idea bank, cited NYC costs (demo banner stays until every cost
   has a source), monitoring, accessibility check.
2. UX redesign (React + Vite) stays later. Vectors, rituals, the learner,
   extra regions, Europe, and climate stay out of scope.

## Blocked / needs the owner
- Which hosting account should the private preview be deployed to?
- What SMTP host, port, username, password, and From address should magic-link email use?
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use?
- Choosing the places-data provider's API key and monthly budget (Foursquare is already the recorded provider).
- Choosing the map provider (it depends on the data provider's terms).
