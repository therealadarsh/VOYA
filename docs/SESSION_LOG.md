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

## 2026-11-12 · Claude Code (cloud) · branch claude/happy-brown-f43m58 · 56647b6..HEAD

**Goal:** discuss a curated "first week" idea bank with rotation, and later
similarity search over saved ideas.

**Done:** design discussion only; no code changes. Test suite green (94).
Added the idea bank to PROGRESS "Next".

**Decisions:** none yet. The owner wants the current MVP fully working first;
vector search is next phase.

**Next:** owner explains the trip cases; then design the idea-bank data shape.

**Questions for the owner:** cases for the first-week sets; how learning
from usage should feed back.

---

## 2026-11-13 · Cursor Cloud Agent · branch cursor/phase-1a-private-preview-3eef · 7301ed8

**Goal:** private preview (production settings, invite gate, email sign-in, durable SQLite, safety, draft legal pages, preview UI, health, container, browser flow, deploy guide).

**Done:**
- `src/voya/settings.py`: production start refuses to continue until invite code, https URL, absolute data directory, and SMTP values are set.
- Invite cookie gate, SMTP magic-link mailer (fake SMTP in tests), dev sign-in unchanged.
- SQLite path from `VOYA_DATA_DIR`; `python -m voya.backup`.
- Security headers, same-host POST check, draft `/privacy` and `/terms`.
- Preview label, feedback rows, `/healthz` and `/readyz`, JSON access logs without query strings.
- `Dockerfile`, `docker-compose.yml`, `docs/DEPLOY.md` (single Docker host and AWS).
- `tests/test_p1_preview.py`. Browser flow in `tests/browser/test_preview_flow.py` passed with `VOYA_BROWSER=1` (plan, feedback, dev sign-in, save). Default `make verify`: 112 passed, 1 skipped.

**Decisions:** see `DECISIONS.md` (private preview settings, draft legal pages).

**Not done / known issues:**
- No Docker daemon here, so the image was not built.
- SMTP account, invite code, public URL, hosting account, alarm amount, and legal wording are unanswered. Draft pages state that they are not legal text.
- Demo catalog and dev token sign-in remain the local defaults.

**Next:**
1. Phase 1b on a branch stacked on this one: Postgres, places pipeline, NYC idea bank, sourced-cost banner rule, monitoring, accessibility.

**Questions for the owner:**
- Which hosting account should the private preview be deployed to?
- What SMTP host, port, username, password, and From address should magic-link email use?
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use?

---

## 2026-11-13 · Cursor Cloud Agent · branch cursor/phase-1b-nyc-mvp-3eef · fc6838f

**Goal:** public NYC slice on top of the private preview: Postgres, places pipeline, idea bank, sourced-cost banner rule, metrics, accessibility.

**Done:**
- `src/voya/db.py`: SQLite or Postgres. `tests/test_p1_nyc.py` round trip passed against local Postgres 16 when `VOYA_TEST_DATABASE_URL` is set. Default `make verify` skips that test.
- Foursquare search client. Live calls require a key, a monthly budget, a per-call USD amount, and `VOYA_PLACES_LIVE=1`. Coordinates rounded to 3 decimal places. Price levels are not converted to dollars.
- `data/ideas/nyc.json`: two 7-day sets. Rotation by seed. "Show me another" advances the set. The only attached cost is the cited MTA fare.
- `show_demo_banner`: stays on for the synthetic catalog and for any type-guess or price-bucket cost.
- `/metrics` Prometheus text. Static accessibility checks for labels, language, contrast, and focus. Browser flow passed again, including idea rotation.
- Default suite: 123 passed, 2 skipped.

**Decisions:** see `DECISIONS.md` (Postgres URL, Foursquare budget gate, demo banner rule, idea bank).

**Not done / known issues:**
- No Foursquare key or budget, so no live place fetch and no real NYC place prices. The demo banner stays.
- Hosting, SMTP, invite code, public URL, alarm amount, and legal wording are still unanswered.
- Vectors, rituals, the learner, extra regions, Europe, and climate were not started.

**Next:**
1. Owner supplies the blocked values. Then cited NYC place prices can replace the demo catalog.

**Questions for the owner:**
- Which hosting account should this be deployed to?
- What SMTP host, port, username, password, and From address should magic-link email use?
- What invite code should the private preview require?
- What public https URL should magic links use?
- What monthly hosting budget should the AWS cost alarm use? BUILD_PLAN recorded $20; confirm or replace it before any alarm is created.
- What wording should the Privacy page and the Terms page use?
- What is the Foursquare API key, the monthly budget in USD, and the USD to count per search?

