# Deployment — parametricdata.io

Treaty-grade infrastructure: the `/determination/{uuid}` route will be referenced in reinsurance contracts. This doc covers the development workflow, environments, DNS, and hosting.

## Development Workflow

```
dev branch        → local development (no auto-deploy)
                      ↓ merge
staging branch    → auto-deploys to gad-dashboard-staging.fly.dev
                      ↓ verify, then merge
main branch       → auto-deploys to parametricdata.io (production)
```

**Rules:**
- All work happens on `dev` (or feature branches off `dev`).
- Never push directly to `staging` or `main`.
- Merge `dev` → `staging` to test. Merge `staging` → `main` to ship.
- GitHub Actions handle deployment automatically on merge.

## Environments

| Environment | Fly App | URL | Branch | Auto-deploy |
|-------------|---------|-----|--------|-------------|
| **Development** | — | localhost:8501 | `dev` | No |
| **Staging** | gad-dashboard-staging | gad-dashboard-staging.fly.dev | `staging` | Yes |
| **Production** | gad-dashboard | parametricdata.io | `main` | Yes |

Both Fly apps have the same API key secrets (FIRMS, OpenSky, WAQI). Staging uses the same data sources as production — the only difference is the URL.

## GitHub Actions (`.github/workflows/fly-deploy.yml`)

- Push to `staging` → deploys to `gad-dashboard-staging`
- Push to `main` → deploys to `gad-dashboard` (production)
- Requires `FLY_API_TOKEN` secret in GitHub repo settings

## How to deploy

### Local development
```bash
source .venv/bin/activate
python -m gad.monitor.fetcher    # fetch live data
streamlit run dashboard/app.py   # run dashboard
```

### Deploy to staging
```bash
git checkout staging
git merge dev
git push origin staging
# GitHub Action auto-deploys to gad-dashboard-staging.fly.dev
# Verify at https://gad-dashboard-staging.fly.dev
```

### Deploy to production
```bash
git checkout main
git merge staging
git push origin main
# GitHub Action auto-deploys to parametricdata.io
```

### Manual deploy (emergency)
```bash
fly deploy --app gad-dashboard           # production
fly deploy --app gad-dashboard-staging   # staging
```

## Domain and DNS

- **Domain:** `parametricdata.io`
- **Registrar:** Bigrock (nameservers pointed to Cloudflare)
- **DNS:** Cloudflare (authoritative)

### DNS records

| Record | Type | Target | Proxy |
|--------|------|--------|-------|
| `parametricdata.io` | A | `66.241.125.64` | ON |
| `parametricdata.io` | AAAA | `2a09:8280:1::e7:c15f:0` | ON |
| `www` | CNAME | `parametricdata.io` | ON |
| `oracle.parametricdata.io` | CNAME | Cloudflare Worker | ON |

### Fly.io certificates
```bash
fly certs add parametricdata.io
fly certs add www.parametricdata.io
```

## Routing architecture

```
parametricdata.io (production)
├── /                         → Fly.io (Streamlit dashboard + Global Monitor)
├── /determination/{uuid}     → Cloudflare Worker → R2
├── /.well-known/...          → Cloudflare Worker → R2
└── /docs                     → Cloudflare Pages (optional)

gad-dashboard-staging.fly.dev (staging)
└── /                         → Fly.io staging app (same code, same data sources)
```

- **Dashboard:** ~99.5% SLA (Fly.io). Not treaty-critical.
- **Determination ledger + keys:** 99.99% SLA (Cloudflare Workers + R2). Treaty-critical.

## R2 bucket

```bash
cd oracle_ledger
npx wrangler r2 bucket create gad-oracle-determinations
```

## Cloudflare Worker

```bash
cd oracle_ledger
npx wrangler deploy --env production
```

## Environment Variable Reference

Every env var the platform reads, whether it is required, and what breaks without it.

### Infrastructure (required)

| Variable | Required? | Default | Consequence if missing |
|----------|-----------|---------|------------------------|
| `SUPABASE_URL` | **Yes** | — | Auth, saved triggers, and analytics all fail. Dashboard login is broken. |
| `SUPABASE_ANON_KEY` | **Yes** | — | Same as above — Supabase client cannot initialize. |
| `SUPABASE_SERVICE_KEY` | **Yes** | — | Analytics event writes fail (service-role bypass needed for RLS). |

### Data Sources

