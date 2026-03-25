# TODOS

> **65 completed / 91 remaining.** Last updated: 2026-03-24.
> Dependency graph and execution order validated by eng review.

---

## Completed Work

<details>
<summary>P0 Bugs — all 4 fixed</summary>

- [x] BUG-01: AQI city coordinates (city_lat/city_lon, radius tightened)
- [x] BUG-02: Flight delay metric source-aware (AviationStack delay vs OpenSky count)
- [x] BUG-03: Stale cache preserves fired status
- [x] BUG-04: Oracle genesis hash verified + 4 tests
</details>

<details>
<summary>P0.5 Design — identity upgrade complete</summary>

- [x] DESIGN-01: Light theme with system fonts
- [x] DESIGN-02: Parchment + burnt vermillion (Fraunces/Instrument Sans/JetBrains Mono, 17 color replacements, shared theme.py)
- [x] DESIGN-03: 14 DESIGN.md compliance gaps closed (charts, score card, checklist, oracle artifact, typography, animations)
</details>

<details>
<summary>P1 Data — historical pipeline + precompute</summary>

- [x] DATA-01a: 144 airports × 5yr weather (Open-Meteo)
- [x] DATA-01b: 74 airports × 2yr AQI (OpenAQ v3)
- [x] DATA-01d/e/f: 221 precomputed basis risk reports, rho badges on map, profile page wired
</details>

<details>
<summary>P2 Oracle — fully wired</summary>

- [x] ORACLE-01a-e: Key gen, fetcher signing, R2 upload, Oracle Ledger page
</details>

<details>
<summary>P3-P4 New perils — all shipped</summary>

- [x] Marine: 10 ports, 20 triggers, AISstream WebSocket
- [x] Flood: 20 USGS river gauges
- [x] Cyclone: 20 NOAA NHC location triggers
- [x] Crop/NDVI: 10 agricultural zones, Copernicus/MODIS
- [x] Solar/Space Weather: 5 NOAA SWPC Kp index triggers
- [x] Health/Pandemic: 10 WHO Disease Outbreak News triggers
</details>

<details>
<summary>P5 Intelligence — PREI + AI briefs done</summary>

- [x] INTEL-02: Country Risk Exposure Index on Global Monitor
- [x] INTEL-01: AI risk briefs (Claude API + template fallback), daily digest page, brief on Trigger Profile
</details>

<details>
<summary>P7 Infrastructure — 2256 tests, env audit, AQI diagnostics</summary>

- [x] INFRA-01a-c + new d/e: fetcher, oracle chain, AQI coords, triggers, risk_index (2256 tests)
- [x] INFRA-03: Env var reference table (19 vars) + startup health check
- [x] DATA-02: AQI diagnostic mode + NO STATION status for unavailable triggers
</details>

---

## Track A — COMPLETE (all shipped 2026-03-24)

- [x] **DATA-02a/b:** AQI diagnostic mode + NO STATION status
- [x] **INTEL-01a-d:** AI risk briefs (Claude API), daily digest page (8_Digest.py), brief on Trigger Profile
- [x] **INFRA-03a/b:** Env var reference table (19 vars in DEPLOYMENT.md) + startup health check
- [x] **SRC-04:** Health/Pandemic peril — 10 WHO Disease Outbreak News triggers
- [x] **SRC-05:** Solar/Space Weather peril — 5 NOAA SWPC Kp index triggers

### Still pending (Track A):
- [ ] **DATA-01c:** `scripts/fetch_historical_opensky.py` — 1yr daily departures (resumable, multi-day job)
- [x] **UX-01:** Searchable dropdowns — rich labels ("Delhi DEL — Flight Delay (India)"), sorted alphabetically, type-to-filter. Shared `trigger_selector.py`. Applied to Trigger Profile, Compare, Guided Mode.

---

## Frontend Performance & UX

