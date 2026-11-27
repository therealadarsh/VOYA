# How to review and understand VOYA

**Verified:** 2026-11-27 01:24 ET · base commit `ccd1791` · branch `dev`.
Everything marked *observed* was run or read on that date. *Convention* means
a written rule that nothing enforces. *Not built* means described, not present.
*Unverified* means I did not check it. Re-run the commands in section 4 before
trusting any number here.

## 1. The one-paragraph mental model

**ELI5:** VOYA is a careful calculator with a chat window bolted on. You say
"3 days in Chicago for $600". The calculator picks places, adds up every cost
as a *range* with a source and a date, and checks the total against your
budget. The AI never does the math. It only chooses which calculator button to
press, and the calculator re-checks the answer before anything changes.

**Deeper:** `planner.py` is the deterministic core (no AI). Every price is a
`CostLine` (`cost/model.py`) holding a low, a point and a high value, a source,
an observed date, and a confidence. `uncertainty.py` simulates plan totals so
"wiggle room" budgets can be checked. `agent.py` picks a typed tool, the planner
re-prices, a guard (`planner.evaluate`) refuses changes that don't fit, and a
single-use proposal is stored until the user taps apply. Persistence is
`store.py` over `db.py` (SQLite, or Postgres when `DATABASE_URL` says so).

## 2. Data flow (read top to bottom)

```
browser  src/voya/web/*.js  ──HTTP──▶  api.py
   middleware: safety.py headers + same-host POST check, preview.py invite gate,
               metrics.py counters, obs.py trace, log.py access log (no query string)

POST /v1/plans ─▶ planner.build(PlanRequest)
      catalog.load_catalog()   demo.json (synthetic)  +  pricing/cited_rules.overlay_rules()
                               └─ cited JSON under data/ (pricing/, data/loaders.py)
      choose() ─▶ price() ─▶ CostLine / summarize()  (cost/model.py)
      evaluate()  budget fit via uncertainty.simulate / quantile / p_under
      over budget? repair()      optional: worth_it() upgrades
      store.create_plan / add_version   (requests + versions; undo = store.undo)

POST /v1/plans/{id}/helper ─▶ agent.respond
      route_intent  or  llm.Harness (OpenRouter, or FakeLLM in tests)
      ─▶ tool_nearby / tool_cheaper / tool_swap / tool_worth_it / tool_explain
      ─▶ planner re-prices ─▶ guard ─▶ store.add_proposal ─▶ user applies once

POST /v1/plans/{id}/spend ─▶ tracking.budget_status / recovery_options
```

Function names are used on purpose instead of line numbers: line numbers rot
(see section 6).

## 3. Reading order (about 90 minutes)

| Step | Read | Why |
|---|---|---|
| 1 | `AGENTS.md`, `docs/PROGRESS.md`, last 2 entries of `docs/SESSION_LOG.md` | State and rules |
| 2 | `DECISIONS.md` | Why the code looks the way it does |
| 3 | `cost/model.py` (`CostLine`, `CostSource`, `summarize`) | The money vocabulary |
| 4 | `planner.py`: `PlanRequest`, `choose`, `price`, `evaluate`, `repair`, `worth_it`, `build` | The core |
| 5 | `uncertainty.py` | How "fits in 9 of 10 outcomes" is computed |
| 6 | `catalog/__init__.py`, `pricing/`, `data/loaders.py`, one file under `data/` | Where numbers come from |
| 7 | `api.py` routes, then `store.py` | How the core is exposed and saved |
| 8 | `agent.py`, `llm.py` | The only AI surface; read `docs/CONCEPT_MAP.md` alongside |
| 9 | `settings.py`, `preview.py`, `safety.py`, `accounts/` | Production gates and privacy |
| 10 | `tests/test_planner.py`, `tests/test_agent_and_api.py` | What is actually guarded |

### Where to look when...

| Question | Look at |
|---|---|
| Why is this total what it is? | `planner.price`, `cost/model.summarize` |
| Why does a plan count as "fits"? | `planner.evaluate`, `uncertainty.simulate` |
| Where does a tax or fare come from? | `pricing/rules.py`, `pricing/cited_rules.overlay_rules`, `data/` |
| Why did the helper change my plan? | `agent.respond`, `agent.run_loop`, `store.take_proposal` |
| What does production refuse to start without? | `settings.production_problems` |
| Why is the demo banner showing? | `catalog.show_demo_banner` |
| What does a request log or trace contain? | `log.py`, `obs.redact`, `obs.span` |

