# TODOS

## Sprint 1: Close the Actuarial Gap (NEXT SESSION — PRIORITY 1)

The product is called an actuarial data platform. It needs to actually compute actuarial math for more than 2 triggers. This sprint makes every trigger on the map show real Spearman rho, Lloyd's scores, and confusion matrices.

### Task 1.1: Historical data download pipeline
**What:** One script per data source that downloads historical time series for all triggers and writes to `data/series/{trigger_id}.csv` in the format `load_weather_data_from_csv()` already expects (columns: period, trigger_value/index_value, loss_proxy/loss_event).
**Sources and methods:**
- **Open-Meteo** `/v1/archive` endpoint — takes `start_date`/`end_date`, free, no key. Pull 5 years of daily temp/rainfall/wind for all 144 airports. Easiest source.
- **OpenAQ** `/v2/measurements` — takes `date_from`/`date_to` and `location_id`. Pull 2-3 years of daily AQI. Need to first resolve nearest station per airport, then batch download.
- **OpenSky** `/flights/departure` — has `begin`/`end` time window (max 2 hours per call). Pull 1 year of departure history per airport. Must batch carefully to respect 4000 credits/day.
- **USGS Earthquake** API already returns historical data by date range natively. Pull 5 years of M2+ within 200km of each earthquake zone.
- **CHIRPS/GPM IMERG** — pipeline already exists in `gad/pipeline.py`. Extend to download multi-year monthly series for drought triggers.
- **NASA FIRMS** — FIRMS archive endpoint provides historical fire data. Pull 1 year for each wildfire zone.
**Output:** `data/series/{trigger_id}.csv` per trigger. Gitignored (large files). Script: `python -m gad.monitor.historical`
**Effort with CC:** ~2-3 hours (one fetcher per source, they're all REST APIs returning JSON/CSV).

### Task 1.2: Precompute basis risk for all triggers
**What:** Once CSVs exist, run `compute_basis_risk()` across all 436 triggers. Serialize `BasisRiskReport` to JSON. Store at `data/basis_risk/{trigger_id}.json`.
**Implementation:**
```bash
python -m gad.monitor.precompute   # runs once, ~5 min
```
Script reads each `data/series/{trigger_id}.csv`, builds a `TriggerDef`, calls `compute_basis_risk()`, writes the report JSON. Refresh monthly via cron.
**Effort with CC:** ~30 min (the engine already works, just need the orchestration script).

### Task 1.3: Wire precomputed reports into Trigger Profile
**What:** Load precomputed `BasisRiskReport` from `data/basis_risk/{trigger_id}.json` on the Trigger Profile page. Replaces the current "Historical basis risk analysis requires time-series data" placeholder with actual Spearman rho, back-test timeline, scatter plot, confusion matrix, Lloyd's checklist, and PDF export — for every trigger.
**Implementation:** In `dashboard/pages/3_Trigger_profile.py`, check for `data/basis_risk/{trigger_id}.json` before falling back to the legacy CSV check. If found, deserialize `BasisRiskReport` and render with existing dashboard components.
**Effort with CC:** ~15 min (the components already exist, just need to load from JSON instead of computing live).

## v0.2 — Remaining

### NOAA HRRR Smoke data (wildfire impact)
**What:** Add NOAA HRRR smoke plume data for wildfire impact assessment.
**Why:** Fire count alone doesn't capture impact. Smoke data shows which populations are affected.
**API:** Free via NOAA NOMADS. Complex GRIB format — needs processing.
**Effort:** Medium.

### NOAA GFS weather fallback
**What:** Add NOAA GFS as secondary weather source behind Open-Meteo.
**Why:** Direct access to the authoritative global weather model gives more control.
**API:** Free, no key needed. GRIB format — needs processing.
**Effort:** Medium.

### NOAA SPI drought index
**What:** Add Standardized Precipitation Index as supplementary drought metric.
**Why:** SPI normalizes anomalies — "how dry vs normal?" More meaningful than raw mm for insurance triggers.
**Depends on:** GPM IMERG working (done).
**Effort:** Medium.

## v0.2.2 — Oracle Layer

### Wire oracle signing to live monitor (next session)
**What:** Each successful data fetch in the monitor produces a `TriggerDetermination`, signs it with Ed25519, and appends to the oracle log. This connects the existing signing primitives to the live data flow.
**Implementation:**
1. After each trigger evaluation in the fetcher, create a `TriggerDetermination`
2. Call `sign_determination()` with the private key from env
3. Call `append_to_oracle_log()` (dual write: JSONL + per-file JSON)
4. Upload per-file JSON to R2 via Cloudflare API
**Infrastructure already in place:** `sign_determination()`, `verify_determination()`, `append_to_oracle_log()`, `read_last_hash()`, `verify_chain()`, `GENESIS_HASH`, `key_id` field — all built.
**Effort:** Medium — mostly wiring, not new primitives.
**Depends on:** Generate an Ed25519 key pair and set `GAD_ORACLE_PRIVATE_KEY_HEX` + `GAD_ORACLE_PUBLIC_KEY_HEX` in Fly.io secrets.

### Determination status page upgrade
**What:** Upgrade `oracle_ledger/worker.js` to verification proof page (green/red seal, hash chain, in-browser WebCrypto).
**Context:** Design decisions from /plan-design-review. Seal-first hierarchy, oracle palette (#0a0e1a, #00d4d4).
**Depends on:** Signed determinations wired.
**Effort:** Medium.

## v0.3 — Platform & New Perils

### New peril: Earthquake (USGS)
**API:** https://earthquake.usgs.gov/fdsnws/event/1/ — free, no auth, GeoJSON.
**Triggers:** Magnitude-based (M5+ within 200km). **Effort:** Small.

### New peril: Shipping / Marine (AIS)
**API:** MarineTraffic (paid), explore free AIS sources. **Effort:** Large.

### New peril: Health / Pandemic
**API:** WHO Disease Outbreak News (free), ECDC, ProMED. **Effort:** Medium.

### New peril: Solar / Space Weather
**API:** NOAA SWPC (free, no key). Kp index, solar flare alerts. **Effort:** Small.

### Verification SDK and CLI
**What:** `gad.verify` submodule + `python -m gad.verify <url>` CLI. **Effort:** Small.

### Webhook delivery with HMAC-SHA256 auth
**What:** POST signed determinations to settlement endpoints with retries and dead-letter queue. **Effort:** Medium.

### Deploy to Oracle button (dashboard)
**What:** "Deploy to Oracle" in guided mode wizard → registers trigger for live monitoring. **Effort:** Medium.

### Parametric Data Pro (enterprise tier)
**What:** Paid tier: premium data (FlightAware), higher refresh, custom triggers, API access, white-label reports. **Effort:** Large.

### FlightAware AeroAPI (premium flight data)
**What:** Most accurate flight data. Paid only (~$1/query). For enterprise tier. **Effort:** Medium + cost.

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
- Multi-source fetcher: AviationStack→OpenSky, AirNow→WAQI, VIIRS+MODIS, GPM→CHIRPS
- All 8 API keys configured (FIRMS, OpenSky OAuth2, WAQI, AviationStack, OpenAQ, Earthdata, AirNow)

### v0.2 — Page Updates (2026-03-23)
- All pages wired to 436-trigger registry (no more 3-trigger YAML system)
- Trigger Profile: click-through from Global Monitor, live data + basis risk when available
- Compare: searchable dropdown of all 436 triggers, side-by-side with delta table
- Guided Mode: 6 perils (incl. earthquake), outputs MonitorTrigger, computes basis risk
- Expert Mode: JSON editor, validates as MonitorTrigger, "View trigger profile"
- Account → Monitor Status: per-peril data health, source table, platform stats

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
- Dev → staging → production workflow with GitHub Actions auto-deploy
- Fly.io hosting with auto-stop, connection limits, cost protection
- Consistent dark theme, hidden Streamlit chrome, shared footer on all pages
- Author attribution: "World's first open-source actuarial data platform. Powered by OrbitCover (MedPiper — YC-backed). Built by Nitthin Chandran Nair using Claude Code."