### FE-01: Speed + caching
- [x] **FE-01a:** `<link rel="preconnect">` for fonts.googleapis.com + fonts.gstatic.com (~100ms saving).
- [x] **FE-01b:** `@st.cache_data` on PREI (5min), basis risk JSON (1hr), digest (5min), account stats (5min).
- [x] **FE-01c:** `st.spinner` on Trigger Profile, Account, and Digest page loads.

### FE-02: Interactions
- [x] **FE-02a:** URL deep linking for triggers — pass `?trigger=flight-delay-del` as query param on Trigger Profile. Currently uses `st.session_state` which doesn't survive page refresh/share.
- [x] **FE-02b:** Mobile bottom nav — sticky footer with 4 key pages (Monitor, Build, Profile, Oracle) for mobile screens. CSS only, no Streamlit change.
- [x] **FE-02c:** Toast feedback — replace `st.success` with `st.toast()` (Streamlit 1.33+) for ephemeral actions. ⚠️ Requires bumping `streamlit>=1.31` to `>=1.33` in requirements.txt.

---

## API Documentation & Quality

### API-03: Developer documentation
**Why:** Auto-generated Swagger at /v1/docs exists but has terse descriptions, no examples, no getting-started guide. Users can't onboard without reading source code.

- [x] **API-03a:** `docs/API_GUIDE.md` — curl examples, SDK snippets, error table, linked from README.
- [x] **API-03b:** Enriched docstrings with Query/Path descriptions for Swagger UI.
- [x] **API-03c:** Dynamic `len(GLOBAL_TRIGGERS)` / `len(PERIL_LABELS)` in API description.
- [x] **API-03d:** `gad/api/models.py` — Pydantic response models on all routes for auto-generated schemas.

### SRC-01/02/03: Additional data sources (standalone)
- [ ] **SRC-01:** NOAA HRRR Smoke data — wildfire impact, GRIB format. Medium effort.
- [ ] **SRC-02:** NOAA GFS weather fallback — authoritative global model behind Open-Meteo. GRIB format.
- [ ] **SRC-03:** NOAA SPI drought index — normalized anomalies. Depends on GPM IMERG (already live).

### Deferred tests
- [ ] **INFRA-01d:** `tests/test_worker_contract.py` — requires Wrangler CLI
- [ ] **INFRA-01e:** `tests/test_marine_aisstream.py` — requires websockets mock

---

## Track B — API Layer (unblocks P8 endpoints + P9 hardening)

**Must be done before:** SL-08a-d, SL-09d, CEO-01/02/03/06, INFRA-02b.

### API-01: FastAPI REST surface
- [x] **API-01a:** `gad/api/main.py` — 7 routes: /v1/triggers, /v1/triggers/{id}, /v1/triggers/{id}/basis-risk, /v1/triggers/{id}/determinations, /v1/status, /v1/ports, /v1/perils.
- [x] **API-01b:** API key auth via X-API-Key header. Opt-in (API_REQUIRE_AUTH env var). Open by default for community access.
- [x] **API-01c:** Dockerfile switched from `&` hack to supervisord (3 processes: streamlit, fetcher, uvicorn). fly.toml updated with API port 8502.
- [x] **API-01d:** Auto-generated OpenAPI docs at /v1/docs, ReDoc at /v1/redoc.

### API-02: MCP server
- [x] **API-02a:** `gad/mcp/server.py` — check_trigger_status, list_triggers_by_location, etc.
- [x] **API-02b:** Deploy as Cloudflare Worker or `/mcp` route

### INFRA-02: Process management (done — merged into API-01c)
- [x] **INFRA-02a:** supervisord replaces `&` pattern. Auto-restart on failure.
- [x] ~~**INFRA-02b:**~~ FastAPI as third supervised process — done in API-01c.

---

## Track C — DuckDB Infrastructure (P8 Phase 0, blocks all learning)

**Strict sequential order.** Each step depends on the previous.

