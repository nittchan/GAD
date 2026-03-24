# TODOS

## P0 — Bugs (wrong data, silent failures)

### BUG-01: AQI triggers use airport coordinates, not city coordinates ← CURRENT SESSION
**Files:** `gad/monitor/airports.py`, `gad/monitor/triggers.py`, `gad/monitor/sources/openaq.py`
**Problem:** Airport lat/lon is the runway. AQI monitors are in city centres. BLR airport is 38km north of Bengaluru. DEL is in Dwarka, not Anand Vihar. 125 AQI triggers pull data for the wrong location.

- [x] **BUG-01a:** Add `city_lat`/`city_lon` fields to `Airport` dataclass, default to `lat`/`lon`
- [x] **BUG-01b:** Populate correct `city_lat`/`city_lon` for 30+ airports where distance > 15km. Audit script: `scripts/audit_airport_city_distance.py`
- [x] **BUG-01c:** AQI trigger generation uses `airport.effective_city_lat`/`effective_city_lon` instead of `airport.lat`/`lon`
- [x] **BUG-01d:** OpenAQ radius tightened from 50km to 15km; AirNow tightened from 50mi to 15mi

### BUG-02: Flight delay metric is flight count, not delay minutes
**Files:** `gad/monitor/sources/opensky.py`, `gad/monitor/triggers.py`, `dashboard/pages/6_Global_Monitor.py`
**Problem:** OpenSky returns flight objects, not delay minutes. Threshold "60 minutes" is compared against wrong metric.

- [x] **BUG-02a:** Confirmed: OpenSky has no scheduled times, delay cannot be computed. `avg_delay_min` was always 0.
- [x] **BUG-02b:** AviationStack already computes real delay correctly. No change needed.
- [x] **BUG-02c:** OpenSky `fetch_departures` now returns `departure_count` (honest metric), `avg_delay_min: None`. `evaluate_trigger` is source-aware: fires on 0 departures (disruption).
- [x] **BUG-02d:** Global Monitor column changed from "Avg Delay" to "Metric" with source-aware labels: "X min delay" (AviationStack) or "X flights" (OpenSky).

### BUG-03: Stale cache shows wrong status label
**Files:** `gad/monitor/cache.py`, `dashboard/pages/6_Global_Monitor.py`
**Problem:** Staleness overwrites fired status — a critical trigger going stale shows as "stale" not "critical + stale".

- [x] **BUG-03a:** Staleness no longer overwrites fired status. `result["status"]` stays `"critical"` when trigger is stale-but-fired.
- [x] **BUG-03b:** Stale-but-fired markers stay red on the map. Status label shows "TRIGGERED (stale)" to indicate both states.

### BUG-04: Oracle log hash chain not started (GENESIS_HASH unused)
**Files:** `gad/engine/oracle.py`, `tests/test_oracle.py`
**Problem:** First entry may write empty `prev_hash` instead of `GENESIS_HASH`.

- [x] **BUG-04a:** Confirmed: `read_last_hash()` already returns `GENESIS_HASH` for empty logs. Added 4 tests: genesis return, first-entry prev_hash, chain verification, and broken-genesis detection.
- [x] **BUG-04b:** Confirmed: `verify_chain()` already validates first entry's `prev_hash == GENESIS_HASH`. Test added for broken genesis case.

---

## P1 — Data Integrity and Coverage

### DATA-01: Historical data download pipeline
**Why:** Most triggers had "no historical data". Platform needs Spearman rho for all triggers. Now 221 of 456 have precomputed reports.

