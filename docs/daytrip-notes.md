# Daytrip notes

Reference: `ArabotHXL/trip-planner` at commit `74610afb` (2026-07-25), MIT per
`package.json` (no LICENSE file, no named copyright holder). Read-only, fetched
by `scripts/fetch_reference.sh`. Paths below are relative to the repo root;
`lib/` alone means `artifacts/api-server/src/lib/`.

The question behind every note: **for each dollar in the output, where did it
come from, how sure is it, and when was it observed?**

## Per-file summaries

### README.md
City + budget in, hour-by-hour single-day plan out. TypeScript monorepo: Express
API, React PWA, Postgres via Drizzle, OpenAPI spec as the contract (Orval
generates client hooks and Zod validators). External APIs: Google Places/
Geocoding, Open-Meteo, Frankfurter FX. Says "estimates, never guarantees"
(`README.md:8`), but ROADMAP still sells a "budget guarantee" (`ROADMAP.md:42`).

### ROADMAP.md / IMPROVEMENT_PLAN.md
Product strategy, metric gates, shipped log. Confirms the fixed split
"food 35%, transport 15%, activities 50%" (`ROADMAP.md:24`) and "planner runs in
USD". No item anywhere about per-city prices or what travelers actually paid.
IMPROVEMENT_PLAN is engineering status (CI gates, single-instance lock,
in-process FX cache).

### PLACES_TOS_NOTES.md
Google Places ToS: only lat/lng (30 days) and **place IDs (indefinitely)** may
be cached. Names, ratings, hours and prices may not. Daytrip's 7-day full-POI
cache and name-bearing golden fixtures are "outside the letter" (`:16`, `:19`).
**Lesson for VOYA Phase 4:** cache place IDs + our own derived numbers; treat
provider content as request-scoped unless the terms say otherwise.

### lib/db/src/schema/
- `externalCache.ts`: one table for every external call. `(namespace,
  cache_key)` unique, `payload jsonb`, `expires_at` indexed for GC. Good
  pattern, copy it.
- `trips.ts`: saved plans, whole `TripPlan` as jsonb, `last_accessed_at` for a
  12-month retention sweep.
- `tripEvents.ts`: analytics log (plan/save/swap/thumbs) with metadata jsonb.
  **Stores no spend data** and no per-line cost provenance.

### lib/pois.ts — `estimateCost` (`:523`)
Turns one Google place into one number. Order of preference:
1. `priceRange` midpoint, **USD only** (`priceRangeUsd`, `:511`). Any other
   currency returns `null` at `:514`, so a ¥1,000–2,000 range is thrown away.
   Open-ended ranges use made-up multipliers (×1.25 / ×0.85, `:518-519`).
2. `priceLevel` bucket → fixed USD (food 12/26/40/70, `:533-542`).
3. Type guess (museum 18, zoo 30, landmark 0, generic 12, `:548-596`).
Returns a bare `number`: no source, no range, no timestamp, no confidence.
The same $26 "moderate" lunch in Hanoi and Zurich.
Caching (`fetchPOIs`, `:1064`): key = coords at 3 dp (~110 m) + every input
that changes the Google request; 7-day TTL for full pools, 24 h for sparse
ones, never caches a half-failed fetch (`:1264`, `:1279`).

### lib/fx.ts
`getUsdRate(cur)`: live Frankfurter rate, 6 h in-memory cache, 4 s timeout,
static mid-2026 fallback table (`:12`) whose fallback is cached for only ~1 min
(`:92`). Used **only to convert the user's budget into USD and the results
back**. Never applied to place prices. Rate timestamp is not exposed.

### lib/cache.ts
`getCache`/`setCache` over `external_cache`. Best-effort: any DB error = miss,
never fails a request. `CACHE_SCHEMA_VERSION` (`:39`) is baked into the key so
a payload-shape change turns old rows into misses. Lazy eviction on read + a
maintenance sweep. Copy all three ideas.

