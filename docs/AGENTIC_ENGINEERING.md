# Agentic engineering in VOYA (living register)

A committed, mentor-style catalog of every **AI and agentic** technique used to
**run** VOYA (runtime, in `src/voya/`) and to **build** VOYA (owner tools,
harnesses, checks). For each entry: what it is, how this repo implements it,
why it matters, and **when to update the row**.

**Companion docs**

| Doc | Use when you need… |
|---|---|
| [`CONCEPT_MAP.md`](CONCEPT_MAP.md) | Exact symbols, line anchors, and hands-on experiments |
| [`DATA_SOURCES.md`](DATA_SOURCES.md) | OpenRouter and other providers' terms and caching |
| [`docs/README.md`](README.md) | One-line map of all project documentation |

**Keep it current.** Any PR that adds, removes, or materially changes runtime AI,
build-time agent workflow, or verification scripts should update the relevant
row(s) here and add one dated line to the [changelog](#changelog). Session
logging in `AGENTS.md` points here.

**Status:** **Built** · **Partial** · **Planned** · **Not used**

---

## Build-time vs runtime AI

| Layer | Who uses it | Where it lives | Must never… |
|---|---|---|---|
| **Runtime (product)** | Travellers via "Ask VOYA" | `src/voya/agent.py`, `llm.py`, `obs.py`, `api.py` helper routes | Invent prices, approve budget changes, or skip the guard |
| **Build-time (owner tools)** | Humans and coding agents building the repo | `AGENTS.md`, `.cursor/rules/`, `.voya-private/`, Cursor / Claude Code / Gemini | Copy private prompts into tracked files; commit secrets |

**The product rule (runtime):** the model may pick **one** of five tools; deterministic code computes every dollar, checks budget fit, and applies changes only after the traveller approves a single-use proposal.

**The build rule (tooling):** agents read `docs/PROGRESS.md` and `docs/SESSION_LOG.md`, follow `AGENTS.md` non-negotiables, and run `make verify` before claiming done. Prices, API keys, and legal copy come from the owner, not from the model.

```
                    BUILD-TIME                         RUNTIME
  Owner ──▶ AI IDE (Cursor, Claude…) ──▶ code/tests     Traveller ──▶ /helper ──▶ agent loop
                │                                        │                    │
                ▼                                        ▼                    ▼
         AGENTS.md + SESSION_LOG              OpenRouter (optional)    router fallback
                │                                        │                    │
                ▼                                        └──────────┬─────────┘
         make verify (policy, citations…)                               ▼
                                                              planner + guard + proposal
```

---

## Part A — Runtime (product)

### A. LLM stack

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **LLM client abstraction** | Vendor-neutral "complete JSON" API | `llm.py`: `LLMClient` protocol, `OpenRouterClient`, `FakeLLM`, `client_from_env()`; models `VOYA_LLM_MODEL_HELPER`, `VOYA_LLM_MODEL_NARRATOR` | Swap providers without touching features; tests need no network | You add a provider, change env var names, or alter `complete_json` contract | Built |
| **OpenRouter adapter** | One API key, many models | `OpenRouterClient` in `llm.py`; default helper model `openrouter/auto` (see `DECISIONS.md`) | Commercial models without per-vendor SDKs | OpenRouter API shape, default model, or billing assumptions change | Built |
| **Harness (caps, retries, breaker)** | Safety wrapper on every model call | `llm.py` `Harness.call`: per-task, per-user-day, and monthly USD caps (`VOYA_TASK_BUDGET_USD`, `VOYA_USER_DAILY_BUDGET_USD`, `VOYA_MONTHLY_BUDGET_USD`); retry only retryable errors; 60s breaker after 5 failures; spend recorded in `store.py` | Runaway loops or bad models cannot blow the budget or take the app down | Cap amounts, retry policy, breaker thresholds, or ledger fields change | Built |
| **No-key / test mode** | Same UX without paid inference | `client_from_env()` returns `None` → `api.py` passes `harness=None` → `run_loop` uses `route_intent` only; tests use `FakeLLM` | Demo and CI stay free and deterministic | Helper entrypoints or env gating change | Built |

### B. Agent loop and tools

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Loop engineering** | Bounded decide → act → stop cycle | `agent.py` `run_loop`: `MAX_STEPS=4`, `MAX_TOOL_CALLS=6`, one model call per task, `stop_reason` on every exit, duplicate-call stop, one guided retry on `fix_input` | Predictable cost/latency; debuggable stops | Step/tool budgets, stop reasons, or retry rules change | Built |
| **Tool registry** | Typed, narrow actions | `agent.py` `TOOLS`: `find_nearby`, `find_cheaper`, `swap_stop`, `worth_it`, `explain_cost`; Pydantic args; `ToolError` envelope | Model cannot invent new side effects | Tools added/removed or schemas change | Built |
| **Deterministic router** | Keyword → tool without LLM | `agent.py` `route_intent` | Works offline when caps hit or key missing | Intent patterns or fallback order change | Built |
| **Orchestration** | Who decides what | `agent.py` `respond`: model/router → tool → planner re-price → guard → proposal | Money promise stays in code | Flow between helper, planner, and API changes | Built |

### C. Context, prompts, and safety

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **System prompt & schema** | Fixed instructions + JSON shape | `agent.py` `SYSTEM`, `SCHEMA`; not copied into this file (tracked prompts stay minimal) | Consistent tool-only behaviour | `SYSTEM`/`SCHEMA` or validation rules change | Built |
| **Context digest** | Small state snapshot for the model | `agent.py` `build_context`: budget, total, local time, interests, next stops; manifest logged via `obs.py` | Fewer tokens; less hallucinated state | Fields in digest or manifest change | Built |
| **Untrusted data tagging** | Anti prompt-injection | User text and place names wrapped in `<untrusted_data>`; schema limits tool choice | Untrusted copy cannot rewrite budget logic | Tagging or instruction text changes | Built |
| **Structured output** | JSON tool choice only | `complete_json` + `SCHEMA` + `model_validate`; invalid → router + `BAD_ARGS` | No free-form money claims from the model | Output shape or validation changes | Built |
| **Output verification** | Post-check on assistant text | `agent.py` `verify_answer`: rejects unknown dollar amounts, >3-decimal coordinates, banned words | Last line of defence on prose | Rules or banned patterns change (also `scripts/check_policy.py`) | Built |

### D. Memory, guardrails, human approval

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Working memory** | Per helper task | `agent.py` `Ctx` for one `/helper` request | Short-lived plan context | `Ctx` fields change | Built |
| **Opt-in long-term memory** | Cross-trip prefs | `store.py` `set_pref`, `/v1/me/memory`; keys limited (no income/locations) | Faster replanning without sensitive storage | Allowed keys or API change | Built |
| **Budget guard** | Deterministic fit check | `agent.py` `_candidate`, `planner.py` `evaluate`, `api.py` `new_version` (`DOES_NOT_FIT`) | AI cannot approve an over-budget plan | Guard or evaluate semantics change | Built |
| **Human in the loop** | Tap to apply once | `store.py` `add_proposal` / `take_proposal`; version-bound; `PROPOSAL_USED` | Traveller always approves mutations | Proposal lifecycle changes | Built |

### E. Observability and cost

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Tracing** | Redacted request spans | `obs.py` `span`, `event`, `redact`; `X-Trace-Id`; CLI `python -m voya.obs show` | Debug helper without leaking secrets | Events, redaction rules, or CLI change | Built |
| **Spend ledger & ops** | AI spend visibility | Harness + store counters; price overrides `VOYA_LLM_PRICE_IN_PER_M` / `VOYA_LLM_PRICE_OUT_PER_M`; `/v1/ops` | Owner can see burn rate | Ledger schema or ops endpoints change | Built |

### F. Evaluation

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Planner property tests** | Outcome-based evals | `tests/test_planner.py` (budget fit, upgrades, simulation coverage) | Proves money promises, not exact wording | Planner economics or test properties change | Built |
| **Agent/helper tests** | Harness, loop, injection | `tests/test_agent_and_api.py` with `FakeLLM` | Regression on agent engineering | Helper API or tool behaviour changes | Built |
| **Golden-trip evals** | End-to-end scenarios | `make eval` stub (`Makefile`); artifacts planned | Future calibration of full trips | `make eval` implemented or golden files added | Planned |
| **Plan narration** | Cheap model for prose | Env `VOYA_LLM_MODEL_NARRATOR`; must pass `verify_answer` | Friendly copy without touching numbers | Narrator wired to UI | Planned |

### G. Runtime — deliberately not used

| Technique | Why not (yet) | Update when… |
|---|---|---|
| LLM-computed prices | Core rule; `Decimal` in code | Never for money (document if policy changes) |
| RAG / vector search | Five-city scope; idea bank is curated JSON (`ideas.py`, `data/ideas/`) | You add semantic retrieval over places or trips |
| Fine-tuning | Prompt + tools sufficient | Training pipeline adopted |
| Multi-agent runtime | Single bounded agent is testable | Architecture splits into multiple runtime agents |

---

## Part B — Build-time (owner tools)

### H. Instruction harnesses and repos rules

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **`AGENTS.md`** | Single rulebook for all AI IDEs | Read order, non-negotiables, session logging, commands | Cursor, Claude Code, Gemini stay aligned | Workflow or logging rules change | Built |
| **Shim entrypoints** | Pointers, not duplicates | `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/voya.mdc` → `AGENTS.md` | Rules cannot drift per tool | New IDE supported | Built |
| **Private owner folder** | Plan, briefs, prompts (local only) | Gitignored `.voya-private/` (`PLAN.md`, step briefs, `SESSION_NOTES.md`, etc.) | Public repo stays safe; strategy stays private | **Never** copy contents into tracked files—only describe categories here | Built |
| **Tracked vs gitignored prompts** | Where text may live | **Tracked:** minimal `SYSTEM`/`SCHEMA` in `agent.py`; policy in `scripts/`; docs like this file. **Gitignored:** kickoff answers, step briefs, chat exports (see `.gitignore` / `AGENTS.md`) | Contributors know what may be committed | `.gitignore` patterns or agent prompt location moves | Built |

### I. Coding agents and subagents

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Cursor Agent** | Primary builder (local/cloud) | Used for preview, NYC slice, CI/docs work; subagents via Cursor `Task` for explore/review when enabled | Parallel search and specialised review without polluting repo | New Cursor workflow adopted for this repo | Built |
| **Claude Code** | Architect / planner sessions | MVP, planning, `SESSION_LOG` entries | Long-horizon design and verification | Role changes | Built |
| **Gemini** | Optional reader | `GEMINI.md` → `AGENTS.md` | Second toolchain with same rules | Used for shipping code | Partial |
| **Grok (second opinion)** | Diff review | Mentioned in prior catalog; not required for build | Planned peer review on edge cases | First regular use | Planned |
| **Subagents (tooling only)** | Specialised short tasks | Cursor: `explore`, `code-reviewer`, `ci-investigator`, etc.—**not** shipped in VOYA runtime | Faster codebase search and review | New subagent types become standard for VOYA | Built |

### J. Builder loop and hand-off memory

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **Step loop** | One step → one branch → verify | Plan → tests → implement → `make verify` → session log; never weaken tests; never edit `reference/` | Same discipline as runtime loop limits | Branch/PR policy changes | Built |
| **SESSION_LOG + PROGRESS** | Cross-session memory | `docs/SESSION_LOG.md`, `docs/PROGRESS.md` | Next agent knows done/next/blocked | Template or required fields change | Built |
| **CONCEPT_MAP experiments** | Learn by doing | Nine numbered experiments in `CONCEPT_MAP.md` | New contributors prove harness/loop/guard | New runtime concept needs a map row | Built |

### K. Automated policy and traceability (`make verify`)

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **`check_policy.py`** | Banned words, coarse coords, secret patterns | Scans `src`, `web`, `data`, `examples`, root `README.md` | Catches "guarantee" and accidental key paste | `BANNED`, `SCAN_DIRS`, or coord rules change | Built |
| **`check_data_citations.py`** | Sourced numbers in `data/` | `make citations` | Real fares/taxes must cite source + `observed_at` | Citation schema changes | Built |
| **`check_traceability.py`** | Requirements ↔ tests map | `make traceability` | Agent features stay tied to tests | Traceability matrix changes | Built |
| **`check_secrets.sh`** | Secret scan | `make secrets` | Extra guard beyond policy regexes | Patterns or paths change | Built |
| **`validate_examples.py`** | Example JSON plans | `make examples` | Public examples stay valid | Example format changes | Built |
| **CI (GitHub Actions)** | Remote `make verify` | `.github/workflows/ci.yml`: `verify` (`make verify`), `postgres` (`tests/test_p1_nyc.py`), `docker` build; PRs to `dev`/`uat`/`prod` | Catches regressions before merge | Workflow jobs, triggers, or runner image change | Built |

### L. MCP and external assistant tools

| Entry | What it is | How VOYA implements it | How it helps | Update this row when… | Status |
|---|---|---|---|---|---|
| **AWS MCP (read-only)** | Docs + read-only AWS checks via MCP | Owner-approved during deploy/cost planning; not imported into `src/voya/` | Safer infra research from the IDE | MCP server list or allowed operations change | Built |
| **Browser MCP** | UI verification | Optional Cursor browser tools for flows; production tests use pytest + opt-in `VOYA_BROWSER=1` | Human-like checks without committing automation secrets | Standard browser test path changes | Partial |
| **OpenRouter (data)** | Provider terms | `docs/DATA_SOURCES.md`: no prompt secrets in logs; traces redacted | Legal/ops compliance | Terms or retention policy changes | Built |

---

## How techniques support project goals

| Goal | Primary entries |
|---|---|
| Honest money | Budget guard, human approval, orchestration, `check_policy`, citations |
| Bounded AI cost | Harness, loop limits, digest, spend ledger |
| Works without AI | Router, `FakeLLM`, optional `client_from_env` |
| Safe with untrusted input | Tagging, structured output, `verify_answer` |
| Debuggable agent | Stop reasons, tracing, CONCEPT_MAP |
| Consistent multi-tool build | AGENTS.md, SESSION_LOG, this register |

---

## Changelog

Newest at the bottom.

- 2026-11-27: Created as canonical agentic register (`docs/AGENTIC_ENGINEERING.md`). Consolidated narrative from `docs/AI_TECHNOLOGIES.md`, added per-row "update when" guidance, build/runtime split, subagents, and `make verify` policy scripts. Added `docs/README.md` documentation index.
- 2026-11-27: Marked **CI (GitHub Actions)** Built after `.github/workflows/ci.yml` merged to `dev`.
- 2026-11-27: CI row updated: Postgres service job, PR triggers on `uat`/`prod`; Makefile `RUN` for local `snakeenv`.