- [x] **DATA-01a:** `scripts/fetch_historical_openmeteo.py` — 5yr daily weather for 144 airports. Open-Meteo Archive API, no key. Output: `data/series/weather/{IATA}_daily.csv`. Gitignored.
- [x] **DATA-01b:** `scripts/fetch_historical_openaq.py` — 2yr daily AQI per city. OpenAQ v3 /sensors/{id}/days endpoint. Probes for best sensor with recent data. Output: `data/series/aqi/{IATA}_aqi_daily.csv`. Writes station mapping log for audit.
- [ ] **DATA-01c:** `scripts/fetch_historical_opensky.py` — 1yr daily departures (resumable)
- [x] **DATA-01d:** `scripts/precompute_basis_risk.py` — 221 reports computed (144 weather + 72 AQI + legacy). 114 with valid rho. Output: `data/basis_risk/{trigger_id}.json`.
- [x] **DATA-01e:** Trigger Profile loads precomputed `BasisRiskReport` from JSON. Falls back to legacy CSV, then placeholder. Full rendering with PDF export.
- [x] **DATA-01f:** Rho badge on Global Monitor — flight table and peril cards show `ρ=X.XX` (green/amber/red). Cached 1hr.

### DATA-02: AQI source fallback order is unverified
- [ ] **DATA-02a:** Add `diagnostic_mode` to fetcher showing source, distance, station name
- [ ] **DATA-02b:** Mark triggers with no station within 25km as `data_source_unavailable`

---

## P2 — Oracle Wiring (trust layer)

### ORACLE-01: Wire Ed25519 signing to live fetcher
**Prerequisite:** BUG-04 fixed.

- [x] **ORACLE-01a:** `scripts/generate_oracle_keypair.py` — generates Ed25519 key pair with Fly.io secret commands. User runs once, never committed.
- [x] **ORACLE-01b:** Already wired in `fetcher.py` (lines 212-283). Creates TriggerDetermination, signs with Ed25519, appends to oracle log after each trigger evaluation. Also fixed inconsistent genesis hash in `seed_oracle_determination.py`.
- [x] **ORACLE-01c:** `scripts/publish_oracle_key.py` — standalone script to upload `oracle-keys.json` to R2 via S3-compatible API.
- [x] **ORACLE-01d:** `gad/engine/r2_upload.py` — uploads per-determination JSON to R2 after signing. Optional (requires R2 credentials). Wired into fetcher, never blocks on failure.
- [x] **ORACLE-01e:** `dashboard/pages/7_Oracle.py` — Oracle Ledger page showing chain status, stats, and 20 most recent determinations with links to the Cloudflare Worker. Added to sidebar nav on all pages.

---

## P3 — New Peril: Marine and Shipping

### MARINE-01: Port registry
- [x] **MARINE-01a:** `gad/monitor/ports.py` with `Port` dataclass (id, name, city, country, lat/lon, anchor_bbox, un_locode, tier)
- [x] **MARINE-01b:** 10 tier-1 ports with anchorage bounding boxes (Singapore, Rotterdam, Shanghai, LA, JNPT, Jebel Ali, Hamburg, Colombo, Port Klang, Busan)
- [x] **MARINE-01c:** 20 marine triggers auto-generated (congestion + dwell time per port)

### MARINE-02: AISstream connector
- [x] **MARINE-02a:** `gad/monitor/sources/aisstream.py` — WebSocket fetcher. Connects to AISstream, subscribes to anchor_bbox, collects position reports for 90s window, deduplicates by MMSI, returns vessel stats.
- [x] **MARINE-02b:** `evaluate_trigger` — congestion (vessels at anchor > threshold) and dwell time (proxy via vessel count)
- [x] **MARINE-02c:** `AISSTREAM_API_KEY` added to env docs (DEPLOYMENT.md, CLAUDE_ENGINEERING.md)
- [x] **MARINE-02d:** Integrated into `fetcher.py` — `fetch_marine()` extracts port_id from trigger_id, looks up port, calls `fetch_port_vessels`
- [x] **MARINE-02e:** "marine" / "Marine / Shipping" added to PERIL_LABELS, PERIL_ICONS, SOURCE_KEY_MAP on all pages, evaluate functions in Global Monitor and fetcher

---

## P4 — New Perils (high commercial value)