**Design principles:** DuckDB on Fly.io persistent volume. Single writer (fetcher). Read-only dashboard. Supabase stays for auth/user data only. Cost: +$1.50/mo.
**Eng review additions:** Singleton connections, twice-daily backup, CHECKPOINT before copy, flock lock, EVAL_MAP dispatch, geographic bounding (2000km).

### Phase 0: Infrastructure Foundation
**Order:** DB-01a → DB-01b → DB-01x → DB-01c → DB-01d → DB-05 → DB-02a → DB-02b/c → DB-03a/b/c → DB-04

- [x] **DB-01a:** Fly.io volumes provisioned — 10GB prod (bom) + 10GB staging (sin). $1.50/mo each.
- [x] **DB-01b:** Volume mounted in `fly.toml` at `/data` via `[mounts]` block.
- [x] **DB-01x:** `flock` file lock in fetcher — `fcntl.LOCK_EX|LOCK_NB` on `DATA_ROOT/.fetcher.lock`.
- [x] **DB-01c:** `gad/config.py` — centralised paths with auto-detection (`/data` on Fly, `./data` local). 11 files updated. 2298 tests pass.
- [x] **DB-01d:** Volume health check — write/read/delete test file at fetcher startup. `CRITICAL` log on failure.
- [x] **DB-05:** `duckdb>=0.10.0`, `statsmodels>=0.14.0`, `scikit-learn>=1.4.0` added to requirements.txt.
- [x] **DB-02a:** DuckDB schema — 8 tables in `gad/engine/db.py`. Singleton connection (lazy init per eng review).
- [x] **DB-02b:** Write helpers — `gad/engine/db_write.py`. 8 functions, all try/except wrapped.
- [x] **DB-02c:** Read helpers — `gad/engine/db_read.py`. 7 query functions, return DataFrames.
- [x] **DB-03a:** R2 backup — `gad/engine/backup.py`. CHECKPOINT before copy, gzip, upload. `prune_old_backups()` included.
- [x] **DB-03b:** Restore script — `scripts/restore_duckdb.py`. R2 download, gunzip, SHA-256 checksum verification.
- [x] **DB-03c:** Prune old backups — `prune_old_backups(keep_days=30)` in backup.py.
- [x] **DB-04:** Supabase scope confirmed in db.py header comment — auth/user tables stay on Supabase, all analytical tables in DuckDB.

### Phase 1: Time Series Foundation (blocks all learning)
**Depends on:** Phase 0 complete.

- [x] **SL-01a:** `TriggerObservation` model in models.py. Exported from `gad/engine/__init__.py`.
- [x] **SL-01b:** Wired into fetcher — writes observation to DuckDB after each evaluation. try/except wrapped.
- [x] **SL-01c:** `gad/engine/timeseries.py` — get_trigger_timeseries(), get_trigger_stats(), has_enough_observations().
- [x] **SL-01d:** `scripts/backfill_observations.py` — CSV to DuckDB backfill (weather + AQI). Skips existing.
- [x] **SL-09a:** `ModelVersion` model in models.py. Append-only audit trail.
- [x] **SL-09b:** `gad/engine/model_registry.py` — register_model_version() writes to DuckDB + R2 `model-registry/`.
- [x] **SL-09c:** `model_version_id: Optional[UUID] = None` on TriggerDetermination. Added to canonical JSON. Chain-compatible.
- [x] **SL-09d:** `GET /v1/triggers/{id}/model-history` endpoint + `get_model_versions()` in db_read.py.
- [x] **DB-06a:** Daily/weekly flag file debounce (23hr / 6.5day intervals).
- [x] **DB-06b:** `_run_daily_jobs()` (backup + prune) + `_run_weekly_jobs()` (placeholder for Phase 3). Called at end of fetch_all().

### Phase 2: Distribution Learning
**Depends on:** Phase 1 complete.

