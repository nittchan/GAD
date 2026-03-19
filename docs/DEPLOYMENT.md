# GAD deployment — oracle.gad.dev

Treaty-grade infrastructure: the `/determination/{uuid}` route will be referenced in reinsurance contracts. This doc covers DNS, dashboard hosting, and the oracle Worker.

## Domain and DNS

- **Register** `gad.dev` at Cloudflare Registrar (keeps DNS and registrar in one place).
- **Authoritative DNS** at Cloudflare. Do not delegate to a third-party nameserver.

### DNS records

| Record | Type | Target | Proxy |
|--------|------|--------|-------|
| `oracle.gad.dev` | CNAME | Your dashboard host (e.g. Fly.io) | ON |
| DNSSEC | — | Enable in Cloudflare → DNS → Settings → DNSSEC | — |
| `gad.dev` | CAA | `0 issue "letsencrypt.org"` | — |
| `gad.dev` | CAA | `0 issuewild ";"` (no wildcards) | — |

## Routing architecture

```
oracle.gad.dev
├── /                         → Fly.io (Streamlit dashboard)
├── /determination/{uuid}     → Cloudflare Worker → R2
├── /.well-known/...          → Cloudflare Worker → R2
└── /docs                     → Cloudflare Pages (optional)
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
# Production (oracle.gad.dev):
npx wrangler deploy --env production
```

Ensure `wrangler.toml` production routes point to `oracle.gad.dev` with zone_name `gad.dev`.

## Fly.io dashboard

From repo root:

```bash
# Build and deploy (after adding fly.toml and dashboard/Dockerfile)
fly launch --name gad-dashboard --region bom
# Or: fly deploy
```

Example `fly.toml`:

```toml
app = "gad-dashboard"
primary_region = "bom"

[build]
  dockerfile = "dashboard/Dockerfile"

[http_service]
  internal_port = 8501
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
```

Example `dashboard/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
```

## TLS and HSTS

Cloudflare terminates TLS at the edge. Universal SSL is automatic. Set minimum TLS to 1.2 (SSL/TLS → Edge Certificates). Enable HSTS (max-age=31536000, include subdomains).

## Cost summary (approx.)

| Item | Monthly |
|------|---------|
| Cloudflare Registrar (gad.dev) | ~\$1.50 |
| Cloudflare Workers (paid) | \$5 |
| Cloudflare R2 | \< \$0.50 |
| Fly.io (dashboard) | \$6 |
| **Total** | **~\$13** |