---

## 2026-11-27 · Claude Code (desktop) · branch ci/pr-checks · ccd1791

**Goal:** check the current state and lay out the remaining build as small,
testable steps for the next sessions.

**Done:**
- No code changes. Installed the project into the local `snakeenv` conda
  environment and ran the suite: 123 passed, 2 skipped (browser flow and
  Postgres, both opt-in).
- Checked API behaviour for the step specs: `/healthz` ok; `/v1/meta` shows 5
  destinations, all demo; `examples/plans/chicago_weekend.json` returns
  `status: infeasible` at its own $350 budget; unknown destination and
  `days: 31` return 422.
- Wrote the step-by-step build brief in the gitignored private folder.

**Decisions:** none in tracked files. Proposed changes wait for the owner.

**Not done / known issues:**
- No CI workflow yet (`.github/workflows/` is missing); `ci/pr-checks` has
  no commits beyond `main`.
- `make lint` / `make typecheck` cover only part of `src/voya`
  (`planner.py`, `api.py`, `agent.py`, `store.py` and others are outside).
- Every `make` target calls `uv run`; there is no switch for running in an
  existing environment.
- The Chicago example does not fit its own budget.

**Next:**
1. S01: `RUN ?= uv run` in the Makefile so targets work with or without uv.
2. S02: GitHub Actions running `make verify` on PRs into `dev`, plus a
   Postgres service job for `tests/test_p1_nyc.py`.
3. S03: widen ruff and mypy to all of `src/voya`, no behaviour change.

**Questions for the owner:**
- Should `docs/SESSION_LOG.md` and `docs/PROGRESS.md` stay tracked (AGENTS.md)
  or move to the gitignored folder?

---

## 2026-11-27 · Cursor Agent · branch dev (docs, uncommitted) · ccd1791

**Goal:** add committed living documentation for agentic/LLM build and runtime stack.

**Done:**
- Added `docs/AGENTIC_ENGINEERING.md`: runtime + build-time register with per-row
  "update when" guidance, build vs runtime diagram, policy/MCP/subagent rows,
  changelog.
- Added `docs/README.md`: index of root + `docs/` markdown; marks `.voya-private/`
  and `reference/`; links agentic doc prominently.
- Replaced `docs/AI_TECHNOLOGIES.md` body with redirect to the new canonical doc.
- Updated `README.md`, `docs/PROGRESS.md`, `AGENTS.md` (read order + session logging
  target). No `src/` changes; `make verify` not run (docs-only).

**Decisions:** none in `DECISIONS.md` (documentation only).

**Not done / known issues:**
- `VERIFY.md` still partially stale vs `PROGRESS.md` (left as historical log;
  noted in docs index).
- CI and `make eval` golden trips still planned.

**Next:**
1. Owner reviews doc structure; commit when ready.
2. Continue CI step (Makefile `RUN`, GitHub Actions on `dev`).

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor Agent · branch dev · ef0d247

**Goal:** merge open PRs #6–#8 into `dev` in creation order.

**Done:**
- Merged PR #6 (agentic register + doc index), #7 (`docs/REVIEW_GUIDE.md`), #8
  (`.github/workflows/ci.yml`); all merge commits, branches deleted.
- Checked out `dev`, pulled `origin/dev` at `ef0d247`.
- Updated `docs/AGENTIC_ENGINEERING.md` CI row to Built; `docs/PROGRESS.md` last
  updated + CI bullet.

**Decisions:** none.

**Not done / known issues:** none from merges (all `mergeStateStatus: CLEAN`).

**Next:**
1. Continue build steps from private brief (Makefile `RUN`, widen lint/mypy).

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor Agent (subagent) · branch feat/cursor-prompt-next · ef0d247..19a13f4

**Goal:** execute P0 safety-net steps S01–S03 from the private build brief (Makefile,
CI, lint/mypy coverage).

**Done:**
- `Makefile`: `RUN ?= uv run`, shared `LINT_PATHS` / `TYPE_PATHS`, conditional
  `sync` on `verify`, `make help`.
- `.github/workflows/ci.yml`: `postgres` job (PG 16, `VOYA_TEST_DATABASE_URL`),
  PR triggers for `uat`/`prod`, 15m timeouts.
