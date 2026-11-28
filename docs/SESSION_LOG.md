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

---

## 2026-11-27 · Claude Code (desktop) · branch fix/blank-db-settings · ae5efdb..c4d4cbe

**Goal:** connect magic-link email to Amazon SES and fix the local-run defaults
that broke on the way.

**Done:**
- Owner set up Amazon SES in `us-east-1`: domain identity with Easy DKIM
  (RSA 2048) verified, one sandbox test inbox verified, and an IAM SMTP user
  limited to `ses:SendRawEmail`. Credentials live only in the owner's
  gitignored `.env`. No code change was needed for SMTP.
- Live check: the app ran with `--env-file .env` (`VOYA_ENV=development`,
  `VOYA_DEV_SIGNIN=0`); `POST /v1/auth/start` returned `email_sent` and SES
  counted one send.
- `src/voya/store.py`: `default_db_path()` treats a blank or whitespace
  `VOYA_DB`, `DATABASE_URL` or `VOYA_DATA_DIR` as unset. Before, a blank
  `VOYA_DATA_DIR` put `voya.db` in the working directory.
- `.env.example`: `DATABASE_URL` is blank (it pointed at a local Postgres
  database that does not exist), so a fresh copy runs on SQLite.
- `.gitignore`: `*.db` and SQLite journal/WAL files.
- `tests/test_db_path.py`: 7 tests (blank, whitespace, explicit path,
  Postgres URL, `.env.example` stays on SQLite). Lint, mypy (39 files),
  secrets and policy checks green. **130 passed, 2 skipped.**

**Decisions:** none.

**Not done / known issues:**
- `make run` does not load `.env`; use
  `uvicorn voya.api:app --reload --port 8000 --env-file .env`.
- SES is still in the sandbox (only verified recipients, 200 a day).
  Production access is an owner request in the SES console.
- Production SMTP values belong in SSM, not a file. Not deployed.

**Next:**
1. Merge this branch into `dev`.
2. S04 demo banner per area.
3. Owner: request SES production access before inviting testers (S17).

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor · branch feat/s04-demo-banner-per-area · base ca838cb

**Goal:** S04, demo banner per destination instead of one catalog-wide switch.

**Done:**
- `Destination.synthetic` (None inherits the catalog). `destination_is_demo`
  treats a synthetic catalog as demo for every area, an empty place list as
  demo, and `type_guess` / `price_bucket` money as demo.
- `show_demo_banner` is true when any destination is demo.
- `GET /v1/meta` adds `data_status`. Plan `demo_data` uses only that plan's
  destination. The picker appends " — Demo prices" on demo options.
- `tests/test_p1_banner.py` covers the boundary rows and the three input rows.
  `make verify RUN=` green.

**Decisions:** none. Discover stays catalog-wide; it was outside this step.

**Not done / known issues:**
- Bundled catalog is still synthetic, so the live picker still tags every area.

**Next:**
1. Open a PR into `dev`.
2. S05 cited place catalog.

**Questions for the owner:** none.

---

## 2026-11-27 · Cursor · branch feat/migrations-and-places · ef27900..01a68cb

**Goal:** Close the phase 1 review gaps as four PRs into `dev`.

