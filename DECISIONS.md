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
