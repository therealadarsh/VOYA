# VOYA

A budget-first trip planner. Every cost estimate carries a range, a source and
a stated confidence, and is always labeled as an estimate.

## Status

| Part | Status |
|---|---|
| Reference notes (`docs/daytrip-notes.md`) | done |
| Cost model (`src/voya/cost/`) | done, 40 tests |
| MVP | in progress |

## Setup

```sh
uv sync                        # Python 3.12 venv + deps
uv run pytest                  # tests
./scripts/fetch_reference.sh   # optional: read-only reference project at a pinned commit
```

Copy `.env.example` to `.env` for local configuration. `.env` is gitignored;
never commit keys.

## Cost model (`src/voya/cost/`)

A `CostLine` has:
- `amount` (point estimate), plus `low` and `high`;
- `currency`;
- `source`: `user_actual`, `price_range`, `price_bucket` or `type_guess`;
- `observed_at` (timezone-aware);
- `confidence`: the stated probability that the real price falls in
  `[low, high]`.

Money is `Decimal`, rounded to cents. `summarize(lines)` reports point, low and
high totals, the share of spend backed by real price data, and breakdowns by
source and category.

## For AI coding tools

See [`AGENTS.md`](AGENTS.md).
