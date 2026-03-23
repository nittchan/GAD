# Deployment — parametricdata.io

Treaty-grade infrastructure: the `/determination/{uuid}` route will be referenced in reinsurance contracts. This doc covers DNS, dashboard hosting, and the oracle Worker.

## Domain and DNS

- **Domain:** `parametricdata.io`
- **Authoritative DNS** at Cloudflare. Do not delegate to a third-party nameserver.

### DNS records

| Record | Type | Target | Proxy |
|--------|------|--------|-------|
| `parametricdata.io` | A / CNAME | Fly.io dashboard app | ON |
| `oracle.parametricdata.io` | CNAME | Cloudflare Worker (or Fly.io) | ON |
| DNSSEC | — | Enable in Cloudflare → DNS → Settings → DNSSEC | — |
| `parametricdata.io` | CAA | `0 issue "letsencrypt.org"` | — |
| `parametricdata.io` | CAA | `0 issuewild ";"` (no wildcards) | — |

## Routing architecture

```
parametricdata.io
├── /                         → Fly.io (Streamlit dashboard + Global Monitor)
├── /determination/{uuid}     → Cloudflare Worker → R2
├── /.well-known/...          → Cloudflare Worker → R2
└── /docs                     → Cloudflare Pages (optional)

oracle.parametricdata.io
├── /determination/{uuid}     → Cloudflare Worker → R2
└── /.well-known/oracle-keys.json → Cloudflare Worker → R2
```

- **Dashboard:** ~99.5% SLA (Fly.io). Not treaty-critical.
- **Determination ledger + keys:** 99.99% SLA (Cloudflare Workers + R2). Treaty-critical.

## R2 bucket

```bash
cd oracle_ledger
npx wrangler r2 bucket create gad-oracle-determinations
```

- **Versioning:** OFF (determinations are write-once).
- **Public access:** OFF (served via Worker only).

## Cloudflare Worker

```bash
cd oracle_ledger
npx wrangler deploy
# Production (oracle.parametricdata.io):
npx wrangler deploy --env production
```

Ensure `wrangler.toml` production routes point to `oracle.parametricdata.io` with zone_name `parametricdata.io`.

## Fly.io dashboard

From repo root:

```bash
fly launch --name gad-dashboard --region bom
# Or: fly deploy
```

### Environment variables on Fly.io

```bash
fly secrets set NASA_FIRMS_MAP_KEY=<key>
fly secrets set OPENSKY_CLIENT_ID=<id>
fly secrets set OPENSKY_CLIENT_SECRET=<secret>
fly secrets set WAQI_API_TOKEN=<token>
fly secrets set SUPABASE_URL=<url>
fly secrets set SUPABASE_ANON_KEY=<key>
fly secrets set SUPABASE_SERVICE_KEY=<key>
```

### Background fetcher

The fetcher runs as a scheduled process to keep the monitor cache fresh:

```bash
# Option 1: Fly.io scheduled Machine (recommended)
# Add to fly.toml: [processes] fetcher = "python -m gad.monitor.fetcher --loop --interval 900"

# Option 2: External cron (e.g., GitHub Actions, cron-job.org)
# Run every 15 minutes: python -m gad.monitor.fetcher
```

## TLS and HSTS

Cloudflare terminates TLS at the edge. Universal SSL is automatic. Set minimum TLS to 1.2 (SSL/TLS → Edge Certificates). Enable HSTS (max-age=31536000, include subdomains).

## DDoS protection

Cloudflare proxy (orange cloud ON) provides:
- Layer 3/4 DDoS mitigation (automatic)
- Rate limiting (configure in Security → WAF → Rate limiting rules)
- Bot detection (Security → Bots → enable Bot Fight Mode)

Recommended rate limit: 60 requests/minute per IP on the dashboard.

## Cost summary (approx.)

| Item | Monthly |
|------|---------|
| Cloudflare (parametricdata.io) | ~$10/yr domain |
| Cloudflare Workers (paid) | $5 |
| Cloudflare R2 | < $0.50 |
| Fly.io (dashboard) | $6 |
| **Total** | **~$12** |
