# Progress

The living status of the build. Update it at the end of every session (see
`AGENTS.md` → "Session logging"). History lives in `docs/SESSION_LOG.md`.

**Last updated:** 2026-11-12 · branch **`main`** (`56647b6`) · independent review of M1–M6 work

## Done
- **Cost model** (`src/voya/cost/`): ranged, sourced, timestamped cost lines;
  units and evidence; plan totals with hidden costs and "you could keep".
- **Cited rules in `data/`:** sales tax (NYC, SF, Chicago), transit fares
  (MTA, Muni/BART, CTA), park fees (Yosemite, Indiana Dunes), tipping
  default.
  - Used by the planner when `VOYA_CITED_RULES=1` (the default).
  - **Some values still need checking against their sources** (see Blocked).
- **Planner** (`planner.py`):
  - value plan first; ranking by interests → value → distance, with one
    hidden gem per day;
  - hidden costs (tax, tips, transit, extras); gifts allowance;
  - multi-day lodging; fixed-activity days; optional getting-there estimate;
  - repair when over budget; worth-it upgrades.
- **Budget fit** (`uncertainty.py`): hard limit or wiggle room, via a
  correlated price simulation.
- **Discovery, live spend tracking** with recovery options.
- **AI helper** (`agent.py`, `llm.py`): tools, a bounded loop, a context
  digest, a budget guard, single-use proposals; OpenRouter or a built-in
  router.
- **Accounts:**
  - magic-link sign-in (fake mailer in tests; dev sign-in still on by
    default via `VOYA_DEV_SIGNIN`);
  - 18+; export and delete; opt-in memory; entitlements stub.
- **Data workflow:** `voya price-check` CLI with `owner_check` evidence and a
  coverage metric on `/v1/ops`; provider interface + fakes.
- **Web:** the plain-JS app at `/` (fully working); a React + Vite scaffold
  in `web/` (scaffold only).
- **Quality:**
  - `make verify` is green: ruff, mypy on money code, 94 tests, and policy,
    citation, secret, traceability and example checks.
  - Mutation-checked on 2026-11-12: a looser budget check, a weaker hard
    limit and dropped sales tax are each caught by a test.
- **Docs:** `docs/CONCEPT_MAP.md`, `docs/MVP_TEST_GUIDE.md`,
  `docs/DATA_SOURCES.md`, `docs/DEPLOY.md`, `docs/BUILD_PLAN.md`,
  `VERIFY.md`, `DECISIONS.md`.

## Known limits
- **Places are still the synthetic demo catalog** ("Demo prices" banner).
  Plans mix cited rules (tax, fares, park fees) with demo places, demo
  lodging and the occupancy tax.
- **The sales-tax label rounds** (8.875% shows as "8.88%"); the maths uses
  the exact rate.
- **SQLite only** (Postgres/Alembic not wired). Not deployed.
- **The React app is a scaffold;** no Playwright/axe automation yet.
- **`make eval` is a stub.**
- **The agent package split** (`agent/loop.py`, …) is deferred; everything
  lives in `agent.py`.

## Next (suggested order)
1. **Verify the cited values** against their official pages (see Blocked)
   and change the "planning value; confirm" quotes to exact quotes from the
   pages.
2. **UX:** pick a direction, then build the React app to parity with the
   plain-JS app, with Playwright + axe.
3. **First real places provider** (fake → live behind a spend cap) +
   canonical places table.
4. **Insider notes** (`voya note`, `/curate`, the insider-pick badge).
5. **Postgres/Alembic, AWS deploy** with a cost alarm, real email sign-in.

## Blocked / needs the owner
- **Confirm the cited values from the official pages.** The quotes for these
  say "planning value; confirm" or "verify", and the review session couldn't
  reach the sites:
  - NYC subway fare ($2.90);
  - Muni fare ($2.50);
  - BART minimum ($2.35);
  - CTA rail/bus ($2.50 / $2.25);
  - Yosemite vehicle fee ($35, 7-day);
  - Indiana Dunes entrance fee ($0);
  - SF sales tax (8.625%);
  - Chicago (10.25%; restaurant meals in parts of the city may be taxed
    higher).
- Places-data provider confirmation (Foursquare is recorded as the choice)
  and its budget tier.
- Map provider and UX direction.
