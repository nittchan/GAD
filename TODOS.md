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
**Why:** Most triggers had "no historical data". Platform needs Spearman rho for all triggers. Now 221 of 496 have precomputed reports.

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

## P0.5 — Design: Identity Upgrade ← CURRENT SESSION

### DESIGN-01: Initial light theme (DONE)
- [x] All sub-tasks completed — basic light theme with system fonts.

### DESIGN-02: Parchment + Burnt Vermillion identity upgrade
**Why:** DESIGN.md overhauled with "Industrial-Editorial" direction. Warm parchment palette, Fraunces serif, Instrument Sans body, JetBrains Mono data, copper accents, oracle notarial artifacts. Competitive gap: no one owns "warm, authoritative, light" in insurance/data.

- [x] **DESIGN-02a:** `.streamlit/config.toml` updated — parchment `#F5F0EB`, vellum `#EDE7E0`, burnt vermillion `#C8553D`, obsidian `#1E1B18`.
- [x] **DESIGN-02b:** `dashboard/components/theme.py` — shared Google Fonts loader (Fraunces + Instrument Sans + JetBrains Mono) + font CSS. `inject_theme(st)` called on all pages.
- [x] **DESIGN-02c:** 17 color replacements across all 8 pages — full parchment palette applied. All old Primer/system colors gone.
- [x] **DESIGN-02d:** Status badges updated — TRIGGERED carmine, NORMAL verdigris, NO DATA warm gray, STALE amber. All with semantic bg colors.
- [x] **DESIGN-02e:** Rho badges updated — verdigris/amber/carmine with matching bg tints.
- [x] **DESIGN-02f:** Global Monitor — tooltip parchment, flight table, trigger cards, PREI table all use new palette.
- [x] **DESIGN-02g:** Oracle Ledger page — patina green `#467B6B` for oracle elements, warm palette throughout.
- [x] **DESIGN-02h:** Homepage — Fraunces via inject_theme, burnt vermillion CTAs, parchment bg.

### DESIGN-03: Close DESIGN.md compliance gaps ← CURRENT
**Why:** Eng review audit found 14 gaps between DESIGN.md spec and actual code. Components (score_card, charts, checklist) still have v0.1 dark theme. Oracle notarial artifact not built. Typography tokens not applied.

