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

## Background fetcher

The Dockerfile runs the fetcher in the background on startup:
```dockerfile
CMD python -m gad.monitor.fetcher & streamlit run dashboard/app.py ...
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

## Cost summary (approx.)

| Item | Monthly |
|------|---------|
| Cloudflare (parametricdata.io) | ~$10/yr |
| Cloudflare Workers (paid) | $5 |
| Cloudflare R2 | < $0.50 |
| Fly.io production | $3-6 (auto-stop) |
| Fly.io staging | $0-3 (auto-stop) |
| **Total** | **~$10-15** |
