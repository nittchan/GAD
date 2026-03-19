# Oracle ledger (Cloudflare Worker)

Serves the GAD determination ledger at `/determination/{uuid}` and the public key registry at `/.well-known/oracle-keys.json`.

## Routes

- **GET /determination/{uuid}** — Returns the determination JSON from R2 (`determinations/{uuid}.json`). Accept `application/json` or `?format=json` for JSON; otherwise returns HTML.
- **GET /.well-known/oracle-keys.json** — Returns the key registry from R2 (`oracle-keys.json`), or `{"keys":[]}` if not present.

## How determinations get written to R2

- **v0.1:** Local only. Use `gad.engine.oracle.append_to_oracle_log(det)` to write to `registry/determinations/{uuid}.json`. To expose a determination via the Worker, upload that file to R2: `wrangler r2 object put gad-oracle-determinations/determinations/{uuid}.json --file=registry/determinations/{uuid}.json`.
- **v0.2:** Worker or API that accepts signed determinations and writes to R2 (TBD).

## Deploy

```bash
cd oracle_ledger
npx wrangler deploy
# Production: npx wrangler deploy --env production
```

Ensure the R2 bucket `gad-oracle-determinations` exists (`npx wrangler r2 bucket create gad-oracle-determinations`).