## 4. Review commands and what they printed

I ran the tools straight from the existing `.venv` instead of `make verify`,
because `make verify` starts with `uv sync --frozen`, which can modify the
environment. Run `make verify` yourself for the official gate.

| Check | Command | Observed 2026-11-27 |
|---|---|---|
| Tests | `.venv/bin/python -m pytest -p no:warnings -o addopts= -q` | `123 passed, 2 skipped` in about 1.9 s |
| Skips | add `-rs` | browser flow (`VOYA_BROWSER=1`) and Postgres (`VOYA_TEST_DATABASE_URL`), both opt-in |
| Lint, gated paths | `.venv/bin/ruff check <the Makefile `lint` paths>` | `All checks passed!` |
| Types, gated paths | `.venv/bin/mypy <the Makefile `typecheck` paths>` | `no issues found in 24 source files` |
| Policy | `scripts/check_policy.py` | ok |
| Citations | `scripts/check_data_citations.py` | 10 cited file(s) |
| Traceability | `scripts/check_traceability.py` | ok (3 snippets, see section 6) |
| Secrets | `bash scripts/check_secrets.sh` | ok |
| Examples | `scripts/validate_examples.py` | ok |

## 5. What to check in a pull request

Work through the diff in this order. Stop and ask when one item is unclear.

1. **Money.** Amounts are `Decimal` rounded to cents. A new price carries a
   source and an `observed_at`. Anything made up is `synthetic: true`. No float
   arithmetic on dollars.
2. **The AI boundary.** The model may only pick a tool and arguments. Code
   computes every number, and every change goes through the guard and a
   single-use proposal. New tools have strict typed arguments.
3. **Honesty rules.** No banned promise word (the exact pattern is in
   `scripts/check_policy.py`; it scans `src`, `web`, `data`, `examples` and
   `README.md` only, not `docs/`, so check docs by eye). Coordinates at 3 decimals or
   fewer (`providers/foursquare.round_coord` rounds; the scan skips test files
   and any match with the word "synthetic" within 20 characters). Estimates labeled "est." (*unverified*:
   my search for that string was inconclusive).
4. **Tests.** New behaviour has a test. No test was loosened to pass. Run the
   mutation habit from `docs/CONCEPT_MAP.md`: break the rule on purpose
   (for example `ok=metric <= req.budget` to `<= req.budget * 2` in
   `planner.py`) and confirm a test fails, then restore it.
5. **Network and secrets.** Tests use fakes. Only `tests/test_agent_and_api.py`
   has the autouse fixture that blocks `socket.connect` (there is no
   `conftest.py`), so a new test file elsewhere is not protected. Secrets live
   only in environment variables.
6. **Privacy and production.** Production start-up checks, the invite gate,
   security headers and the same-host POST check keep working. Logs keep paths
   without query strings (magic-link tokens), and traces are redacted.
7. **Private files.** Nothing from `.voya-private/` is copied into tracked
   files, commit messages or comments.
8. **Docs.** If behaviour, state or the next steps changed, the docs in
   section 7 changed in the same PR.

### Merge into `dev` (label gate)

After items 1–8 look good, the **owner** (not an agent) may merge by adding the
**`auto-merge`** label on the PR. A GitHub Actions workflow waits for **required**
CI checks (`verify`, `postgres`, `docker` once configured in a ruleset), then
merges and deletes the head branch. Fork PRs never auto-merge. Full setup:
[`GITHUB_AUTOMATION.md`](GITHUB_AUTOMATION.md).

## 6. Known review gaps (observed)

- **The gate does not cover the core.** `make lint` and `make typecheck` use a
  fixed list of paths. `planner.py`, `agent.py`, `api.py`, `store.py`, `llm.py`,
  `tracking.py`, `uncertainty.py`, `discover.py`, `obs.py`, `catalog/`,
  `cli.py` and `curate/` are not in it. Run on all of `src`: ruff reports 23
  errors and mypy reports 136 errors in 9 files. A new type error in
  `planner.py` would not fail `make verify`. Review those files by eye.
- **Traceability is thin.** `check_traceability.py` only looks for three
  snippets (`S-01`, `S-23`, `MVP-PLAN`) in test text.