- [x] **SL-02a:** `distribution_tracker.py` — 90d/365d rolling stats, model versioning. Wired into daily_jobs().
- [x] **SL-02b:** Histogram + stat cards on Trigger Profile (observations, mean, std, firing rate).
- [x] **SL-03a:** `drift_detector.py` — CUSUM: mean shift (>1.5σ), firing rate (>3pp), variance (>50%). Wired into daily_jobs().
- [x] **SL-03b:** "DRIFTING" status with pulsing amber badge on Global Monitor. try/except guarded.
- [x] **SL-03c:** Drift alerts section in daily digest (last 24h alerts).
- [ ] **SL-10a:** Seasonal decomposition (STL). Requires 730+ observations (~2yr of data).
- [ ] **SL-10b:** Season-adjusted thresholds.
- [ ] **SL-10c:** 12-month seasonal bar chart on Trigger Profile.

### Phase 3: Threshold Optimization + Peer Intelligence
**Depends on:** Phase 2 (distributions).

- [ ] **SL-04a:** Threshold optimizer — frequency matching + KS separability.
- [ ] **SL-04b:** Evidence gating (<30 obs = None, 30-99 = low, 100-499 = medium, 500+ = high).
- [ ] **SL-04c:** "Threshold advisor" panel on Trigger Profile.
- [ ] **SL-04d:** "Suggest optimal threshold" in Guided Mode step 3.
- [ ] **SL-05a:** Koppen climate zone lookup.
- [ ] **SL-05b:** Peer index — cosine similarity, top-5 peers. **Depends on:** SL-05a.
- [ ] **SL-05c:** Outlier detection — >2σ from peer median.
- [ ] **SL-06a:** Cold-start inference — weighted-average from 5 nearest peers. **Depends on:** SL-05b.
- [ ] **SL-06b:** Replace "NO DATA" with inferred estimate + progress bar.
- [ ] **SL-06c:** Graduation trigger — cold-start → direct at 30 observations.

### Phase 4: Global Intelligence
**Depends on:** Phase 3 (peers). API endpoints **blocked by** API-01.

- [ ] **SL-07a:** Co-firing correlation matrix — phi coefficient. Geographic bounding 2000km. *(eng review)*
- [ ] **SL-07b:** Correlation clusters toggle on Global Monitor — use Kepler.gl (`streamlit-keplergl`) for advanced map with arcs, heatmaps, time playback. Keep PyDeck as default lightweight view.
- [ ] **SL-07c:** "Correlated triggers" on Trigger Profile.
- [ ] **SL-07d:** Lead-lag analysis for high-phi pairs.
- [x] **SL-08a:** `GET /v1/intelligence/peril-patterns`. **Blocked by:** API-01.
- [x] **SL-08b:** `GET /v1/intelligence/location/{lat}/{lon}`. **Blocked by:** API-01.
- [x] **SL-08c:** `GET /v1/intelligence/climate-zone/{zone}`. **Blocked by:** API-01.
- [x] **SL-08d:** Enhanced PREI using co-firing cluster data.

### Phase 5: User Accounts + Saved Work
**Depends on:** Phase 3 (model versioning).

- [ ] **UA-01:** `user_trigger_annotations` table in Supabase (RLS).
- [ ] **UA-02:** Snapshot on save — model_version_id, threshold_percentile, firing_rate.
- [ ] **UA-03:** Account page watchlist intelligence — calibration drift since save.

---

## Track D — Hardening (blocked by API-01)

### CEO Review Plan Hardening
All items tagged with their phase dependency.

- [x] **CEO-04:** Source recovery cooldown — 2-cycle pause on oracle signing after source recovery.
- [x] **CEO-05:** Per-source rate limiter — sliding-window (FIRMS 5000/10min, WAQI 1000/day, AviationStack 16/day). 11 new tests.
- [ ] **CEO-01:** R2 as API fallback. **Blocked by:** API-01.
- [ ] **CEO-02:** Webhook retry + dead-letter queue. **Blocked by:** API-01. *(Note: overlaps with PLAT-02 — CEO-02 is canonical.)*
- [ ] **CEO-03:** Hash API keys in CF Workers KV. **Blocked by:** API-01.
- [ ] **CEO-06:** Deployment sequence for API layer. **Blocked by:** API-01.