### PERIL-01: Flood (NOAA NWS river gauge)
- [ ] **PERIL-01a:** 20 flood gauge locations via USGS Water Services API (free)
- [ ] **PERIL-01b:** `gad/monitor/sources/noaa_flood.py` — fetcher + evaluator
- [ ] **PERIL-01c:** Flood trigger generation in `triggers.py`

### PERIL-02: Tropical cyclone (NOAA NHC)
- [ ] **PERIL-02a:** Active storms fetcher from NHC GeoJSON (free)
- [ ] **PERIL-02b:** 20 high-exposure location triggers
- [ ] **PERIL-02c:** Proximity evaluation (haversine + wind threshold)

### PERIL-03: Crop / NDVI drought index
- [ ] **PERIL-03a:** NASA MODIS NDVI fetcher via AppEEARS or Copernicus WCS
- [ ] **PERIL-03b:** 10 agricultural zone triggers
- [ ] **PERIL-03c:** NDVI threshold evaluation with 16-day composite window

---

## P5 — Intelligence Layer

### INTEL-01: AI risk brief per trigger
- [ ] **INTEL-01a:** `gad/monitor/intelligence.py` — Claude API brief generator (cached daily)
- [ ] **INTEL-01b:** Brief on Trigger Profile page
- [ ] **INTEL-01c:** `generate_global_digest()` — daily summary to `data/digest/`
- [ ] **INTEL-01d:** Digest page (`dashboard/pages/7_Digest.py`)

### INTEL-02: Parametric Risk Exposure Index per country
- [ ] **INTEL-02a:** PREI score computation per country
- [ ] **INTEL-02b:** Choropleth toggle on Global Monitor map

---

## P6 — API and Distribution

### API-01: FastAPI REST surface
- [ ] **API-01a:** `gad/api/main.py` — triggers, basis-risk, determinations, status routes
- [ ] **API-01b:** API key auth middleware (Supabase `api_keys` table)
- [ ] **API-01c:** Deploy alongside Streamlit on Fly.io
- [ ] **API-01d:** Auto-generated OpenAPI docs at `/v1/docs`

### API-02: MCP server
- [ ] **API-02a:** `gad/mcp/server.py` — check_trigger_status, list_triggers_by_location, etc.
- [ ] **API-02b:** Deploy as Cloudflare Worker or `/mcp` route

---

## P7 — Infrastructure and Tests

### INFRA-01: Test coverage gaps
- [ ] **INFRA-01a:** `tests/test_monitor_fetcher.py` — mocked HTTP integration test
- [ ] **INFRA-01b:** `tests/test_oracle_chain.py` — 5 signed determinations, tamper detection (partially done: 3-entry chain + broken genesis tests already in `test_oracle.py`)
- [ ] **INFRA-01c:** `tests/test_aqi_coordinates.py` — haversine sanity for all airports
- [ ] **INFRA-01d:** `tests/test_worker_contract.py` — Wrangler dev contract test
- [ ] **INFRA-01e:** `tests/test_marine_aisstream.py` — mock WebSocket test

### INFRA-02: Dockerfile and process management
- [ ] **INFRA-02a:** Replace `&` pattern with `supervisord` or restart-on-failure script
- [ ] **INFRA-02b:** Add FastAPI as third supervised process when API-01 ships

### INFRA-03: Fly.io secrets audit
- [ ] **INFRA-03a:** Document every env var with consequences of absence
- [ ] **INFRA-03b:** Startup health check logging which data sources are available

---

## Session Sequencing