- **CI is remote-only.** `.github/workflows/ci.yml` runs on PRs; local
  `core.hooksPath` is still unset. `make verify` runs when a person or tool runs it.
  Label-based auto-merge is documented in `GITHUB_AUTOMATION.md` (not a substitute
  for reading the diff).
- **Not exercised here.** The browser flow, the Postgres round trip and the
  Docker image build. `docs/PROGRESS.md` says the image was never built in the
  authoring environment.
- **Stale documents** (details in section 7): `VERIFY.md`, the line numbers in
  `docs/CONCEPT_MAP.md`, a commit id in `docs/PROGRESS.md`, and the old $20
  alarm amount.

## 7. Where documents get updated

**Short answer: nothing in this repo updates a document automatically.**
Scripts check some *content* rules, and a written protocol tells people and AI
tools to update the rest by hand. Nothing fails when a document goes stale.

| Document | Updated by | When | Enforced? |
|---|---|---|---|
| `docs/SESSION_LOG.md` | The AI tool or person, by hand | End of every session (`AGENTS.md` → Session logging) | Convention. Git history has `log: session summary` commits, so it is followed. |
| `docs/PROGRESS.md` | Same | Same | Convention. Stale evidence below. |
| `README.md` "Status" line | Same | Same | Convention |
| `DECISIONS.md` | By hand | When a major choice is made | Convention |
| `docs/CONCEPT_MAP.md` | By hand | When agent code moves | None. Its line numbers no longer match the code (for example `llm.py:134` is not `Harness`). |
| `VERIFY.md` | By hand | At milestones | None. It still says 91 tests and "Postgres not wired"; the suite has 123 tests and Postgres is built. |
| `docs/DEPLOY.md`, `docs/BUILD_PLAN.md` | By hand | When plans change | None. They still say $20; the decided alarm is $40. |
| `docs/DATA_SOURCES.md` | By hand | When a source is added | Citation check covers `data/` files, not this table |
| `.voya-private/PLAN.md` | The AI tool, per `AGENTS.md` | When the owner gives feedback | Convention. Gitignored. |
| `data/owner_checks/entries.jsonl` | The `voya price-check` CLI | When prices are checked | Program-written, gitignored |
| `var/` (traces, database, backups) | The running app | At runtime | Program-written, gitignored. Not documentation. |

**How the AI tools find out they should update docs:** `AGENTS.md` holds the
rules, and `CLAUDE.md`, `GEMINI.md` and `.cursor/rules/voya.mdc` each point to
it. These files tell the tool what to do. They do not make it happen.

**What the scripts do check** (all run by `make verify`, by hand today):
`check_policy.py` (banned word, coordinate precision, secret patterns),
`check_data_citations.py` (every non-synthetic `data/` file has a source, an
`observed_at` and a quote), `check_traceability.py`, `check_secrets.sh`,
`validate_examples.py`.

**Stale evidence found:** `docs/PROGRESS.md` says it was last updated on
branch `cursor/phase-1b-nyc-mvp-3eef` at commit `fc6838f`. That commit id does
not exist in this clone. `VERIFY.md` and `docs/CONCEPT_MAP.md` are stale as
shown in the table. A real automatic check would have caught these.

### Planned, not built: the handoff system

The pasted handoff brief would add the missing automation. None of it exists
yet.

| Piece | What it would do | Status |
|---|---|---|
| `docs/TIMELOG.md` | Append-only log, one entry per change, ET timestamp | Not built |
| `scripts/handoff.py log` (`make log`) | Appends an entry and fills the time, files and base commit | Not built |
| `scripts/handoff.py status` (`make status`) | Prints branch, recent log entries, next steps, staleness warning | Not built |
| `scripts/handoff.py check` (`make handoff-check`) | Fails if code changed without a log entry, or a module has no map row | Not built |
| `scripts/install_hooks.sh` | Runs the check before each commit | Not built |
| Handoff check in CI | Runs the check on every pull request | Not built |
| `docs/HANDOFF.md`, `docs/CODEMAP.md` | Living state and a one-row-per-file map | Not built |

Even when built, `log` only appends facts it can read from git, and `check`
only fails a build. Neither writes the explanations in HANDOFF or CODEMAP. A
person or AI tool still writes those, and the check only tells them when they
forgot.

## 8. Keeping this guide honest

Re-run section 4 and update the date, the base commit and the observed
numbers. If you change a name mentioned in sections 2 or 3, change it here in
the same pull request.
