# Concept map: agent engineering in VOYA

Where each concept lives, which features use it, the test that proves it, and
a hands-on experiment. Paths are relative to `src/voya/`.

| Concept | Features that use it | Code | Proving tests (`tests/test_agent_and_api.py` unless noted) |
|---|---|---|---|
| **Harness** (timeouts, retries, caps, sandbox) | Ask VOYA | `llm.py:134` `Harness`, `llm.py:155` `call`, `llm.py:58` OpenRouter adapter, `llm.py:106` `FakeLLM` | `test_cost_cap_falls_back_to_router`, `test_monthly_kill_switch`, `test_retries_only_retryable_and_breaker_opens` |
| **Loop** (limits, repeats, stop reasons) | Ask VOYA | `agent.py:280` `run_loop` | `test_loop_without_model_uses_router`, `test_model_choice_is_validated_and_bad_args_fall_back` |
| **Context** (digest, untrusted data, manifest) | Ask VOYA | `agent.py:245` `build_context` | `test_prompt_injection_in_user_text_is_data` |
| **Tools** (narrow, typed, error envelope) | Ask VOYA | `agent.py:201` `TOOLS`, `agent.py:122` `tool_nearby`, `agent.py:91` `ToolError` | `test_router_picks_the_right_tool`, `test_unknown_tool_from_model_is_ignored` |
| **Memory** (short-term + opt-in long-term) | Remember / Forget, form prefill | `agent.py` `Ctx` (working memory per task); `store.py:157` `set_pref`; `api.py` `/v1/me/memory` | `test_full_flow` (remember, forget, rejects keys like income) |
| **Orchestration** (who decides what) | Ask VOYA, planning | The router or model picks a tool → deterministic tools → the planner re-prices → the guard decides → the user approves: `agent.py:372` `respond` | `test_every_option_fits_and_raising_needs_a_tap` |
| **Guardrails** (budget guard, permissions, output checks) | Every change, every answer | `agent.py:363` `_candidate`, `planner.py:468` `evaluate`, `agent.py:338` `verify_answer`, `api.py` `new_version` (refuses changes that don't fit) | `tests/test_planner.py::test_guard_property_random_proposals_never_produce_unfit_ready_plans`, `test_upgrade_that_does_not_fit_is_refused`, `test_verify_answer_catches_bad_text` |
| **Evals** (outcomes, not outputs) | The whole planner | `tests/test_planner.py`: budget fit, hidden costs, ranking, anchors, multi-day | `test_hard_limit_is_never_looser_than_wiggle_room`, `test_upgrades_always_fit_and_cost_more`, `test_lognormal_matches_stated_coverage` |
| **Human in the loop** | Worth it, Ask VOYA, recovery, memory | `store.py:190` `add_proposal` / `store.py:199` `take_proposal` (single-use, bound to content, stale-version check) | `test_full_flow` (proposal applies once) |
| **Observability** | Every request | `obs.py:65` `span`, `obs.py:29` `redact`, `api.py:81` `_trace_and_limit` | `test_traces_are_redacted` |

## Try it yourself

1. **Harness:** set `VOYA_TASK_BUDGET_USD=0.0001` with an OpenRouter key and
   ask VOYA something. The model call is blocked before spending, and the
   built-in router answers.
2. **Loop:** in a Python shell, give `run_loop` a `FakeLLM` that names a tool
   that doesn't exist. The router takes over, and `errors` shows why.
3. **Context:** call `agent.build_context(ctx)` and read what the model would
   see: a short digest, with place names and your message wrapped in
   `<untrusted_data>`.
4. **Tools:** send `{"tool": "find_cheaper", "args": {"evil": 1}}` from a
   `FakeLLM`. Strict schemas reject the extra field (`BAD_ARGS`).
5. **Memory:** save a trip, tap "Remember", start a new plan (interests are
   pre-filled), then Forget.
6. **Guardrails:** `POST /v1/plans/{id}/upgrades/d0-s4:chi-steak` on a $60
   Chicago plan returns `DOES_NOT_FIT`.
7. **Evals (mutation test):** change `ok=metric <= req.budget` to
   `<= req.budget * 2` in `planner.py` and run `make test`. The guard
   property test fails.
8. **Human in the loop:** apply the same helper proposal twice. The second
   attempt returns `PROPOSAL_USED`.
9. **Observability:** copy `X-Trace-Id` from any response, then run
   `uv run python -m voya.obs show <trace_id>`.
