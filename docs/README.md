# Documentation index

One-line map of useful **tracked** docs. Owner-only material lives in
**gitignored** `.voya-private/` (plan, prompts, strategy)—see `AGENTS.md`; it is
**not** listed here and must never be copied into committed files.

**Start here for agentic / LLM work:** [`AGENTIC_ENGINEERING.md`](AGENTIC_ENGINEERING.md)
(living register). **`CONCEPT_MAP.md`** has code anchors and experiments.

---

## Repository root (markdown)

| File | Purpose |
|---|---|
| [`README.md`](../README.md) | Product overview, run commands, feature table, doc links |
| [`AGENTS.md`](../AGENTS.md) | Rules for AI coding tools: read order, logging, non-negotiables |
| [`CLAUDE.md`](../CLAUDE.md) | Pointer → `AGENTS.md` |
| [`GEMINI.md`](../GEMINI.md) | Pointer → `AGENTS.md` |
| [`DECISIONS.md`](../DECISIONS.md) | One line per major design choice (newest at bottom) |
| [`VERIFY.md`](../VERIFY.md) | Historical verification milestones (superseded in part by `PROGRESS.md`) |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | Attributed borrowed code (e.g. Daytrip cost estimates) |

**Owner-only (gitignored, not committed):** `.voya-private/` — plan, build briefs,
session strategy notes, prompt templates. **Cursor rule:** `.cursor/rules/voya.mdc`
(points at `AGENTS.md`; may exist only on a developer machine).

**Reference clone (read-only, not edited):** `reference/` — Daytrip at pinned SHA via
`scripts/fetch_reference.sh`.

---

## `docs/`

| File | Purpose |
|---|---|
| **[`AGENTIC_ENGINEERING.md`](AGENTIC_ENGINEERING.md)** | **Living register** of runtime + build-time AI/agentic tech |
| [`AI_TECHNOLOGIES.md`](AI_TECHNOLOGIES.md) | Short redirect → `AGENTIC_ENGINEERING.md` (legacy name) |
| [`CONCEPT_MAP.md`](CONCEPT_MAP.md) | Agent concepts → modules, tests, "try it yourself" |
| [`PROGRESS.md`](PROGRESS.md) | Done / limits / next / blocked (update every session) |
| [`SESSION_LOG.md`](SESSION_LOG.md) | Append-only technical session history |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | Provider terms, caching, attribution (incl. OpenRouter) |
| [`DEPLOY.md`](DEPLOY.md) | Private preview: Docker, env, AWS notes |
| [`VOYA_BOT.md`](VOYA_BOT.md) | What the VOYA-bot crawler reads and keeps, and how a site opts out |
| [`MVP_TEST_GUIDE.md`](MVP_TEST_GUIDE.md) | Manual MVP checks; intentional gaps |
| [`GITHUB_AUTOMATION.md`](GITHUB_AUTOMATION.md) | Owner: rulesets, delete-branch setting, `auto-merge` label workflow |
| [`REVIEW_GUIDE.md`](REVIEW_GUIDE.md) | How to review PRs; points at label-gated merge |
| [`BUILD_PLAN.md`](BUILD_PLAN.md) | Milestone-oriented build outline |
| [`daytrip-notes.md`](daytrip-notes.md) | Notes from read-only Daytrip reference (not `reference/` itself) |

---

## Suggested read order (new contributor)

1. `README.md` → `docs/PROGRESS.md` → last `SESSION_LOG` entries  
2. `docs/AGENTIC_ENGINEERING.md` + `docs/CONCEPT_MAP.md` if touching Ask VOYA or agent tests  
3. `DECISIONS.md` before changing economics or data policy  
4. `AGENTS.md` before any AI-assisted coding session  