# Oracle webhook interface and OracleLog append contract

**Purpose:** v0.1 schema definitions for the data pipeline gap (Gap 5). Real-time polling and live delivery ship in v0.2; this document defines the **webhook interface schema** and the **OracleLog append contract** so implementations and integrations can target a stable contract.

**See also:** [GAP_ANALYSIS_ORACLE.md](GAP_ANALYSIS_ORACLE.md) (Gap 5), [gad/oracle_models.py](../gad/oracle_models.py) (`TriggerDetermination`).

---

## 1. Webhook interface schema

The oracle runtime delivers each new determination to downstream systems (OrbitCover settlement, reinsurer reporting, public audit) via HTTP POST to a configured webhook URL.

### 1.1 Request

| Aspect | Contract |
|--------|----------|
| **Method** | `POST` |
| **URL** | Configured per environment (e.g. settlement endpoint); not fixed in v0.1. |
| **Content-Type** | `application/json` |
| **Body** | Single JSON object: the **TriggerDetermination** (see [Payload shape](#12-payload-shape)). |
| **Idempotency** | Callers may send the same determination more than once (e.g. retries). Receivers MUST treat `determination_id` as the idempotency key: duplicate IDs are idempotent (return success, no side effect). |
| **Optional headers** | `X-Request-ID` (UUID) for correlation; `Authorization` (v0.2, when auth is required). |

### 1.2 Payload shape

The body is a single `TriggerDetermination` encoded as JSON. Field names and types must match [gad/oracle_models.py](../gad/oracle_models.py):

| Field | Type | Description |
|-------|------|-------------|
| `determination_id` | UUID string | Unique idempotency key for this determination. |
| `policy_id` | UUID string | Policy this determination is for. |
| `trigger_id` | string | Trigger definition id. |
| `fired` | boolean | Whether the trigger fired. |
| `fired_at` | ISO 8601 datetime | When the trigger fired. |
| `data_snapshot_hash` | string | SHA-256 hex of raw input data. |
| `computation_version` | string | GAD git commit or version tag. |
| `determined_at` | ISO 8601 datetime | When this determination was produced. |
| `signature` | string | Ed25519 signature hex; empty string in v0.1. |
| `prev_hash` | string | Hash of previous log entry (hash chain). |

Example (v0.1, unsigned):

```json
{
  "determination_id": "550e8400-e29b-41d4-a716-446655440000",
  "policy_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "trigger_id": "kenya_drought_ndvi",
  "fired": true,
  "fired_at": "2026-03-19T12:00:00Z",
  "data_snapshot_hash": "a1b2c3...",
  "computation_version": "a1b2c3d4",
  "determined_at": "2026-03-19T12:00:05Z",
  "signature": "",
  "prev_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### 1.3 Response and retries

| Status | Meaning |
|--------|---------|
| `2xx` | Success. Receiver has accepted the determination (and will process idempotently by `determination_id`). |
| `4xx` | Client error. Sender MUST NOT retry with the same body (e.g. invalid payload). |
| `5xx` / network error | Transient. Sender SHOULD retry with exponential backoff; same body (same `determination_id`) is idempotent. |

Recommended: at least 3 retries with backoff (e.g. 1s, 2s, 4s). No requirement to persist undelivered determinations in v0.1; v0.2 may add a dead-letter or replay queue.

---

## 2. OracleLog append contract

The OracleLog is an **append-only** log of trigger determinations. Every determination produced by the oracle is appended exactly once. Ordering and hash-chain semantics enable tamper detection and public audit.

### 2.1 Invariants

- **Append-only:** New entries are appended at the end. No updates or deletions of existing entries. No insertion in the middle.
- **One record per determination:** Each log entry is exactly one `TriggerDetermination`. No batching of multiple determinations into one record.
- **Hash chain:** Each determination’s `prev_hash` is the hash of the **canonical serialization** of the previous log entry (see [2.3](#23-entry-hash)). Genesis entry uses a fixed value (e.g. SHA-256 of the string `"GAD_ORACLE_LOG_GENESIS"` or a documented constant).
- **Order:** Log order is the order in which determinations were appended. Consumers MUST verify that `determined_at` and `prev_hash` order are consistent (no backdated inserts).

### 2.2 Record format

- **Storage format:** JSON Lines (one JSON object per line, UTF-8). Each line is the full `TriggerDetermination` JSON (same shape as webhook payload).
- **File or API:** v0.1 defines the **contract** (append-only, one record per line, hash chain). Implementation may be file-based (e.g. append to `oracle_log.jsonl`) or an API (e.g. `POST /log/append` that appends and returns the new index). Public read access (e.g. GET of the log or export) is required for audit; exact URL/API is environment-specific.

### 2.3 Entry hash

For hash-chain verification, the “previous entry” hash is computed over the **previous log line** in canonical form:

- Serialize the previous `TriggerDetermination` to JSON with **canonical key order** (e.g. lexicographic by key) and no unnecessary whitespace.
- `prev_hash = SHA-256(UTF-8(canonical_json)).hex()`.

So the chain is: `genesis_hash → hash(entry_1) → hash(entry_2) → …`. Each determination’s `prev_hash` must equal the hash of the preceding line. v0.2 will also sign the same canonical payload (or a defined signing payload that includes `prev_hash`).

### 2.4 Verification (v0.2)

Walk the log in order; for each line:

1. Parse JSON to `TriggerDetermination`.
2. Check `prev_hash` equals the hash of the previous line (or genesis for the first).
3. Verify `signature` using the public key from the key registry for the key valid at `determined_at`.

Any break in the chain or invalid signature invalidates the log from that point forward.

---

## 3. v0.1 vs v0.2

| Item | v0.1 | v0.2 |
|------|------|------|
| Webhook | Schema and contract defined; URL and delivery are config/TODO. | Live delivery to settlement and reporting endpoints; auth as needed. |
| OracleLog | Append contract and record format defined; implementation may be stub or file-based. | Append-only store with hash-chain verification and public read; signing on every append. |
| Signature | `signature` field present but empty. | Ed25519 signing; `verify_determination()` and key registry. |

Defining these contracts in v0.1 ensures that when v0.2 implements the real-time pipeline and signing, the wire format and log format do not change — avoiding breaking changes for existing log consumers or webhook receivers.
