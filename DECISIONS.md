# Decisions

One line per major choice and why. Newest at the bottom.

- **Daytrip is a gitignored reference fetched at pinned SHA `74610afb`** (`scripts/fetch_reference.sh`): we read it, we don't vendor it, and everyone reads the same version.
- **Python 3.12 + uv + Pydantic v2 + pytest**, as specified; uv for a reproducible lockfile and fast installs.
- **`src/` layout** so tests import the installed package, not stray files in the repo root.
- **Money is `Decimal` rounded to cents**: plan totals sum many lines and floats drift.
- **`confidence` = stated probability that the real price lies in `[low, high]`**: the only definition the Phase 5 coverage metric can test directly.
- **"Data-backed" = `price_range` or `user_actual` only**: a price bucket's level is observed, but its money value is our mapping.
- **`user_actual` lines must be exact** (`low == amount == high`, confidence 1.0): an actual with a range is a modelling error.
- **Plan totals report `high_total` as a sum of line highs**: simple and conservative; it is a bound, not a joint interval, and is labeled so.
- **Mixed-currency plans are rejected by `summarize`** until Phase 2 adds FX: silently adding yen to dollars is worse than an error.
- **Bucket/type point values reused from Daytrip's `estimateCost`** (MIT, credited in `THIRD_PARTY_NOTICES.md`); VOYA's bands and confidences are initial priors to be calibrated in Phases 5–6.
- **MVP runs on a synthetic demo catalog** (`synthetic: true`, made-up names, "Demo prices" banner): real cited data needs API keys and a data budget; inventing real-looking prices for real places would mislead.
- **Hard limit = max(sum of highs, 97th percentile); wiggle room = 90th percentile**: low-confidence lines have tails past their stated high, so a pure sum of highs could be looser than wiggle room.
- **Lodging estimates are a rule-based planning range at 80% confidence**: the traveller chooses a place within the range; treating it as a 50% guess made every multi-day plan infeasible.
- **Restaurants may repeat on different days, sights never repeat**: small catalogs otherwise force expensive meals late in a trip.
- **Worth-it upgrades must add at least $5 and still fit**: smaller deltas are swaps, not upgrades; ranked by interest match, rating gain and popularity.
- **Plans are stored as requests and re-planned deterministically**, with a version history for undo; proposals are single-use and bound to their content and plan version.
- **The AI only picks a tool; code computes every number**: works without any model (built-in router), and model output is schema-validated.
- **Runtime AI via OpenRouter behind one `LLMClient` interface**, default model `openrouter/auto`, configurable per role; caps $0.15/task, $1.50/user/day, $30/month.
- **SQLite for the MVP**, same table shapes as the planned Postgres schema.
- **Plain HTML/CSS/JS frontend with no build step** for speed; a React/Vite rewrite can come once the UX settles.
- **Sign-in returns a token directly (dev mode)**; production sends an email magic link.
- **Memory is opt-in per tap** and limited to interests, pace, tip %, firmness and adults; never income or locations.
- **M1 data layer:** cited JSON under `data/` for 3 cities + Yosemite + Indiana Dunes; demo catalog unchanged until M2.
- **Foursquare Places API** as the commercial places provider (≤$50 one-time enrichment); fakes in tests.
- **Second launch park:** Indiana Dunes (INDU), reachable from Chicago; entrance fee $0 per NPS page cited in `data/`.
- **OpenRouter models (target):** helper `openrouter/google/gemini-2.5-flash`, narration `openrouter/openai/gpt-4o-mini` (override via env).
- **`owner_check` cost source:** approved rows from `voya price-check` (pending → approve); coverage on `/v1/ops`.
- **Data strategy (2026-11-11):** paid APIs for display only; licensed data per licence; owned prices via insider notes + price-check — no scraping.
- **Private preview (2026-11-13):** `VOYA_ENV=production` refuses to start until an invite code, https public URL, absolute `VOYA_DATA_DIR`, and SMTP settings are present. Dev sign-in stays the default outside production. SQLite lives in that directory; `python -m voya.backup` copies it. Privacy and Terms pages are drafts until the owner supplies legal wording.