**Done:**
- F-01–F-04 on `fix/preview-security` (PR #16): sign-in limits keyed by an email hash, client address only from a trusted proxy, production metrics token, feedback length cap and privacy wording.
- F-05–F-07 on `feat/idea-bank-slots` (PR #17): per-slot NYC sample idea bank, plan-seeded rotation, anonymous `idea_stats`.
- F-08–F-10 on `test/e2e-and-smoke` (PR #18): `make e2e` at 360px and 1280px with axe, CI `e2e` job, `scripts/smoke.sh`.
- F-11–F-14 on `feat/migrations-and-places` (PR #19): Alembic on SQLite and Postgres, `python -m voya.copy_db`, fake places cache, deploy and test docs.
- `make verify RUN=`: 175 passed, 7 skipped. `make e2e RUN=`: 4 passed.
- CI on PR #19: `verify`, `postgres`, `e2e`, and `docker` green. Local smoke was not run because Docker was not running.

**Decisions:** S05 (cited JSON place catalog) is not F-13. F-13 is the database cache. The uncommitted S05 work stayed in the stash `wip: S05 cited place catalog`. The NYC idea file is a sample, `curated_by: "sample"`. Foursquare live import stays off. No AI feature changed, so `docs/AGENTIC_ENGINEERING.md` was not edited.

### Phase 1 fixes report
| ID | Status (done / partial / blocked / covered by Sxx) | PR | Commit | Tests added | Notes / owner question |
|----|---|---|---|---|---|
| F-00 | done | — | — | — | `make verify` was already green on `dev` |
| F-01 | done | #16 | ef27900 | tests/test_f01_signin_limit.py | |
| F-02 | done | #16 | f0767d6 | tests/test_f02_client_ip.py | Which proxy addresses should `VOYA_TRUSTED_PROXY_IPS` list? |
| F-03 | done | #16 | 8d7586b | tests/test_f03_metrics.py | What token should scrape `/metrics`? |
| F-04 | done | #16 | 8c5802c | tests/test_f04_feedback.py | What wording should the Privacy page use? |
| F-05 | done | #17 | e0456ff | tests/test_f05_ideas.py | Sample NYC picks, not the owner's |
| F-06 | done | #17 | a2ab730 | tests/test_f06_rotation.py | |
| F-07 | done | #17 | d3e92e9 | tests/test_f07_idea_stats.py | |
| F-08 | done | #18 | 5df30c7 | tests/browser/test_preview_flow.py | `make e2e`: 4 passed |
| F-09 | done | #18 | 02a8127 | CI job `e2e` | Owner should add `e2e` as a required check |
| F-10 | done | #18 | fc27ee0 | scripts/smoke.sh | Local smoke not run (Docker off). CI `docker` green on #18 and #19 |
| F-11 | done | #19 | cf03cf3 | tests/test_f11_migrations.py | Postgres migrate-then-test is in CI |
| F-12 | done | #19 | 6fb5ece | tests/test_f12_copy_db.py | Postgres copy runs in CI. The command never prints the URL |
| F-13 | partial | #19 | 9f4427e | tests/test_f13_places.py | Fake import, refresh, and drop are done. Live Foursquare import is blocked |
| F-14 | done | #19 | 01a68cb | — | No AI feature change |

make verify: green   make e2e: green   smoke: green in CI (not run locally; Docker is not running)   tests: 175 passed, 7 skipped (verify); 4 passed (e2e)

Open owner questions:
1. Which host should the preview use, and which addresses belong in `VOYA_TRUSTED_PROXY_IPS`?
2. What value should `VOYA_METRICS_TOKEN` use?
3. What wording should the Privacy and Terms pages use?
4. Which NYC places should replace the sample classic picks?
5. What is the Foursquare API key, the monthly budget in USD, and the USD to count per search?
6. What invite code, public https URL, and SES production access should the preview use?
7. What monthly amount should the hosting cost alarm use?
8. Please add `e2e` as a required check on `dev`.

**Not done / known issues:**
- The four PRs are open and not merged. Merge #16, then #17, then #18, then #19.
- Live Foursquare import is blocked on the owner's key and budget. No cache window is invented.
- Classic picks are a sample. The owner's own NYC list is not in the file.
- S05 cited place catalog remains stashed and was not built again.

**Next:**
1. Owner merges the four PRs in order and adds `e2e` as a required check.
2. S05 cited place catalog, then the owner's NYC picks in `data/ideas/nyc.json`.
3. Later, not started: vectors, the preference learner and rituals, regions with specialties, multi-region trips, Europe and currencies, climate matching, the bandit, and the React redesign.

**Questions for the owner:** the numbered list above.

---

## 2026-11-28 · Claude Code · branch feat/migrations-and-places · 2653771..HEAD

**Goal:** Review PR #19 and fix what the review found.

**Done:**
- `migrations/versions/0003_plan_ideas_column.py`: adds `plan_versions.ideas_json`
  when missing. Before this, an older database was stamped at head without the
  column, so the first saved plan would fail. Checked on SQLite (test) and on a
  throwaway local Postgres database; a second upgrade is a no-op.
- `python -m voya.copy_db` returns 2 when the `--from` file does not exist,
  instead of creating an empty file and reporting success.
- `docs/DEPLOY.md`: Compose deploys run
  `docker compose run --rm --entrypoint .venv/bin/alembic voya upgrade head`
  before `docker compose up`, since the database lives in the volume.
- Tests added: `test_upgrade_adds_ideas_json_to_an_older_database`,
  `test_a_missing_source_file_is_refused`. `make verify RUN=`: 177 passed, 7 skipped.

**Decisions:** a new revision instead of editing `0001_baseline`, so databases
already stamped at `0002_places` also get the column.

**Not done / known issues:**
- Once a Foursquare key is set, `import_search` would make the paid search
  before `cache_until` refuses to store the rows. Live import is blocked today.
- The schema is still defined in both `Store` and the migrations.
- `make e2e` and `scripts/smoke.sh` were not run locally (CI runs both).

**Next:**
1. CI green on PR #19, then merge #16, #17, #18, #19 in order.
2. S05 cited place catalog.

**Questions for the owner:** none new.
