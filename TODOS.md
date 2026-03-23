# TODOS

## v0.2 — Global Monitor (In Progress)

### Wire CHIRPS drought data to background fetcher
**What:** Connect the existing CHIRPS pipeline (`gad/pipeline.py`) to the monitor fetcher so drought triggers get live data.
**Why:** 2 of 17 global triggers (Kenya Marsabit, Rajasthan) show "no data" because the fetcher doesn't have a CHIRPS source connector.
**Cons:** None — the pipeline code already exists, just needs wiring.
**Context:** Add a `chirps` case to `fetch_trigger()` in `gad/monitor/fetcher.py`. Use `fetch_chirps_series()` from `gad/pipeline.py`.
**Depends on:** Nothing — can be done immediately.

### Get free API keys for better data quality
**What:** Register for free API keys: NASA FIRMS (wildfire), WAQI (air quality), OpenSky (flight data).
**Why:** Wildfire triggers show "no API key." AQI data falls back to demo token (returns wrong stations). OpenSky hits rate limits without auth.
**Pros:** All free. Unlocks full data for all 17 triggers.
**Context:** NASA FIRMS: firms.modaps.eosdis.nasa.gov/api/area. WAQI: aqicn.org/api. OpenSky: opensky-network.org/apidoc.
**Depends on:** Nothing — account registration only.

### Deploy dashboard to Fly.io
**What:** Deploy the Streamlit dashboard (with Global Monitor) to Fly.io. Run the background fetcher as a scheduled process.
**Why:** The dashboard is functional locally but not publicly accessible.
**Context:** fly.toml is configured. `fly deploy` should work. Fetcher can run as a cron job or Fly.io scheduled Machine.
**Depends on:** API keys (above) for full data quality.

### Add Cloudflare proxy for DDoS protection
**What:** Point the domain through Cloudflare for rate limiting, bot detection, and DDoS mitigation.
**Why:** Public dashboard without DDoS protection risks cost overruns on Fly.io.
**Context:** Cloudflare free tier includes DDoS protection and rate limiting. Configure in Cloudflare DNS dashboard.
**Depends on:** Domain registered and dashboard deployed.

### Add more peril categories and triggers
**What:** Expand beyond 5 perils. Candidates: shipping (AIS data), health (WHO), earthquake (USGS), volcanic (Smithsonian GVP), solar/space weather.
**Why:** More perils = more coverage = closer to "WorldMonitor for parametric insurance."
**Context:** Each peril needs: a free data source API, a source fetcher in `gad/monitor/sources/`, and trigger entries in `gad/monitor/triggers.py`.
**Depends on:** v0.2.0 deployed and stable.

### Pre-built trigger profiles with historical basis risk
**What:** For each of the 17 global triggers, pre-compute historical basis risk (Spearman rho, back-test) using the existing engine. Show scores on the map alongside live status.
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

## v0.3 — Platform

### DataSourceConnector protocol
**What:** Define a Python Protocol for data source connectors with `fetch_raw()`, `parse()`, `evaluate()` methods.
**Why:** Community can contribute new data source connectors without modifying core code.
**Context:** CEO plan accepted this as scope. Start by refactoring existing source fetchers into the protocol.
**Depends on:** v0.2.0 source fetchers stable.

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
**What:** Built `gad/monitor/` package with 5 peril categories (flight delay, air quality, wildfire, drought, extreme weather), 17 pre-built triggers, 4 data source fetchers (OpenSky, OpenAQ/WAQI, NASA FIRMS, Open-Meteo), cache-based security model, background fetcher, and interactive map dashboard page. 15/17 triggers successfully fetch real data.