### CEO Deferred Expansions
- [ ] **CEO-07:** Data Adapter Plugin Protocol — `DataSourceAdapter` ABC.
- [ ] **CEO-08:** Verification SDK + CLI — `pip install parametricdata`. *(Note: `python -m gad.verify` already exists — this is packaging.)*
- [ ] **CEO-09:** Trigger Proximity Alerts — notify at 80% threshold.
- [ ] **CEO-10:** Multi-Peril Product Composer — composite products.
- [ ] **CEO-11:** Embeddable Trigger Widget — `<script>` for broker portals.

---

## Track E — Platform & Product Features

### Oracle / verification
- [ ] **PLAT-01:** "Deploy to Oracle" button in Guided Mode wizard.
- [ ] ~~**PLAT-02:** Webhook delivery~~ → **see CEO-02** (same feature, CEO-02 is more detailed).

### Enterprise
- [ ] **PLAT-03:** Parametric Data Pro — premium data (FlightAware), higher refresh, custom triggers, API access, white-label reports.

### Premium data sources
- [ ] **SRC-06:** FlightAware AeroAPI — paid (~$1/query). Enterprise tier only.

---

## Dependency Graph (ASCII)

```
TRACK A (safe now — no deps)          TRACK B (API layer)
  INTEL-01, DATA-01c, DATA-02,          API-01a → 01b → 01c+INFRA-02 → 01d
  INFRA-03, SRC-01-05                        │
                                             ▼
TRACK C (DuckDB — strict order)         unblocks:
  DB-01a/b → DB-01x → DB-01c              SL-08a-d, SL-09d
    → DB-01d → DB-05                       CEO-01/02/03/06
    → DB-02a → DB-02b/c
    → DB-03a/b/c → DB-04
    → Phase 1 (SL-01, SL-09, DB-06)
    → Phase 2 (SL-02, SL-03, SL-10)
    → Phase 3 (SL-04, SL-05, SL-06)
    → Phase 4 (SL-07, SL-08*)
    → Phase 5 (UA-01/02/03)

TRACK D (hardening)
  CEO-04, CEO-05 ← can do now
  CEO-01/02/03/06 ← blocked by API-01

* SL-08 API endpoints blocked by API-01
* SL-09c (model_version_id on TriggerDetermination)
  must be Optional[UUID]=None for chain compat
```

---

## Completed (historical)

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

### v0.2.x — Bug fixes + Design + New Perils (2026-03-24)
- All P0 bugs fixed (AQI coords, flight metric, stale status, oracle genesis)
- Parchment + burnt vermillion design system (Fraunces, Instrument Sans, JetBrains Mono)
- 14 DESIGN.md compliance gaps closed (charts, components, oracle artifact)
- Marine peril (10 ports, AISstream), Flood (20 USGS gauges), Cyclone (20 NHC locations), Crop/NDVI (10 agricultural zones)
- PREI country risk index, collapsible peril expanders
- Oracle signing wired, R2 upload, Oracle Ledger page
- 221 precomputed basis risk reports, rho badges
- 2240 tests (was 13)
- 506 triggers, 10 perils, 13 data sources

### Infrastructure (2026-03-23)
- Domain parametricdata.io live with Cloudflare SSL + DDoS protection
- Dev -> staging -> production workflow with GitHub Actions auto-deploy
- Fly.io hosting with auto-stop, connection limits, cost protection
- Author attribution: "World's first open-source actuarial data platform. Powered by OrbitCover (MedPiper — YC-backed). Built by Nitthin Chandran Nair using Claude Code."
