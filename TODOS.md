# TODOS

## v0.2.1 — Multi-Source Data (Next Session)

### Multi-source architecture (DataSourceConnector protocol)
**What:** Refactor data fetching so each peril has multiple sources. The fetcher picks the best available reading (freshest, highest confidence, nearest station). If one source is down, it falls back to the next.
**Why:** Single-source is fragile. OpenSky has rate limits (4000/day for 144 airports). WAQI demo token returns wrong stations. Multiple sources = better coverage, higher reliability, more accurate data.
**Architecture:**
```
peril: flight_delay
  sources:
    1. AviationStack (best: has schedule vs actual)  ← primary
    2. OpenSky Network (current, free)               ← fallback
    3. FlightAware AeroAPI (most accurate)           ← premium fallback

peril: air_quality
  sources:
    1. WAQI with real token (current, good global)   ← primary
    2. OpenAQ v3 (open data, many stations)          ← fallback
    3. AirNow EPA (authoritative for US)             ← US-specific

peril: wildfire
  sources:
    1. NASA FIRMS VIIRS (current, near real-time)    ← primary
    2. NASA FIRMS MODIS (different satellite)         ← complementary
    3. NOAA HRRR Smoke (smoke plume data)            ← supplementary

peril: extreme_weather
  sources:
    1. Open-Meteo (current, free, no key)            ← primary
    2. NOAA GFS (authoritative US/global forecasts)  ← fallback
    3. ERA5 Copernicus (historical reanalysis)       ← historical

peril: drought
  sources:
    1. NASA GPM IMERG (daily precipitation satellite) ← primary
    2. CHIRPS (current, monthly rainfall)             ← fallback
    3. NOAA SPI (Standardized Precipitation Index)   ← supplementary
```
**Implementation:** Define `DataSourceConnector` protocol in `gad/monitor/protocol.py`:
```python
class DataSourceConnector(Protocol):
    name: str
    priority: int  # lower = preferred
    async def fetch(self, lat: float, lon: float) -> RawReading | None: ...
    def parse(self, raw: RawReading) -> ParsedReading: ...
```
Fetcher calls sources in priority order, stops at first success. Logs which source was used.
**Depends on:** Current single-source fetchers working and deployed.

### Flight delay: Add AviationStack
**What:** Add AviationStack as primary flight delay source (has scheduled vs actual departure times — real delay calculation).
**Why:** OpenSky doesn't provide scheduled times, so we can't compute actual delays. AviationStack has this data.
**API:** Free tier = 500 requests/month (~16/day). Enough for tier-1 airports only. Paid = $50/mo for 10,000 req.
**Account needed:** Sign up at https://aviationstack.com (free, no credit card).
**Rate limit strategy:** Use AviationStack for tier-1 airports (30), OpenSky for the rest (114).
**Depends on:** Account registration.

### Flight delay: Add FlightAware AeroAPI (future/premium)
**What:** FlightAware AeroAPI — most accurate flight data, real schedule vs actual.
**Why:** Premium data quality for enterprise tier (parametricdata.io/pro).
**API:** Paid only (~$1/query or monthly plans). Not for free tier.
**Context:** Defer until paid enterprise version. Track as v0.3 scope.
**Depends on:** Revenue / enterprise tier.

### Air quality: Wire OpenAQ v3 properly
**What:** Fix OpenAQ v3 integration (currently returns 401 — needs API key since v3 launched).
**Why:** OpenAQ has the most open-data stations globally. Currently falling back to WAQI for everything.
**API:** Free with API key. Register at https://explore.openaq.org (OpenAQ Explorer account).
**Implementation:** Update `gad/monitor/sources/openaq.py` to use v3 auth headers.
**Depends on:** OpenAQ account registration.

### Air quality: Add AirNow EPA (US-specific)
**What:** Add US EPA AirNow as a high-authority source for US airports.
**Why:** AirNow is the official US government AQI source. More authoritative than WAQI for US locations.
**API:** Free with API key. Register at https://docs.airnowapi.org/account/request
**Implementation:** New file `gad/monitor/sources/airnow.py`. Use for US airports only (detect by country="USA").
**Depends on:** AirNow API key registration.

### Wildfire: Add FIRMS MODIS (complementary satellite)
**What:** Fetch from MODIS satellite in addition to VIIRS. Same FIRMS API, different `source` parameter.
**Why:** MODIS and VIIRS have different orbits — MODIS may detect fires VIIRS misses and vice versa. Combined = better coverage.
**API:** Same NASA FIRMS MAP KEY (already have). Just change source param from `VIIRS_SNPP_NRT` to `MODIS_NRT`.
**Implementation:** Fetch both in `firms.py`, merge fire counts (deduplicate by proximity).
**Can do NOW:** Yes — no new account needed.
**Depends on:** Nothing.

