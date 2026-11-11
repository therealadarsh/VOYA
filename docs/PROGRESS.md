# Progress

The living status of the build. Update it at the end of every session (see
`AGENTS.md` → "Session logging"). History lives in `docs/SESSION_LOG.md`.

**Last updated:** 2026-11-11 · branch **`main`** (`6a464b3`) · integration + build/mvp merged

## Done
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
- **Sign-in returns a token directly** (dev mode); there are no emailed
  magic links yet.
- **Not deployed;** SQLite only.

## Next (suggested order)
1. **M2 Planner** on `build/mvp`: OpenAPI-aligned `/v1/plans`, cited data behind planner.
2. **UX redesign (M6):** React + Vite + TypeScript, with map and motion.
3. **Real data connectors (licensed, terms-checked):**
   - places API, OSM, NPS/RIDB, transit fares;
   - one canonical place table that links each place's IDs across sources.
3. **Insider notes:** the owner writes sentences about places they know; the
   AI turns them into structured annotations; the owner approves; they show
   as "insider picks".
4. **Deploy to AWS** with a cost alarm, plus real email sign-in.

## Blocked / needs the owner
- Choosing the places-data provider and its monthly budget.
- Choosing the map provider (it depends on the data provider's terms).