### lib/planner.ts — `buildTripPlan` (`:493`)
Fixed split per person: `food = min(35%, $180)`, `transport = min(15%, $40)`,
activities = the rest (`:542-545`). Then greedy loops fill each bucket in
popularity/rating order (meals `:846-1060`, attractions `:1113-1202`,
evening `:1306`). Every add is gated by `spent + estimatedCost <= bucket`, so
"never over budget" holds **against the point estimate only**. A $14 lunch
estimated at $12 still passes. Unspent food money cannot buy a museum.
`totalCost` (`:1496`) is a plain sum. Transport legs are fixed guesses
($4 walk/transit, $6/$10 taxi split by party, `:331-363`).

### lib/iqs.ts
Itinerary Quality Score: six 0..1 components (geo-compactness 0.25, meal
quality 0.20, budget utilization 0.15, diversity 0.15, time-of-day 0.15,
hours violations 0.10). Pure function of a plan. Measures *how nice* a plan
is, not *whether its prices were right*.

### RECOMMENDER.md
Design log of ranking fixes R1–R9 and the measure-before-tuning philosophy.
Notes the gap itself: "per-city price calibration (non-USD priceRange
discarded at pois.ts:262)" (`RECOMMENDER.md:16`; line number has since moved
to `:514`). Feedback loop = per-type removal-rate priors with shrinkage,
clamped to ×[0.85, 1.15], 10% holdout. Good statistics hygiene to reuse for
VOYA's recalibration (Phase 6).

### lib/eval.golden.test.ts
Golden gate: 108–288 persona grid × fixed POI universes through the real
planner (`fetchPOIs` mocked), mean IQS per universe compared with a checked-in
baseline at ±0.03. Universes are synthetic until a real capture exists.
**It never checks cost accuracy:** prices in the fixtures are taken as truth.

## One request, end to end

```
POST /trips/plan  (lib/api-spec/openapi.yaml:34, routes/trips.ts:486)
 → expensiveLimiter + dailyCostGuard           spend ceiling (rateLimiters.ts:42)
 → geocodeCity / reverseGeocode                coords rounded to 3 dp
 → getUsdRate(currency) ‖ fetchWeather         fx.ts:64
 → budgetUSD = budget / rate                   routes/trips.ts:615
 → buildTripPlan(budgetUSD)                    planner.ts:493
     → fetchPOIs → nearbySearch ×2 → toPOI → estimateCost   pois.ts:1064, :523
     → fixed 35/15/50 split, greedy fill       planner.ts:542
 → totalCost × rate, per-line Math.round       routes/trips.ts:641-679
 → PlanTripResponse (estimatedCost: number)    openapi.yaml:666
```

## The four gaps (VOYA's reason to exist)

1. **No source, range, confidence or timestamp on a cost.**
   `estimateCost` returns `number` (`pois.ts:523`); the contract has
   `estimatedCost: number` (`openapi.yaml:666`). A real price range and a
   type guess look identical to the user and to the planner.
2. **Non-USD ranges discarded; no per-city scaling.**
   `if (cc && cc !== "USD") return null` (`pois.ts:514`). Fallback buckets are
   fixed USD (`:533-596`); FX is applied to the budget, never to prices.
3. **Fixed % split instead of optimization.**
   `planner.ts:542-545`; greedy fills per bucket; budget check uses the point
   estimate, so the "never over" claim is only as good as the guess.
4. **No feedback from real spending.**
   `trip_events` holds swaps/thumbs (`tripEvents.ts`); priors learn which
   *types* people remove (`priors.ts`), never what anything *cost*.

## Ideas worth copying

- One `external_cache` table, namespaced, versioned keys, TTL + GC sweep.
- Never cache a partial/failed upstream result.
- Spend ceiling persisted across restarts.
- Coordinates at 3 dp (~110 m) in cache keys and stored rows.
- OpenAPI as the single contract.
- Golden-fixture gate with a checked-in baseline and an explicit update flag.
- ToS read *before* building the capture.