| Session | Tasks | Outcome |
|---------|-------|---------|
| 1 | BUG-01 (all) | **DONE** — AQI data correct for all 144 airports |
| 2 | BUG-02 (all) | **DONE** — Flight metric accurate or correctly relabelled |
| 3 | BUG-03, BUG-04 | **DONE** — Stale status correct, oracle chain verified with tests |
| 4 | ORACLE-01a–01c | **DONE** — Key gen script, fetcher signing verified, key publish script |
| 5 | ORACLE-01d–01e | **DONE** — R2 upload wired, Oracle Ledger dashboard page |
| 6 | DATA-01a | **DONE** — 144 airports have 5yr weather history |
| 7 | DATA-01b | **DONE** — AQI triggers have history (coverage depends on OpenAQ station availability) |
| 8 | DATA-01c | Flight history fetched |
| 9 | DATA-01d–01f | **DONE** — 221 precomputed reports, rho badges on map, profile page wired |
| 10 | MARINE-01, MARINE-02 | **DONE** — Marine peril: 10 ports, 20 triggers, AISstream connector |
| 11 | PERIL-01 | Flood peril live |
| 12 | PERIL-02 | Cyclone peril live |
| 13 | INTEL-01 | AI risk briefs per trigger |
| 14 | API-01 | REST API live |
| 15 | INFRA-01 | Test coverage closes major gaps |

---

## Completed

### v0.1.0 (2026-03-19)
- Full Design System (DESIGN.md)
- PDF/Export for Basis Risk Reports
- Dashboard with guided/expert modes, trigger profile, compare, account
- Oracle determination schema, signing/verification primitives
- 3 sample triggers (Kenya drought, IndiGo flights, India flood)

### v0.2.0 — Global Monitor (2026-03-23)
- Built `gad/monitor/` package with 5 peril categories
- 426 triggers across 144 airports (50 Indian + 94 global) auto-generated from airport registry
- Background fetcher with cache-based security (users never trigger API calls)
- Interactive world map dashboard (Global Monitor page)
- Legacy engine cleanup (deleted all _legacy files, deprecated app.py)

### v0.2.1 — Multi-Source Data (2026-03-23)
- DataSourceConnector protocol with priority fallback (`gad/monitor/protocol.py`)
- AviationStack connector (tier-1 airports, real schedule vs actual delays)
- AirNow EPA connector (authoritative US AQI)
- OpenAQ v3 auth fix (API key headers)
- FIRMS dual satellite (VIIRS + MODIS merged, deduplicated)
- GPM IMERG connector (daily precipitation)
- Multi-source fetcher: AviationStack->OpenSky, AirNow->WAQI, VIIRS+MODIS, GPM->CHIRPS
- All 8 API keys configured (FIRMS, OpenSky OAuth2, WAQI, AviationStack, OpenAQ, Earthdata, AirNow)

### v0.2 — Page Updates (2026-03-23)
- All pages wired to 436-trigger registry (no more 3-trigger YAML system)
- Trigger Profile: click-through from Global Monitor, live data + basis risk when available
- Compare: searchable dropdown of all 436 triggers, side-by-side with delta table
- Guided Mode: 6 perils (incl. earthquake), outputs MonitorTrigger, computes basis risk
- Expert Mode: JSON editor, validates as MonitorTrigger, "View trigger profile"
- Account -> Monitor Status: per-peril data health, source table, platform stats

### v0.2 — Oracle Primitives + Earthquake + Verify CLI (2026-03-23)
- key_id: Optional[UUID] added to TriggerDetermination model
- GENESIS_HASH constant defined in oracle.py
- OracleLog dual write (per-file JSON + JSONL) with canonical_hash()
- read_last_hash() and verify_chain() for hash chain verification
- Earthquake peril: 10 seismic zones via USGS API (free, no key, real-time)
- Verification CLI: `python -m gad.verify <url-or-file>` and `--chain` mode
- Total triggers: 436 (144 flights + 125 AQI + 8 wildfire + 5 drought + 144 weather + 10 earthquake)

### Infrastructure (2026-03-23)
- Domain parametricdata.io live with Cloudflare SSL + DDoS protection
- Dev -> staging -> production workflow with GitHub Actions auto-deploy
- Fly.io hosting with auto-stop, connection limits, cost protection
- Consistent dark theme, hidden Streamlit chrome, shared footer on all pages
- Author attribution: "World's first open-source actuarial data platform. Powered by OrbitCover (MedPiper — YC-backed). Built by Nitthin Chandran Nair using Claude Code."