- `pyproject.toml`: ruff on full tree; pydantic mypy plugin; `[[tool.mypy.overrides]]`
  for `api`/`agent`/`planner` (S03c).
- Ruff fixes across `src/voya` and tests; mypy clean on 39 modules; small typing
  fixes in `store`, `tracking`, `discover`, `obs`, `llm`, `cli`.
- Docs: `docs/PROGRESS.md`, `docs/AGENTIC_ENGINEERING.md` CI row + changelog.
- `make verify` and `make verify RUN=` (snakeenv): green; **123 passed, 2 skipped**.

**Decisions:** none in `DECISIONS.md` (tooling only).

**Not done / known issues:**
- S03c: strict mypy on `api.py`, `agent.py`, `planner.py` still deferred.
- GitHub ruleset not updated here to require `postgres` check (owner action).
- P1–P4 steps (real data, evals, deploy, ops) unchanged; owner-blocked items
  still block catalog and deploy.

**Next:**
1. Merge P0 PR; owner enables required status checks `verify` + `postgres`.
2. S03c then S04 demo banner per area.

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor Agent (subagent) · branch feat/github-auto-merge · bd8146b+

**Goal:** safe label-gated auto-merge into `dev` (option B); owner docs for
rulesets and branch cleanup; no org settings changed here.

**Done:**
- `.github/workflows/auto-merge.yml`: `labeled` / `synchronize` on PRs to `dev`;
  same-repo only; requires label `auto-merge`; `gh pr checks --required --watch`;
  `gh pr merge --merge --delete-branch`.
- `docs/GITHUB_AUTOMATION.md`: delete-branch setting, ruleset steps, owner
  checklist, security (no agent merge token).
- `docs/REVIEW_GUIDE.md`, `docs/README.md`, `docs/AGENTIC_ENGINEERING.md` updated.
- PR #10 verified **MERGED**; branch created from current `origin/dev` (`bd8146b`).
- `make verify RUN=` (snakeenv): green.

**Decisions:** none.

**Not done / known issues:**
- GitHub ruleset and “auto-merge” label still owner actions in UI.
- Workflow not exercised on a real PR until this feature PR lands.

**Next:**
1. Merge auto-merge PR; owner completes checklist in `GITHUB_AUTOMATION.md`.
2. P0 S03c / ruleset verification on a test PR.

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor Agent (subagent) · branch dev · bd8146b..21a4c10

**Goal:** merge PR #11 (auto-merge workflow); report SMTP readiness and finish roadmap.

**Done:**
- PR #11 merged (`gh pr merge --merge --delete-branch`); CI green (verify,
  postgres, docker). `origin/dev` at `21a4c10`.
- No open PRs after merge. `make verify RUN=` (snakeenv): green on `dev`.
- SMTP/code review: implementation complete; credentials and provider are owner-only.

**Decisions:** none.

**Not done / known issues:**
- P0 S03c (strict mypy on `api`, `agent`, `planner`) not started this session.
- GitHub ruleset + `auto-merge` label creation still owner UI actions.
- Owner-blocked: SMTP account, invite code, public URL, hosting, legal, Foursquare.

**Next:**
1. Owner: `docs/GITHUB_AUTOMATION.md` checklist (ruleset, delete head branches, label).
2. Branch `feat/cursor-prompt-s03c` for S03c; then S04 demo banner per area.

**Questions for the owner:** none (SMTP/hosting questions unchanged in PROGRESS).

---

## 2026-11-27 · Cursor Agent (subagent) · branch feat/cursor-prompt-s03c · 21a4c10..2be2c41

**Goal:** strict mypy on `voya.api`, `voya.agent`, and `voya.planner`.

**Done:**
- Removed the `[[tool.mypy.overrides]]` ignore for those three modules in
  `pyproject.toml`.
- Added annotations (`dict[str, Any]` at JSON boundaries, `Category` on cost
  helpers) and a few `None` checks where a place or action was optional.
- `make verify RUN=` and `make verify`: green. **123 passed, 2 skipped.**
  mypy: 39 source files, no issues.

**Decisions:** none.

**Not done / known issues:**
- GitHub ruleset and the `auto-merge` label are still owner UI actions.
- Owner-blocked: SMTP account, invite code, public URL, hosting, legal, Foursquare.

**Next:**
1. Merge this PR into `dev`.
2. S04 demo banner per area.

**Questions for the owner:** none.