| Variable | Required? | Default | Consequence if missing |
|----------|-----------|---------|------------------------|
| `NASA_FIRMS_MAP_KEY` | No | — | Wildfire data unavailable. VIIRS + MODIS fetches return `None`. |
| `WAQI_API_TOKEN` | No | — | AQI fallback to OpenAQ only. WAQI source skipped in priority chain. |
| `OPENSKY_CLIENT_ID` | No | — | Flight departure data rate-limited to anonymous tier (~100 credits/day vs 4000). |
| `OPENSKY_CLIENT_SECRET` | No | — | Same as above — both ID and secret are needed for OAuth2. |
| `AVIATIONSTACK_API_KEY` | No | — | No real-time delay data for tier-1 airports. Falls back to OpenSky only. |
| `OPENAQ_API_KEY` | **Yes** (for AQI) | — | OpenAQ v3 returns 401 without a key. AQI coverage reduced to WAQI/AirNow only. |
| `AIRNOW_API_KEY` | No | — | US airport AQI falls back to WAQI. Non-US airports unaffected. |
| `NASA_EARTHDATA_TOKEN` | No | — | GPM IMERG daily precipitation unavailable. Drought falls back to CHIRPS monthly. |
| `AISSTREAM_API_KEY` | No | — | Marine/port congestion data unavailable. All marine triggers return `None`. |

### Oracle Signing (v0.2.2+)

| Variable | Required? | Default | Consequence if missing |
|----------|-----------|---------|------------------------|
| `GAD_ORACLE_PRIVATE_KEY_HEX` | No | — | Oracle signing disabled. Determinations are not signed or hash-chained. |
| `GAD_ORACLE_PUBLIC_KEY_HEX` | No | — | Public key unavailable for verification. Paired with private key. |
| `GAD_ORACLE_KEY_ID` | No | — | Key ID omitted from signed determinations. |

### R2 Upload (oracle ledger)

| Variable | Required? | Default | Consequence if missing |
|----------|-----------|---------|------------------------|
| `R2_ACCOUNT_ID` | No | — | R2 upload disabled. Signed determinations logged locally only. |
| `R2_ACCESS_KEY_ID` | No | — | Same — all three R2 vars are needed for upload. |
| `R2_SECRET_ACCESS_KEY` | No | — | Same — determinations stay local, not served via Cloudflare Worker. |

### AI Features

| Variable | Required? | Default | Consequence if missing |
|----------|-----------|---------|------------------------|
| `ANTHROPIC_API_KEY` | No | — | AI-generated risk briefs unavailable. Monitor runs normally without them. |

---

## Environment variables on Fly.io

Set on BOTH staging and production:

```bash
# Data source keys (required for full monitor coverage)
fly secrets set NASA_FIRMS_MAP_KEY=<key> --app gad-dashboard
fly secrets set OPENSKY_CLIENT_ID=<id> --app gad-dashboard
fly secrets set OPENSKY_CLIENT_SECRET=<secret> --app gad-dashboard
fly secrets set WAQI_API_TOKEN=<token> --app gad-dashboard
fly secrets set AVIATIONSTACK_API_KEY=<key> --app gad-dashboard
fly secrets set OPENAQ_API_KEY=<key> --app gad-dashboard
fly secrets set AIRNOW_API_KEY=<key> --app gad-dashboard
fly secrets set NASA_EARTHDATA_TOKEN=<token> --app gad-dashboard
fly secrets set AISSTREAM_API_KEY=<key> --app gad-dashboard

# Supabase (required for auth and analytics)
fly secrets set SUPABASE_URL=<url> --app gad-dashboard
fly secrets set SUPABASE_ANON_KEY=<key> --app gad-dashboard
fly secrets set SUPABASE_SERVICE_KEY=<key> --app gad-dashboard

# Oracle signing (v0.2.2+ — generate with scripts/generate_oracle_keypair.py)
fly secrets set GAD_ORACLE_PRIVATE_KEY_HEX=<hex> --app gad-dashboard
fly secrets set GAD_ORACLE_PUBLIC_KEY_HEX=<hex> --app gad-dashboard
fly secrets set GAD_ORACLE_KEY_ID=<uuid> --app gad-dashboard

# Repeat all above for staging: --app gad-dashboard-staging
```

### Oracle key setup

```bash
# 1. Generate a key pair (run once, locally)
python3 scripts/generate_oracle_keypair.py

# 2. Set the keys on Fly.io (copy commands from script output)

# 3. Publish the public key to R2 (requires R2 credentials)
python3 scripts/publish_oracle_key.py
```

