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

## 2026-11-13 · Claude Code (cloud) · branch claude/happy-brown-f43m58 · 86762ee (planning)

**Goal:** check deploy readiness; define Phase 1.

**Done:** make verify green (94 tests); local smoke test (health, meta, NYC plan).
Readiness gaps: synthetic places, fake mailer + dev sign-in default, SQLite file
in the container, no privacy/terms page, no monitoring/backups, sketch deploy guide.
Phase 1 split into tracked IDs P1-00…P1-17 (PROGRESS "Next").

**Decisions:** none; hosting and places provider still with the owner.

**Next:** P1-01 onward on branch `phase1-preview`.

**Questions for the owner:** hosting choice; places provider + monthly budget;
number of preview testers.

---

## 2026-11-13 · Claude Code (cloud) · review of Phase 1 (PR #3, PR #4) · ccd1791

**Goal:** review Phase 1 against P1-00…P1-17.

**Checked:** `make verify` green (123 passed, 2 opt-in skipped); browser flow
passes with Playwright; production start refuses incomplete settings; invite
gate returns 401 without the cookie. Docker image not built (no daemon here either).

### Phase 1 report (review)
| ID | Status | Notes |
|----|---|---|
| P1-01 | done | settings + production refusal verified |
| P1-02 | done | single code, cookie gate |
| P1-03 | partial | no per-email resend limit (3 sends in a row accepted) |
| P1-04 | done | `python -m voya.backup`; restore documented |
| P1-05 | partial | rate limiter keys on client IP; behind a proxy all users share one bucket; no trusted-proxy setting |
| P1-06 | done (draft) | wording needs the owner |
| P1-07 | done | feedback stores an optional contact field; privacy page should say so |
| P1-08 | done | |
| P1-09 | partial | Dockerfile non-root + healthcheck; image never built; no smoke script |
| P1-10 | partial | opt-in, Playwright not a dev dep, no `make e2e`; spend, helper, privacy page, desktop width and console errors not covered |
| P1-11 | done | blocked on host choice |
| P1-12 | partial | Postgres works; no Alembic migrations or SQLite to Postgres copy |
| P1-13 | partial | Foursquare client behind fakes and a budget gate; no canonical places table |
| P1-14 | not to spec | two whole-week sets swapped as a block; no per-slot options, no plan link, no counters; picks written by the agent and marked non-synthetic |
| P1-15 | blocked | needs places key; banner rule done |
| P1-16 | partial | `/metrics` open without a token and outside the invite gate |
| P1-17 | partial | static checks, not axe in a browser |
| report | missing | the build tool did not write the per-ID table |

**Next:** fix P1-03, P1-05, P1-16 (security), then P1-14 to spec, then P1-10/P1-12/P1-13.

**Questions for the owner:** same blocked values as PROGRESS (host, SMTP, invite code,
public URL, alarm amount, legal wording, places key and budget).