### Wildfire: Add NOAA HRRR Smoke (future)
**What:** Add NOAA HRRR smoke plume data for wildfire impact assessment.
**Why:** Fire count alone doesn't capture impact. Smoke data shows which populations are affected.
**API:** Free via NOAA NOMADS. Complex GRIB format — needs processing.
**Depends on:** v0.2.1 multi-source architecture. Medium complexity.

### Weather: Add NOAA GFS forecasts
**What:** Add NOAA GFS (Global Forecast System) as secondary weather source.
**Why:** NOAA GFS is the authoritative global weather model. Open-Meteo already uses GFS data, but direct access gives more control.
**API:** Free, no key needed. NOMADS server. But returns GRIB files — needs processing.
**Implementation:** New file `gad/monitor/sources/noaa_gfs.py`. Start with simple point forecast.
**Can do NOW:** Yes — no account needed. But GRIB parsing adds complexity.
**Depends on:** Nothing, but medium complexity.

### Drought: Add NASA GPM IMERG (daily precipitation)
**What:** Add NASA GPM IMERG as primary drought data source (daily satellite precipitation).
**Why:** CHIRPS is monthly — too slow for real-time monitoring. GPM IMERG has daily data at 10km resolution.
**API:** Free. Requires NASA Earthdata login at https://urs.earthdata.nasa.gov/
**Data:** PMM API provides last 60 days of IMERG Early Run data. 0.1° × 0.1° resolution.
**Implementation:** New file `gad/monitor/sources/gpm_imerg.py`.
**Depends on:** NASA Earthdata account registration.

### Drought: Add NOAA SPI (Standardized Precipitation Index)
**What:** Add NOAA SPI as a supplementary drought metric.
**Why:** SPI normalizes precipitation anomalies — "how dry is this compared to normal?" More meaningful than raw mm for insurance triggers.
**API:** Available via NOAA Climate Data Online. Free with token.
**Depends on:** GPM IMERG working first (SPI is derived from precipitation data).

### API keys to register (action items for Nitthin)
**What:** Register for free API keys needed for multi-source expansion.
**Accounts to create:**
1. AviationStack — https://aviationstack.com (free, 500 req/mo)
2. OpenAQ v3 — https://explore.openaq.org (free, API key for v3)
3. AirNow EPA — https://docs.airnowapi.org/account/request (free)
4. NASA Earthdata — https://urs.earthdata.nasa.gov/ (free, for GPM IMERG)
**Already have:** NASA FIRMS (done), WAQI (done), OpenSky OAuth2 (done)
**Depends on:** Nothing — just account registrations, all free.

## v0.2 — Update Legacy Pages to New Registry (Next Session)

### Wire all pages to the 426-trigger registry
**What:** The v0.1 pages (Guided mode, Expert mode, Trigger profile, Compare, Account) still use the old 3-trigger YAML system. Update them to work with the new `gad/monitor/` trigger registry.
**Why:** Right now the product is split — Global Monitor shows 426 live triggers, but clicking into any other page drops you into a disconnected 3-trigger world. The product needs to feel unified.
**Priority:** HIGH — this is the #1 UX problem. Users land on the map, see data, then can't do anything with it.

### Trigger Profile: click-through from Global Monitor
**What:** When a user clicks a trigger on the Global Monitor map (or in the trigger table), navigate to the Trigger Profile page showing the full basis risk analysis for that trigger.
**Flow:** Global Monitor → click "Delhi DEL" → Trigger Profile page with Spearman rho, back-test timeline, confusion matrix, Lloyd's checklist, PDF export.
**Implementation:**
1. Add click handler on Global Monitor that sets `st.session_state["selected_trigger"]` and calls `st.switch_page("pages/3_Trigger_profile.py")`
2. Update Trigger Profile to read from `MonitorTrigger` + cached data instead of `schema/examples/` YAML
3. The basis risk engine (`compute_basis_risk()`) needs weather_data — use cached fetcher data + historical series
**Depends on:** Historical data pipeline for each trigger location.
**Interim solution:** Show the cached live data (current value, threshold, status) on the profile page even without historical basis risk. Better than nothing.

### Compare: side-by-side from registry
**What:** Update Compare page to let users pick any 2 triggers from the 426-trigger registry and compare them.
**Implementation:** Replace the old 3-trigger dropdown with a searchable selector from `GLOBAL_TRIGGERS`. Show cached live values side-by-side.
**Depends on:** Trigger Profile working with new registry.

