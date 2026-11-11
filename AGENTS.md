# AGENTS.md: start here (for any AI coding tool)

Read automatically by many AI coding tools. `CLAUDE.md`, `GEMINI.md` and
`.cursor/rules/voya.mdc` point here.

## Build spec

The owner gives you the build spec as `VOYA_MVP_PROMPT.md`, either pasted
into the chat or placed at `docs/VOYA_MVP_PROMPT.md`. Follow it. If you don't
have it, ask the owner for it before building anything.

## Non-negotiables

- **Never invent prices, fares, taxes, hours or statistics.** Real data needs
  a `source` and `observed_at`; test data is marked `synthetic: true`.
- **Never write the word "guarantee".** Every estimate is labeled "est.".
- **Coordinates at no more than 3 decimal places** anywhere they are stored,
  logged, prompted or sent.
- **The AI proposes; deterministic code computes money, checks the budget and
  applies changes.**
- **Tests use fakes:** no network, no tokens.
- **Secrets only in environment variables** (`.env` is gitignored; see
  `.env.example`). Never commit, log or put keys into prompts or traces.
- **Keep business strategy out of code, comments, commit messages and public
  docs.**
- **Don't weaken tests to make them pass.**
- **Don't edit `reference/`** (a read-only clone fetched by
  `scripts/fetch_reference.sh`).

## Commands

```sh
uv sync
uv run pytest
```
