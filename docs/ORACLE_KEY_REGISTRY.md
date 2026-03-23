# Oracle public key registry

**Purpose:** Used to verify `TriggerDetermination` signatures. Third parties resolving a determination fetch the registry, select the key valid at `determined_at`, and run verification (e.g. `verify_determination()` in v0.2).

**Canonical URL (reserved):**

```
https://oracle.parametricdata.io/.well-known/oracle-keys.json
```

**Status:** Reserved and documented in v0.1. The endpoint may be unpopulated until v0.2 when Ed25519 signing is live.

## JSON format

The registry is a single JSON document:

```json
{
  "keys": [
    {
      "key_id": "uuid",
      "public_key_hex": "...",
      "valid_from": "2026-04-01T00:00:00Z",
      "valid_until_inclusive": "2026-04-30T23:59:59Z",
      "revoked": false,
      "signed_by_intermediate": "..."
    }
  ]
}
```

- **key_id:** Unique identifier (UUID) for the key.
- **public_key_hex:** Ed25519 public key, raw 32 bytes encoded as hex (64 hex chars).
- **valid_from,** **valid_until_inclusive:** ISO 8601 timestamps; the key is valid for determinations with `determined_at` in this range (inclusive).
- **revoked:** If `true`, the key must not be used for verification after the revocation time; optional **revoked_at** may be present.
- **signed_by_intermediate:** Optional; signature or reference from the Tier 2 intermediate key.

Verifiers: fetch the registry, find the key whose validity window contains the determination’s `determined_at`, and run Ed25519 verification of the determination payload using `public_key_hex`. See [GAP_ANALYSIS_ORACLE.md](GAP_ANALYSIS_ORACLE.md) for the signing payload format and key hierarchy.

**Security-sensitive:** Changes to the registry URL or key format require sign-off (see gap analysis doc).