**Critical (visible, breaks aesthetic):**
- [x] **DESIGN-03a:** Plotly charts — parchment bg `#F5F0EB`, Instrument Sans labels, JetBrains Mono ticks, semantic scatter colors (verdigris/carmine/amber/gray).
- [x] **DESIGN-03b:** Score card — parchment bg, verdigris/amber/carmine rho color, `data-copper` (#7A2E1F) for Lloyd's, `tabular-nums`.
- [x] **DESIGN-03c:** Lloyd's checklist — parchment bg, 4px left border, verdigris pass / carmine fail, Instrument Sans body.
- [x] **DESIGN-03d:** Oracle notarial artifact — corner crop marks (::before/::after in patina green 0.4 opacity), stamp header "⊕ CRYPTOGRAPHICALLY SIGNED DETERMINATION", 2-column fields grid, "CHAIN VERIFIED ✓" signature block.
- [x] **DESIGN-03e:** Hero font-weight 700, Fraunces font-family, letter-spacing -0.03em. Button radius 3px. Feature card radius 6px.
- [x] **DESIGN-03f:** Sidebar bg `#E3DCD3` (surface-2) via theme.py `!important`.
- [x] **DESIGN-03g:** `data-copper` (#7A2E1F) for stat numbers. CSS classes `.data-copper`, `.data-hash`, `.data-coord`, `.data-time` in theme.py.
- [x] **DESIGN-03h:** `font-variant-numeric: tabular-nums` on all code/JetBrains Mono in theme.py. `text-wrap: balance` on h1/h2/h3.
- [x] **DESIGN-03i:** Count-up animation `@keyframes countUp` in theme.py. Applied to stat-number on homepage.
- [x] **DESIGN-03j:** Form input styling — JetBrains Mono + tabular-nums, 3px radius, accent focus ring `rgba(200,85,61,0.12)`. Button hover to `#A8432E`.

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
- [x] **PERIL-01a:** 20 flood gauge locations via USGS Water Services API (free)
- [x] **PERIL-01b:** `gad/monitor/sources/noaa_flood.py` — fetcher + evaluator. Reads real-time river gauge levels from USGS Water Services.
- [x] **PERIL-01c:** Flood trigger generation in `triggers.py` — 20 flood triggers across US flood-prone zones.

### PERIL-02: Tropical cyclone (NOAA NHC)
- [x] **PERIL-02a:** Active storms fetcher from NHC GeoJSON (free). `gad/monitor/sources/noaa_nhc.py` fetches active cyclone advisories.
- [x] **PERIL-02b:** 20 high-exposure coastal location triggers generated in `triggers.py`.
- [x] **PERIL-02c:** Proximity evaluation (haversine + wind threshold) implemented in noaa_nhc.py evaluator.

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
- [x] **INTEL-02a:** PREI score computation per country — `gad/monitor/risk_index.py` computes composite risk scores.
- [x] **INTEL-02b:** Choropleth toggle on Global Monitor map — PREI overlay available.

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

### INFRA-01: Test coverage (2209 tests, was 13)
- [x] **INFRA-01a:** `tests/test_monitor_fetcher.py` — 32 tests. evaluate_fired for all 9 sources, FETCH_MAP coverage, IATA extraction, determination creation.
- [x] **INFRA-01b:** `tests/test_oracle_chain.py` — 12 tests. 5-entry chain, tamper detection, deterministic hash, key_id.
- [x] **INFRA-01c:** `tests/test_aqi_coordinates.py` — ~700 tests. All airports non-zero city coords, haversine sanity, AQI uses city coords.
- [x] **INFRA-01d-new:** `tests/test_triggers.py` — ~1500 tests. 496 count, unique IDs, field validation, marine/flood/cyclone integrity.
- [x] **INFRA-01e-new:** `tests/test_risk_index.py` — 17 tests. PREI formula, empty input, near-threshold, cap at 100.
- [ ] **INFRA-01d:** `tests/test_worker_contract.py` — Wrangler dev contract test (deferred)
- [ ] **INFRA-01e:** `tests/test_marine_aisstream.py` — mock WebSocket test (deferred)

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
| 11 | PERIL-01 | **DONE** — Flood peril: 20 triggers, USGS Water Services connector |
| 12 | PERIL-02 | **DONE** — Cyclone peril: 20 triggers, NOAA NHC connector |
| 13 | INTEL-01 | AI risk briefs per trigger |
| 14 | API-01 | REST API live |
| 15 | INFRA-01 | Test coverage closes major gaps |

---

## P8 — DuckDB Infrastructure + Self-Learning Actuary (2026-03-24)

Source: `GAD_MASTER_TASKS.md` + `/plan-ceo-review` of `parametricdata_design_plan.docx`.
**Supersedes:** Eng plan's Redis/Upstash caching (Phase 1). Redis deferred to Phase 2 API only.
**Design principles:** DuckDB on Fly.io persistent volume. Single writer (fetcher). Read-only dashboard. Supabase stays for auth/user data only. Cost: +$1.50/mo.

### Phase 0: Infrastructure Foundation (blocks everything)

- [ ] **DB-01a:** Provision Fly.io persistent volume (10GB, `sin` region, prod + staging). `$1.50/mo`.
- [ ] **DB-01b:** Mount volume in `fly.toml` at `/data`.
- [ ] **DB-01c:** Centralise all data paths — new `gad/config.py` with `DATA_ROOT`, `CACHE_DIR`, `SERIES_DIR`, `BASIS_RISK_DIR`, `ORACLE_DIR`, `DB_PATH`, `BACKUP_DIR`, `MODEL_DIR`. Replace all `Path("data/")` and `"data/"` string literals codebase-wide.
- [ ] **DB-01d:** Volume health check at fetcher startup — write/read/delete test file, `logger.critical` if volume not mounted.
- [ ] **DB-02a:** DuckDB schema + `init_db()` — 8 tables: `trigger_observations`, `trigger_distributions`, `drift_alerts`, `threshold_suggestions`, `trigger_peers`, `trigger_correlations`, `model_versions`, `seasonal_profiles`. New file: `gad/engine/db.py`.
- [ ] **DB-02b:** Write helpers — `gad/engine/db_write.py`. One function per table. All wrapped in try/except (never raise on DuckDB failure).
- [ ] **DB-02c:** Read helpers — `gad/engine/db_read.py`. Fast analytical queries for dashboard and API.
- [ ] **DB-03a:** R2 daily backup — `gad/engine/backup.py`. Gzip DuckDB, upload to R2. ~$0.01/mo.
- [ ] **DB-03b:** Restore script — `scripts/restore_duckdb.py`. Document in DEPLOYMENT.md.
- [ ] **DB-03c:** Prune old backups — keep last 30 days, delete older from R2.
- [ ] **DB-04:** Supabase scope reduction — confirm: only `profiles`, `saved_triggers`, `api_keys`, `gad_events`, auth stay on Supabase. All analytical/learning tables go to DuckDB.
- [ ] **DB-05:** Add `duckdb>=0.10.0`, `statsmodels>=0.14.0`, `scikit-learn>=1.4.0` to requirements.txt.

### Phase 1: Time Series Foundation (blocks all learning)

- [ ] **SL-01a:** `TriggerObservation` model in `gad/engine/models.py` — atomic unit of the learning layer.
- [ ] **SL-01b:** Wire into fetcher — after each trigger evaluation, write observation to DuckDB.
- [ ] **SL-01c:** `gad/engine/timeseries.py` — thin read abstraction over DuckDB.
- [ ] **SL-01d:** Backfill historical data as observations — `scripts/backfill_observations.py`. Run once per source.
- [ ] **DB-06a:** Daily/weekly flag file pattern in fetcher for job scheduling.
- [ ] **DB-06b:** `daily_jobs()` and `weekly_jobs()` functions — compute distributions, drift, thresholds, seasonality, backup. Wire into fetcher fetch cycle.
- [ ] **SL-09a:** Model versioning — `ModelVersion` in models.py. Append-only audit trail. **Elevated to Phase 1** per Codex review: decision traceability must exist before any learning layer writes.
- [ ] **SL-09b:** JSON copy to R2 `model-registry/` for URL-addressable versions.
- [ ] **SL-09c:** Link `model_version_id` to `TriggerDetermination` — every determination traceable to its calibration state.
- [ ] **SL-09d:** `GET /v1/triggers/{id}/model-history` API endpoint.

### Phase 2: Distribution Learning

- [ ] **SL-02a:** Distribution tracker — `gad/engine/distribution_tracker.py`. Rolling 90d and 365d distributions for all triggers. Min 10 observations.
- [ ] **SL-02b:** Surface on Trigger Profile page — histogram, threshold line, percentile label, 90d vs annual firing rate comparison.
- [ ] **SL-03a:** Drift detector — `gad/engine/drift_detector.py`. CUSUM on mean shift (>1.5σ), firing rate change (>3pp), variance change (>50%).
- [ ] **SL-03b:** "DRIFTING" as 4th status state on Global Monitor map — amber pulsing ring.
- [ ] **SL-03c:** Drift alerts in daily digest.
- [ ] **SL-10a:** Seasonal decomposition — `gad/engine/seasonal.py`. STL decomposition. Requires 730+ observations (2yr).
- [ ] **SL-10b:** Season-adjusted thresholds for triggers with strong seasonality.
- [ ] **SL-10c:** 12-month seasonal bar chart on Trigger Profile page.

### Phase 3: Threshold Optimization + Peer Intelligence

- [ ] **SL-04a:** Threshold optimizer — `gad/engine/threshold_optimizer.py`. Two objectives: frequency matching + distributional separability (KS statistic).
- [ ] **SL-04b:** Evidence gating: <30 obs = None, 30-99 = low, 100-499 = medium, 500+ = high confidence.
- [ ] **SL-04c:** "Threshold advisor" panel on Trigger Profile page.
- [ ] **SL-04d:** "Suggest optimal threshold" button in Guided Mode wizard step 3.
- [ ] **SL-05a:** Koppen climate zone lookup — `gad/monitor/climate_zones.py`. Beck et al. 2018 raster.
- [ ] **SL-05b:** Peer index — `gad/engine/peer_index.py`. Cosine similarity on features. Top-5 peers per trigger. Weekly recompute.
- [ ] **SL-05c:** Outlier detection — flag triggers >2σ from peer median firing rate.
- [ ] **SL-06a:** Cold-start inference — `gad/engine/cold_start.py`. Weighted-average distribution from 5 nearest peers. Source: `cold_start_inference`.
- [ ] **SL-06b:** Replace "NO DATA" on Trigger Profile with inferred estimate + progress bar.
- [ ] **SL-06c:** Graduation trigger — auto-switch from cold-start to direct at 30 observations.

### Phase 4: Global Intelligence

- [ ] **SL-07a:** Co-firing correlation matrix — `gad/engine/correlation_matrix.py`. Phi coefficient for all pairs with 100+ overlapping observations. Weekly recompute.
- [ ] **SL-07b:** Correlation clusters toggle on Global Monitor map — `pydeck LineLayer`.
- [ ] **SL-07c:** "Correlated triggers" panel on Trigger Profile page.
- [ ] **SL-07d:** Lead-lag analysis for high-phi pairs — "leading indicator" surface.
- [ ] **SL-08a:** Global intelligence API — `GET /v1/intelligence/peril-patterns`.
- [ ] **SL-08b:** `GET /v1/intelligence/location/{lat}/{lon}` — all triggers within 500km.
- [ ] **SL-08c:** `GET /v1/intelligence/climate-zone/{zone}`.
- [ ] **SL-08d:** Enhanced PREI score using co-firing cluster data.

### Phase 5: User Accounts + Saved Work

- [ ] **UA-01:** `user_trigger_annotations` table in Supabase (RLS enabled).
- [ ] **UA-02:** Snapshot on save — record model_version_id, threshold_percentile, firing_rate at time of save.
- [ ] **UA-03:** Account page watchlist intelligence — calibration drift since save.

---

## P9 — CEO Review Findings (2026-03-24)

Source: `/plan-ceo-review` of `parametricdata_design_plan.docx`.

### Plan Hardening

- [ ] **CEO-01:** R2 as API fallback — fetcher writes trigger status JSON snapshots to R2. CF Workers: Redis first, R2 fallback. **Phase 2 API only.**
- [ ] **CEO-02:** Webhook retry + dead letter queue — 3 retries with exponential backoff. Failed deliveries to Supabase `webhook_failures`. **Phase 2.**
- [ ] **CEO-03:** Hash API keys in CF Workers KV — `SHA-256(key) → {tier, user_id}`. Never plaintext. **Phase 2.**
- [ ] **CEO-04:** Source recovery cooldown — 2-cycle (30 min) after `very_stale` recovery before resuming oracle signing. **Phase 1.**
- [ ] **CEO-05:** Per-source rate limiter in fetcher — respect per-source limits (FIRMS: per-10-min, WAQI: 1000/day). **Phase 1.**
- [ ] **CEO-06:** Deployment sequence for API layer — provision Redis → dual-write → verify → deploy Workers. **Phase 2.**

### Deferred Expansions

- [ ] **CEO-07:** Data Adapter Plugin Protocol — formalize `DataSourceAdapter` ABC with plugin discovery. **P2.**
- [ ] **CEO-08:** Verification SDK + CLI — `pip install parametricdata` + npm package. **P2.**
- [ ] **CEO-09:** Trigger Proximity Alerts — notify at 80% threshold. **P2.**
- [ ] **CEO-10:** Multi-Peril Product Composer — composite products with backtesting + Lloyd's PDF. **P3.**
- [ ] **CEO-11:** Embeddable Trigger Widget — `<script>` for broker portals. **P3.**

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
