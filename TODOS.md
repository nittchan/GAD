# TODOS

## v0.2 — Remaining

### Pre-built historical basis risk for all 426 triggers
**What:** For each trigger, pre-compute historical basis risk (Spearman rho, back-test) using the engine. Show scores on the map alongside live status.
**Why:** Live status shows "is the trigger firing now." Basis risk shows "how good is this trigger design." Both together make the dashboard valuable.
**Context:** Use `compute_basis_risk()` with historical series data. Currently only 2 legacy triggers (Kenya drought, IndiGo flights) have CSVs. Need to generate historical series from the data source APIs for all 426 triggers.
**Effort:** Large — needs historical data download pipeline per source.
**Depends on:** Multi-source data connectors (done).

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

### Signed determinations
**What:** Enable Ed25519 signing on all trigger determinations produced by the monitor.
**Why:** Cryptographic attestation makes determinations independently verifiable.
**Context:** Signing primitives exist in `gad/engine/oracle.py`. Wire into the fetcher/monitor flow.
**Effort:** Medium.

### Determination status page upgrade
**What:** Upgrade `oracle_ledger/worker.js` to verification proof page (green/red seal, hash chain, in-browser WebCrypto).
**Context:** Design decisions from /plan-design-review. Seal-first hierarchy, oracle palette (#0a0e1a, #00d4d4).
**Depends on:** Signed determinations.
**Effort:** Medium.

### OracleLog dual write (JSONL + per-file JSON)
**What:** Write each determination to JSONL (hash chain, source of truth) and per-file JSON (Worker reads).
**Depends on:** Signed determinations.
**Effort:** Small.

### key_id field + genesis hash constant
**What:** Add `key_id: Optional[UUID]` to TriggerDetermination. Define `GENESIS_HASH` constant.
**Effort:** Small.

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
- All pages wired to 426-trigger registry (no more 3-trigger YAML system)
- Trigger Profile: click-through from Global Monitor, live data + basis risk when available
- Compare: searchable dropdown of all 426 triggers, side-by-side with delta table
- Guided Mode: 5 perils, outputs MonitorTrigger, computes basis risk, "View on map"
- Expert Mode: JSON editor, validates as MonitorTrigger, "View trigger profile"
- Account → Monitor Status: per-peril data health, source table, platform stats

### Infrastructure (2026-03-23)
- Domain parametricdata.io live with Cloudflare SSL + DDoS protection
- Dev → staging → production workflow with GitHub Actions auto-deploy
- Fly.io hosting with auto-stop, connection limits, cost protection
- Consistent dark theme, hidden Streamlit chrome, shared footer on all pages
- Author attribution: "World's first open-source actuarial data platform. Powered by OrbitCover (MedPiper — YC-backed). Built by Nitthin Chandran Nair using Claude Code."