### Guided Mode: build custom trigger → add to registry
**What:** When a user builds a custom trigger in Guided Mode, add it to the monitor. The trigger appears on the Global Monitor map and starts getting live data.
**Implementation:**
1. Guided Mode wizard builds a `MonitorTrigger` from user input
2. Save to a user_triggers.json file (or Supabase when auth is ready)
3. Fetcher picks up user triggers alongside the pre-built ones
**Depends on:** Monitor registry supporting dynamic triggers (currently static list).

### Expert Mode: YAML → MonitorTrigger
**What:** Update Expert Mode to output a `MonitorTrigger` compatible with the new registry, not just the old `TriggerDef`.
**Implementation:** Parse YAML into MonitorTrigger fields. Validate against schema. Offer "Add to Global Monitor" button.
**Depends on:** Guided Mode working with new registry.

### Account page: saved triggers from registry
**What:** Account page currently reads from Supabase (which isn't set up). Update to show the user's custom triggers from the local registry.
**Depends on:** Supabase or local user trigger storage.

## v0.2 — Global Monitor (Completed Items)

### Wire CHIRPS drought data to background fetcher
**Completed:** 2026-03-23
**What:** Connected CHIRPS pipeline to the monitor fetcher via `chirps_monitor.py`. Kenya and Rajasthan drought triggers now show real rainfall data.

### Get free API keys for better data quality
**Completed:** 2026-03-23
**What:** Registered NASA FIRMS (wildfire), WAQI (AQI), OpenSky OAuth2 (flights). All keys configured in `.env` and Fly.io secrets.

### Deploy dashboard to Fly.io
**Completed:** 2026-03-23
**What:** Deployed to gad-dashboard.fly.dev. Custom domain parametricdata.io configured with Cloudflare SSL.

### Add Cloudflare proxy for DDoS protection
**Completed:** 2026-03-23
**What:** Domain on Cloudflare with proxy enabled. TXT record for Fly cert verification.

### Add more peril categories and triggers
**Status:** Partially complete. 144 airports (50 India + 94 global), 426 triggers. Need more peril categories (earthquake, shipping, health — see v0.3).

### Pre-built trigger profiles with historical basis risk
**What:** For each of the 426 global triggers, pre-compute historical basis risk (Spearman rho, back-test) using the existing engine. Show scores on the map alongside live status.
**Why:** Live status shows "is the trigger firing now." Basis risk shows "how good is this trigger design." Both together make the dashboard valuable.
**Context:** Use `compute_basis_risk()` with historical series data. Cache results alongside live data.
**Depends on:** Historical series data for each trigger location.

## v0.2.2 — Oracle Layer

### Signed determinations
**What:** Enable Ed25519 signing on all trigger determinations produced by the monitor.
**Why:** Cryptographic attestation makes determinations independently verifiable.
**Context:** Signing primitives exist in `gad/engine/oracle.py`. Need to wire into the fetcher/monitor flow.
**Depends on:** v0.2.0 Global Monitor deployed and stable.

### Determination status page upgrade
**What:** Upgrade `oracle_ledger/worker.js` to show a verification proof page (green/red seal, hash chain, in-browser WebCrypto verification).
**Why:** The current Worker shows raw data. The upgrade shows proof.
**Context:** Design decisions made in /plan-design-review. Seal-first hierarchy, oracle palette (#0a0e1a bg, #00d4d4 accent).
**Depends on:** Signed determinations enabled.

### OracleLog dual write (JSONL + per-file JSON)
**What:** Write each determination to both a JSONL append log (hash chain) and per-file JSON (for Worker reads).
**Why:** JSONL provides sequential hash-chain verification. Per-file JSON supports the existing Worker read pattern.
**Context:** Engineering decision from /plan-eng-review. JSONL is source of truth.
**Depends on:** Signed determinations.

### Add key_id field to TriggerDetermination
**What:** Add `key_id: Optional[UUID] = None` to the TriggerDetermination model. Include in signing payload.
**Why:** When operational keys rotate (every 30 days), verifiers need to know which key signed which determination.
**Context:** Engineering decision from /plan-eng-review. Schema versioning strategy documented in CEO plan.
**Depends on:** Nothing — additive change.

### Fix genesis hash constant
**What:** Define `GENESIS_HASH = hashlib.sha256(b"GAD_ORACLE_LOG_GENESIS").hexdigest()` in `gad/engine/oracle.py`.
**Why:** The hash chain needs a fixed starting point before the first determination is logged.
**Context:** Verify no existing determinations in R2 before committing the value.
**Depends on:** Nothing.

## v0.3 — Platform & New Perils

### DataSourceConnector protocol (formalized)
**What:** Formalize the multi-source protocol from v0.2.1 into a stable API that community contributors can implement.
**Why:** Community can contribute new data source connectors without modifying core code.
**Context:** v0.2.1 builds the working multi-source fetcher. v0.3 extracts it into a clean protocol with docs and examples.
**Depends on:** v0.2.1 multi-source architecture working.

### New peril: Earthquake (USGS)
**What:** Add earthquake monitoring via USGS Earthquake Hazards API (free, real-time, no key).
**API:** https://earthquake.usgs.gov/fdsnws/event/1/ — free, no auth, GeoJSON format.
**Triggers:** Magnitude-based (e.g., M5+ within 200km of insured location).

### New peril: Shipping / Marine (AIS)
**What:** Add vessel tracking and port delay monitoring.
**API:** MarineTraffic API (paid), UN/LOCODE for ports. Explore free AIS sources.
**Triggers:** Port congestion, vessel delay, route deviation.

### New peril: Health / Pandemic
**What:** Add disease outbreak and health risk monitoring.
**API:** WHO Disease Outbreak News (free), ECDC (European), ProMED.
**Triggers:** Outbreak declaration, case count thresholds by region.

### New peril: Solar / Space Weather
**What:** Add solar storm and geomagnetic activity monitoring.
**API:** NOAA SWPC (free, no key). Kp index, solar flare alerts.
**Triggers:** Geomagnetic storm (Kp >= 7), X-class solar flare.

### Verification SDK and CLI
**What:** Package `verify_determination()` as `gad.verify` submodule. Add `python -m gad.verify <url>` CLI.
**Why:** Makes "anyone can verify" actionable for third-party developers.
**Context:** Start as submodule, not separate PyPI package until external consumers exist.
**Depends on:** Signed determinations.

### Webhook delivery with HMAC-SHA256 auth
**What:** POST signed determinations to configured settlement endpoints with HMAC-SHA256 authentication and exponential backoff retries.
**Why:** Enables automated settlement triggered by oracle determinations.
**Context:** Webhook contract defined in `docs/ORACLE_WEBHOOK_AND_LOG.md`. Dead-letter queue for failed deliveries.
**Depends on:** Signed determinations, OracleLog.

### Deploy to Oracle button (dashboard)
**What:** Add "Deploy to Oracle" button in guided mode wizard. After scoring a trigger, users can deploy it to live monitoring.
**Why:** Bridges pre-trade analysis and post-trade monitoring in one product.
**Context:** Design decisions made in /plan-design-review. Step 5 in wizard flow.
**Depends on:** Oracle monitor, Supabase-based policy discovery.

### Parametric Data Pro (enterprise tier)
**What:** Paid tier with premium data sources (FlightAware), higher refresh rates, custom triggers, API access, white-label reports.
**Why:** Revenue model. Free tier uses open data; Pro tier adds commercial data sources and SLA guarantees.
**Context:** Similar to WorldMonitor Pro. Pricing TBD.
**Depends on:** Free tier stable and demonstrating value.

## Completed

### Legacy Engine Cleanup
**Completed:** 2026-03-23
**What:** Deleted legacy files, deprecated root app.py, and legacy-only pipeline functions. Zero legacy imports remain.

### Full Design System (DESIGN.md)
**Completed:** v0.1.0 (2026-03-19)

### PDF/Export for Basis Risk Reports
**Completed:** v0.1.0 (2026-03-19)

### Global Monitor v0.2.0 — Initial Build
**Completed:** 2026-03-23
**What:** Built `gad/monitor/` package with 5 peril categories, 426 triggers across 144 airports (50 Indian + 94 global) auto-generated from master airport registry, 4 data source fetchers (OpenSky, OpenAQ/WAQI, NASA FIRMS, Open-Meteo, CHIRPS), cache-based security model, background fetcher, and interactive map dashboard page. Deployed to parametricdata.io with Cloudflare DDoS protection.

### Domain and Deployment
**Completed:** 2026-03-23
**What:** Domain parametricdata.io purchased, Cloudflare DNS configured, Fly.io SSL cert issued. Dev → staging → production workflow with GitHub Actions auto-deploy. All API keys (FIRMS, OpenSky OAuth2, WAQI) configured.

### Author Attribution
**Completed:** 2026-03-23
**What:** Footer on all pages: "World's first open-source actuarial data platform. Powered by OrbitCover (MedPiper — backed by Y Combinator). Built and maintained by Nitthin Chandran Nair using Claude Code."
