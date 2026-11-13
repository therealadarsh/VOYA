# Data sources

Terms, caching and attribution for each provider. **No scraping** of sites whose
terms forbid it. Test code uses fakes only (`LIVE=1` caps spend at $1/run).

## Status (M1)

| Source | Use | Cache / storage | Attribution |
|---|---|---|---|
| **Cited JSON in `data/`** | Sales tax, transit fares, park fees for launch cities/parks | Indefinite (we own the extracts; each value has `source`, `quote`, `observed_at`) | N/A (rules); UI shows rule source links |
| **Owner price checks** `data/owner_checks/` | Owned `owner_check` evidence (commissioned / visit / official page) | Stored as JSONL with method, URL, `observed_at`; not scraped | Shown in line evidence |
| **Demo catalog** `src/voya/catalog/demo.json` | Planner MVP UI until real connectors land | Bundled; `synthetic: true` | "Demo prices" banner |
| **Foursquare Places API** (client wired; live calls off) | Place search for enrichment. Price level is stored as a level, never converted to dollars | Live calls need `FOURSQUARE_API_KEY`, `VOYA_PLACES_BUDGET_USD`, `VOYA_PLACES_USD_PER_CALL`, and `VOYA_PLACES_LIVE=1`. Tests use a fake HTTP client | Foursquare attribution when a live result is shown |
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
