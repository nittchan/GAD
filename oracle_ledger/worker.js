/**
 * Parametric Data Oracle Ledger — Cloudflare Worker.
 * Serves /determination/{uuid} and /.well-known/oracle-keys.json from R2.
 * Determination pages include in-browser Ed25519 verification via WebCrypto.
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/determination/")) {
      const uuid = url.pathname.split("/determination/")[1]?.split("/")[0];
      if (!uuid) return new Response("Missing determination ID", { status: 400 });

      const object = await env.ORACLE_BUCKET.get(`determinations/${uuid}.json`);
      if (!object) {
        return new Response(render404(), {
          status: 404,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }

      const det = await object.json();
      const accept = request.headers.get("Accept") || "";

      if (accept.includes("application/json") || url.searchParams.get("format") === "json") {
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

function render404() {
  return `<!DOCTYPE html><html><head><title>Parametric Data Oracle</title>
<style>body{background:#0a0e1a;color:#f9fafb;font-family:'JetBrains Mono',monospace;max-width:760px;margin:80px auto;padding:0 24px;text-align:center;}
h1{font-size:14px;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;}
p{color:#6b7280;font-size:14px;}a{color:#00d4d4;}</style>
</head><body><h1>Parametric Data Oracle</h1><p>No determination found with this ID.</p>
<p><a href="https://parametricdata.io">Back to Global Monitor</a></p></body></html>`;
}

function renderDetermination(det) {
  const hasSig = det.signature && det.signature.length > 0;

  // Seal: VERIFIED (green) if signed, UNSIGNED (amber) if v0.1
  const sealColor = hasSig ? "#00d4d4" : "#d29922";
  const sealLabel = hasSig ? "SIGNED" : "UNSIGNED";
  const sealSub = hasSig
    ? `Ed25519 · key: ${det.key_id || "unknown"}`
    : "v0.1 determination — signature not yet applied";

  const firedColor = det.fired ? "#10b981" : "#6b7280";
  const firedLabel = det.fired ? "TRIGGER FIRED" : "NOT FIRED";

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Oracle Determination — ${det.determination_id}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0a0e1a; color: #f9fafb; font-family: 'JetBrains Mono', ui-monospace, monospace;
           max-width: 760px; margin: 0 auto; padding: 48px 24px; }

    /* Seal */
    .seal { border: 2px solid ${sealColor}; border-radius: 4px; padding: 16px 20px;
            margin-bottom: 32px; }
    .seal-label { font-size: 18px; font-weight: 700; color: ${sealColor};
                  letter-spacing: 0.05em; }
    .seal-sub { font-size: 11px; color: #6b7280; margin-top: 4px; }

    /* Result */
    .result { background: #111827; border: 1px solid #1f2937; border-radius: 4px;
              padding: 16px 20px; margin-bottom: 24px; }
    .result-label { font-size: 11px; color: #6b7280; text-transform: uppercase;
                    letter-spacing: 0.1em; margin-bottom: 4px; }
    .result-value { font-size: 24px; font-weight: 700; color: ${firedColor}; }

    /* Header */
    .header { font-size: 11px; color: #6b7280; letter-spacing: 0.1em;
              text-transform: uppercase; margin-bottom: 24px; }
    .header a { color: #00d4d4; text-decoration: none; }

    /* Rows */
    .section-title { font-size: 11px; color: #6b7280; text-transform: uppercase;
                     letter-spacing: 0.1em; margin: 24px 0 12px 0; }
    .row { display: flex; gap: 20px; padding: 10px 0; border-bottom: 1px solid #1f2937; }
    .label { color: #6b7280; width: 180px; flex-shrink: 0; font-size: 12px; }
    .value { color: #f9fafb; font-size: 12px; word-break: break-all; }
    .hash { color: #00d4d4; font-size: 11px; }

    /* Actions */
    .actions { margin-top: 32px; display: flex; gap: 12px; flex-wrap: wrap; }
    a.btn { color: #00d4d4; border: 1px solid #00d4d4; padding: 8px 16px;
            text-decoration: none; font-size: 12px; border-radius: 3px; }
    a.btn:hover { background: rgba(0,212,212,0.1); }

    /* Verify badge */
    #verify-result { margin-top: 12px; padding: 10px 16px; border-radius: 4px;
                     font-size: 12px; display: none; }
    .verify-pass { background: rgba(0,212,212,0.1); border: 1px solid #00d4d4; color: #00d4d4; }
    .verify-fail { background: rgba(248,81,73,0.1); border: 1px solid #f85149; color: #f85149; }

    /* Footer */
    .footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #1f2937;
              font-size: 11px; color: #484f58; }
    .footer a { color: #6b7280; }

    /* Print */
    @media print {
      body { background: white; color: black; }
      .seal { border-color: black; }
      .seal-label { color: black; }
      .hash { color: #006666; }
      .actions { display: none; }
      #verify-result { display: none; }
    }
  </style>
</head>
<body>
  <div class="header">
    <a href="https://parametricdata.io">Parametric Data</a> · Oracle Determination
  </div>

  <!-- Seal -->
  <div class="seal">
    <div class="seal-label">${sealLabel}</div>
    <div class="seal-sub">${sealSub}</div>
  </div>

  <!-- Result -->
  <div class="result">
    <div class="result-label">Determination</div>
    <div class="result-value">${firedLabel}</div>
    <div style="color:#6b7280;font-size:12px;margin-top:4px;">
      ${det.fired_at ? `Fired at ${det.fired_at}` : `Evaluated at ${det.determined_at}`}
    </div>
  </div>

  <!-- Identity -->
  <div class="section-title">Identity</div>
  <div class="row"><span class="label">Determination ID</span>
       <span class="value hash">${det.determination_id}</span></div>
  <div class="row"><span class="label">Trigger ID</span>
       <span class="value hash">${det.trigger_id}</span></div>
  <div class="row"><span class="label">Policy ID</span>
       <span class="value hash">${det.policy_id}</span></div>

  <!-- Integrity -->
  <div class="section-title">Cryptographic Integrity</div>
  <div class="row"><span class="label">Data Snapshot</span>
       <span class="value hash">sha256:${det.data_snapshot_hash}</span></div>
  <div class="row"><span class="label">Computation Version</span>
       <span class="value hash">${det.computation_version}</span></div>
  <div class="row"><span class="label">Previous Hash</span>
       <span class="value hash">sha256:${det.prev_hash}</span></div>
  <div class="row"><span class="label">Signature</span>
       <span class="value hash">${hasSig ? det.signature : "(unsigned)"}</span></div>
  <div class="row"><span class="label">Key ID</span>
       <span class="value hash">${det.key_id || "(none)"}</span></div>

  <!-- In-browser verification -->
  <div id="verify-result"></div>

  <!-- Actions -->
  <div class="actions">
    <a class="btn" href="?format=json">Raw JSON</a>
    <a class="btn" href="/.well-known/oracle-keys.json">Public Keys</a>
    <a class="btn" href="https://parametricdata.io">Global Monitor</a>
    <a class="btn" href="https://github.com/nittchan/GAD">Verify with CLI</a>
    ${hasSig ? '<a class="btn" href="#" onclick="verifyInBrowser();return false;">Verify in Browser</a>' : ''}
  </div>

  <!-- Footer -->
  <div class="footer">
    <p>World's first open-source actuarial data platform.</p>
    <p>Powered by <a href="https://orbitcover.com">OrbitCover</a> (MedPiper — backed by Y Combinator).
       Built by Nitthin Chandran Nair.</p>
  </div>

  ${hasSig ? renderVerifyScript(det) : ''}
</body>
</html>`;
}

function renderVerifyScript(det) {
  // Build the canonical JSON payload (same as Python _canonical_json)
  const payload = JSON.stringify({
    computation_version: det.computation_version,
    data_snapshot_hash: det.data_snapshot_hash,
    determination_id: det.determination_id,
    determined_at: det.determined_at,
    fired: det.fired,
    fired_at: det.fired_at || null,
    key_id: det.key_id || null,
    policy_id: det.policy_id,
    prev_hash: det.prev_hash,
    trigger_id: det.trigger_id,
  });
  // Note: keys are already alphabetically sorted above

  return `<script>
async function verifyInBrowser() {
  const el = document.getElementById('verify-result');
  el.style.display = 'block';
  el.textContent = 'Verifying...';
  el.className = '';

  try {
    // Fetch public key from registry
    const keysResp = await fetch('/.well-known/oracle-keys.json');
    const keysData = await keysResp.json();
    const keys = keysData.keys || [];

    if (keys.length === 0) {
      el.textContent = 'No public keys in registry. Cannot verify.';
      el.className = 'verify-fail';
      return;
    }

    // Find matching key by key_id, or use first
    const keyId = ${JSON.stringify(det.key_id || null)};
    let keyEntry = keys[0];
    if (keyId) {
      const match = keys.find(k => k.key_id === keyId);
      if (match) keyEntry = match;
    }

    // Decode hex public key
    const pubKeyHex = keyEntry.public_key_hex;
    const pubKeyBytes = new Uint8Array(pubKeyHex.match(/.{2}/g).map(b => parseInt(b, 16)));

    // Import as Ed25519 verify key
    const cryptoKey = await crypto.subtle.importKey(
      'raw', pubKeyBytes, { name: 'Ed25519' }, false, ['verify']
    );

    // Canonical payload
    const payload = ${JSON.stringify(payload)};
    const payloadBytes = new TextEncoder().encode(payload);

    // Decode signature
    const sigHex = ${JSON.stringify(det.signature)};
    const sigBytes = new Uint8Array(sigHex.match(/.{2}/g).map(b => parseInt(b, 16)));

    // Verify
    const valid = await crypto.subtle.verify('Ed25519', cryptoKey, sigBytes, payloadBytes);

    if (valid) {
      el.textContent = 'INDEPENDENTLY VERIFIED — Your browser confirmed the signature using WebCrypto.';
      el.className = 'verify-pass';
    } else {
      el.textContent = 'VERIFICATION FAILED — Signature does not match.';
      el.className = 'verify-fail';
    }
  } catch (err) {
    el.textContent = 'Verification error: ' + err.message;
    el.className = 'verify-fail';
  }
}
</script>`;
}