### R2 credentials (for oracle uploads)

The fetcher automatically uploads signed determinations to R2 when these are set:

```bash
fly secrets set R2_ACCOUNT_ID=<cloudflare_account_id> --app gad-dashboard
fly secrets set R2_ACCESS_KEY_ID=<r2_token_access_key> --app gad-dashboard
fly secrets set R2_SECRET_ACCESS_KEY=<r2_token_secret_key> --app gad-dashboard
```

Without these, determinations are still signed and logged locally but not uploaded to R2.

## Process management

The Dockerfile uses supervisord to manage 3 processes with auto-restart:

| Process | Port | Command |
|---------|------|---------|
| Streamlit dashboard | 8501 | `streamlit run dashboard/app.py` |
| Background fetcher | — | `python -m gad.monitor.fetcher --loop` |
| REST API (FastAPI) | 8502 | `uvicorn gad.api.main:app` |

Config: `supervisord.conf`. All processes restart automatically on failure.

### REST API

OpenAPI docs at `/v1/docs`. Open by default — API key auth opt-in via:
```bash
fly secrets set API_REQUIRE_AUTH=true --app gad-dashboard
fly secrets set API_MASTER_KEY=<your-key> --app gad-dashboard
```

Data is fetched once on machine start, then cached. When the machine auto-stops and restarts, it fetches fresh data again.

## TLS and HSTS

Cloudflare terminates TLS at the edge. Universal SSL is automatic. Set minimum TLS to 1.2. Enable HSTS (max-age=31536000, include subdomains).

## DDoS protection

Cloudflare proxy (orange cloud ON) provides:
- Layer 3/4 DDoS mitigation (automatic)
- Rate limiting (configure in Security → WAF → Rate limiting rules)
- Bot detection (Security → Bots → enable Bot Fight Mode)

Recommended rate limit: 60 requests/minute per IP on the dashboard.

## API Layer Deployment

Sequence for bringing up the public API layer (CF Workers + R2 fallback + key auth).

### 1. Provision Redis (Upstash) — deferred to v0.4

The primary API cache will be Upstash Redis (serverless, per-request pricing). Until then, the fetcher writes trigger-status snapshots directly to R2 as a fallback data source for CF Workers.

### 2. Set up CF Workers KV for API key hashing

API keys are stored as SHA-256 hashes in Cloudflare Workers KV. Generate keys locally:

```bash
python scripts/hash_api_key.py
# Outputs: raw key (give to user) + SHA-256 hash (store in KV)
```

Store the hash in KV namespace `GAD_API_KEYS`:
```bash
npx wrangler kv:key put --binding=API_KEYS "<sha256_hash>" \
  '{"tier":"free","user_id":"<uuid>"}' --env production
```

### 3. Deploy Workers with dual-write (cache + R2 fallback)

The background fetcher already writes to two destinations on every successful trigger evaluation:
- **Local JSON cache** (primary, for dashboard reads)
- **R2 `trigger-status/{trigger_id}.json`** (fallback, for CF Workers when Redis is unavailable)

Deploy the Worker:
```bash
cd oracle_ledger
npx wrangler deploy --env production
```

The Worker reads from R2 `trigger-status/` when the Redis cache misses.

### 4. Verify with integration test

```bash
# Confirm R2 snapshots are being written
npx wrangler r2 object list gad-oracle-determinations --prefix trigger-status/ | head

# Hit the Worker endpoint
curl -s https://oracle.parametricdata.io/trigger-status/flight-delay-blr | jq .

# Verify API key auth (when enabled)
curl -H "Authorization: Bearer pk_<key>" https://api.parametricdata.io/v1/triggers
```

### 5. Cut over DNS

Add a CNAME for `api.parametricdata.io` pointing to the CF Worker:

| Record | Type | Target | Proxy |
|--------|------|--------|-------|
| `api` | CNAME | Cloudflare Worker | ON |

Once verified, update client SDKs and docs to use `api.parametricdata.io`.

## Cost summary (approx.)

| Item | Monthly |
|------|---------|
| Cloudflare (parametricdata.io) | ~$10/yr |
| Cloudflare Workers (paid) | $5 |
| Cloudflare R2 | < $0.50 |
| Fly.io production | $3-6 (auto-stop) |
| Fly.io staging | $0-3 (auto-stop) |
| **Total** | **~$10-15** |
