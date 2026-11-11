# Data sources

Terms, caching and attribution for each provider. **No scraping** of sites whose
terms forbid it. Test code uses fakes only (`LIVE=1` caps spend at $1/run).

## Status (M1)

| Source | Use | Cache / storage | Attribution |
|---|---|---|---|
| **Cited JSON in `data/`** | Sales tax, transit fares, park fees for launch cities/parks | Indefinite (we own the extracts; each value has `source`, `quote`, `observed_at`) | N/A (rules); UI shows rule source links |
| **Owner price checks** `data/owner_checks/` | Owned `owner_check` evidence (commissioned / visit / official page) | Stored as JSONL with method, URL, `observed_at`; not scraped | Shown in line evidence |
| **Demo catalog** `src/voya/catalog/demo.json` | Planner MVP UI until real connectors land | Bundled; `synthetic: true` | "Demo prices" banner |
| **Foursquare Places API** (chosen, not wired in M1) | Ratings, categories, price tier for enrichment | Per Foursquare ToS (IDs + allowed fields; TTL in `external_cache` when implemented) | Foursquare logo/link in UI when shown |
| **OpenStreetMap / Overpass** | POI backfill (later) | ODbL: derived DB in separate table; attribute © OSM | © OpenStreetMap contributors |
| **NPS API** | Park fees, alerts (later live) | API key; cache alerts per NPS guidance | NPS attribution |
| **Recreation.gov RIDB** | Tours/permits (later) | API key | RIDB / Recreation.gov credit |
| **GTFS / agency fares** | `fare_quote` lines | Static files in `data/` refreshed manually | Agency name + link |
| **OpenRouter** | Helper/narration | No prompt logging of secrets; traces redacted | N/A |

## Foursquare Places (commercial, ≤$50 one-time enrichment)

- **Why:** Fits the owner's one-time data budget for launch-city enrichment; official API only.
- **Not in repo:** API key via `FOURSQUARE_API_KEY` (`.env.example` when wired).
- **Spend ceiling:** Persisted counter; hard stop before exceeding budget (see plan 3.8).

## Coordinates

Stored and logged at **≤3 decimal places** (~110 m). Device GPS stays in the browser.
