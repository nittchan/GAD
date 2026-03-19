/**
 * GAD Oracle Ledger — Cloudflare Worker.
 * Serves /determination/{uuid} and /.well-known/oracle-keys.json from R2.
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/determination/")) {
      const uuid = url.pathname.split("/determination/")[1]?.split("/")[0];
      if (!uuid) return new Response("Missing determination ID", { status: 400 });

      const object = await env.ORACLE_BUCKET.get(`determinations/${uuid}.json`);
      if (!object) {
        return new Response(
          "<!DOCTYPE html><html><head><title>GAD Oracle</title></head><body style='background:#0a0e1a;color:#f9fafb;font-family:monospace;padding:2rem;'><h1>Determination not found</h1><p>No determination with this ID in the ledger.</p></body></html>",
          { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } }
        );
      }

      const det = await object.json();
      const accept = request.headers.get("Accept") || "";

      if (accept.includes("application/json") || url.searchParams.has("format=json")) {
        return new Response(JSON.stringify(det, null, 2), {
          headers: {
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=31536000, immutable",
          },
        });
      }

      return new Response(renderDetermination(det), {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    if (url.pathname === "/.well-known/oracle-keys.json") {
      const keys = await env.ORACLE_BUCKET.get("oracle-keys.json");
      const body = keys ? await keys.text() : '{"keys":[]}';
      return new Response(body, {
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "public, max-age=300",
        },
      });
    }

    return new Response("Not found", { status: 404 });
  },
};

function renderDetermination(det) {
  const firedBadge = det.fired
    ? "<span style='color:#10b981;font-weight:700'>YES</span>"
    : "<span style='color:#ef4444;font-weight:700'>NO</span>";

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>GAD Oracle — ${det.determination_id}</title>
  <style>
    body { background: #0a0e1a; color: #f9fafb; font-family: 'JetBrains Mono', monospace;
           max-width: 760px; margin: 60px auto; padding: 0 24px; }
    h1 { font-size: 13px; color: #6b7280; letter-spacing: 0.1em; text-transform: uppercase; }
    .row { display: flex; gap: 24px; padding: 12px 0; border-bottom: 1px solid #1f2937; }
    .label { color: #6b7280; width: 200px; flex-shrink: 0; font-size: 13px; }
    .value { color: #f9fafb; font-size: 13px; word-break: break-all; }
    .hash { color: #00d4d4; font-size: 11px; }
    .actions { margin-top: 32px; display: flex; gap: 16px; }
    a.btn { color: #00d4d4; border: 1px solid #00d4d4; padding: 8px 16px;
            text-decoration: none; font-size: 12px; }
    a.btn:hover { background: rgba(0,212,212,0.13); }
  </style>
</head>
<body>
  <h1>GAD Oracle Determination</h1>
  <div class="row"><span class="label">determination_id</span>
       <span class="value hash">${det.determination_id}</span></div>
  <div class="row"><span class="label">policy_id</span>
       <span class="value hash">${det.policy_id}</span></div>
  <div class="row"><span class="label">trigger_id</span>
       <span class="value hash">${det.trigger_id}</span></div>
  <div class="row"><span class="label">fired</span>
       <span class="value">${firedBadge}</span></div>
  <div class="row"><span class="label">fired_at</span>
       <span class="value">${det.fired_at || "—"}</span></div>
  <div class="row"><span class="label">determined_at</span>
       <span class="value">${det.determined_at}</span></div>
  <div class="row"><span class="label">data_snapshot_hash</span>
       <span class="value hash">sha256:${det.data_snapshot_hash}</span></div>
  <div class="row"><span class="label">gad_version</span>
       <span class="value hash">git:${det.computation_version}</span></div>
  <div class="row"><span class="label">prev_hash</span>
       <span class="value hash">sha256:${det.prev_hash}</span></div>
  <div class="row"><span class="label">signature</span>
       <span class="value hash">${det.signature || "unsigned (v0.1)"}</span></div>
  <div class="actions">
    <a class="btn" href="?format=json">Raw JSON</a>
    <a class="btn" href="https://github.com/orbitcover/gad">Verify with GAD</a>
    <a class="btn" href="/.well-known/oracle-keys.json">Public Keys</a>
  </div>
</body>
</html>`;
}
