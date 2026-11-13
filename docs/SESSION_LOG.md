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
