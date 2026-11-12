# Session log

Append-only. One entry per working session, newest at the bottom. Write an
entry whenever a session ends, is about to hit its context or usage limit, or
hands off to another tool. Keep entries technical: business strategy belongs
in the private folder (`.voya-private/`), never here.

Template:

```markdown
## YYYY-MM-DD · <tool> · branch <name> · <first-sha>..<last-sha>
**Goal:** one line
**Done:** bullets (files/modules, tests added, test count)
**Decisions:** bullets (also added to DECISIONS.md)
**Not done / known issues:** bullets
**Next:** numbered, smallest useful step first
**Questions for the owner:** bullets (or "none")
```

---

## 2026-11-11 · Claude Code (cloud) · branch claude/new-session-4f5ud7 · edf8829..9a36b7b

**Goal:** go from an empty repo to a working, testable MVP.

**Done:**
- Read the reference project (Daytrip, MIT, pinned `74610afb`). Notes are in
  `docs/daytrip-notes.md`; it is fetched by `scripts/fetch_reference.sh`.
- Cost model with 40 tests: ranged, sourced, timestamped cost lines.
- Replaced repo history with one clean commit (strategy docs removed from the
  public repo).
- `AGENTS.md`: rules for AI tools; the plan lives outside the public repo;
  `.gitignore` blocks prompt/question/answer/transcript files.
- MVP: planner, budget fit (correlated price simulation), discovery, spend
  tracking with recovery, AI helper with the ten agent-engineering concepts,
  accounts, opt-in memory, tracing, and a mobile-first web app. 84 tests;
  browser walkthrough with no page errors.

**Decisions:** see `DECISIONS.md` (demo catalog, hard versus wiggle maths,
lodging range, restaurant repeats, worth-it threshold, OpenRouter, SQLite,
no-build frontend, dev sign-in, opt-in memory).

**Not done / known issues:**
- Demo data only.
- No email sign-in.
- No deployment.
- The frontend is plain JS (intended to be replaced).
- The helper's "cheaper" option can save less than the amount asked for when
  little can be cut (it says so).

**Next:**
1. UX redesign.
2. Real data connectors with a canonical place table.
3. Insider-notes pipeline.
4. AWS deploy.

**Questions for the owner:** places-data provider and budget; map provider;
design direction (see the private Cursor prompt).

---

## 2026-11-11 · Cursor Cloud Agent · branch build/mvp · 6edd483..HEAD

**Goal:** adopt owner PLAN.md (autonomous M1–M6); complete M1 foundations.

**Done:**
- `docs/BUILD_PLAN.md` (Foursquare, OpenRouter models, Indiana Dunes).
- CostLine extensions; `pricing/` + `data/` loaders; cited JSON under `data/`.
- `make verify` (scoped lint, mypy on money code, 88 tests, policy scripts).
- `docs/DATA_SOURCES.md`, `VERIFY.md` M1, tag `mvp-m1`.

**Decisions:** Foursquare places; INDU second park; see `DECISIONS.md`.

**Not done / known issues:** Planner still uses demo catalog; M2+ milestones open.

**Next:** M2 planner refactor and cited fares in plan lines.

**Questions for the owner:** none (plan is source of truth).

---

## 2026-11-11 · Cursor Cloud Agent · PR #1 merged · build/mvp → claude/new-session-4f5ud7

**Goal:** land M1–data-strategy work via approved PR.

**Done:** PR #1 merged (735db4c); cited rules, magic link, price-check CLI, providers fakes, 94 tests.

**Next:** Postgres/Alembic, React section-8 shell + Playwright, Foursquare fake→LIVE behind cap.

---

## 2026-11-11 · integration → main

**Goal:** owner requested merge integration branch to `main`.

**Done:** `main` fast-forwarded/reset to `6a464b3` (same as `claude/new-session-4f5ud7`); unrelated old `main` history replaced; `make verify` green on push.

**Note:** Clone `main` and `git pull` — default branch now holds the full MVP stack.

---

## 2026-11-12 · Claude Code (cloud) · review of main 56647b6 (no code changes)

**Goal:** independently check the Cursor M1–M6 work merged to `main`.

**Done:**
- `make verify` green from a clean `uv sync --frozen`: ruff, mypy, 94 tests,
  and policy, citation, secret, traceability and example checks.
- No tracked private files, no secrets in the full git history, no banned
  word in product code. `docs/BUILD_PLAN.md` is technical only.
- Test diff since `6edd483`: no assertions weakened or skipped (removed
  lines were reformatted; the tax test now reads the cited rate).
- Mutation checks, each caught: budget check loosened (guard property test),
  hard limit = median (hard ≥ wiggle test), sales tax dropped (tax/tip test).
- Browser walkthrough on a phone-sized screen: plan → helper → sign in and
  save → log spend → discover, with no page or server errors. Cited NYC tax
  and fare appear in plan lines.
- Corrected `docs/PROGRESS.md` (it was stale: test count, sign-in, Next
  numbering).

**Not done / known issues:**
- Could not verify the cited values: the session's network blocks the
  official sites. Several quotes say "planning value; confirm" while marked
  `synthetic: false`.
- The tax label rounds 8.875% to 8.88%.
- Demo places mixed with cited rules.

**Next:** see `docs/PROGRESS.md` → Next (start with verifying the cited
values).

**Questions for the owner:** confirm the cited values; UX direction;
provider budget tier.
