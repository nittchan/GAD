# GAD: gap analysis — from actuarial tool to oracle standard

**Document status:** Internal architecture decision record  
**Applies to:** GAD v0.1 and forward  
**Last updated:** 2026-03-19  
**Author:** OrbitCover

---

## The core distinction

GAD as currently designed is a pre-trade actuarial tool. It answers:
> "Is this trigger design sound before we deploy it?"

The oracle standard requires post-trade settlement infrastructure. It answers:
> "Did this specific trigger fire, for this specific policy, at this specific moment, irrefutably?"

These are different functions. GAD solves the first. The second doesn't exist in the current design.
Every gap below traces back to this distinction.

---

## Gap 1: Static analysis vs real-time event detection

**Current state:** Historical back-test engine. Takes a trigger definition and historical weather data, computes Spearman rho, produces a BasisRiskReport. Reproducible. Auditable. Correct for its purpose.

**Missing:** A live trigger monitor. A process that runs continuously, ingests real-time data streams (OpenSky, DGCA live feed, METAR current observations), evaluates trigger conditions against active policies, and emits a signed trigger event when a threshold is crossed.

```python
# What GAD has - batch analysis
report = compute_basis_risk(trigger_def, historical_data)

# What the oracle needs - real-time event loop
async def monitor_trigger(trigger_def, policy_id):
    async for observation in live_data_stream(trigger_def.data_source):
        if trigger_def.condition(observation):
            yield TriggerEvent(
                policy_id=policy_id,
                trigger_id=trigger_def.id,
                fired_at=observation.timestamp,
                observation=observation,
                condition_met=True
            )
```

GAD's computation engine produces a `BasisRiskReport`. The oracle must produce `TriggerEvent` objects in real time. These are different data models with different architectural requirements.

**Gap size:** Large  
**Deferrable:** Real-time polling loop can ship in v0.2. But the `TriggerEvent` data model must be defined in v0.1 — retrofitting a signed event schema onto an existing log is a breaking change.

---

## Gap 2: No cryptographic integrity layer

This is the single largest structural gap.

The current design has zero mention of signing, hashing, or tamper-evidence. Every trigger determination GAD produces is a number in a database or a Streamlit render. Nothing makes it irrefutable after the fact. A reinsurer cannot accept it as settlement basis. A regulator cannot certify it.

**Required data structure — every trigger determination must be a signed artifact:**

```python
@dataclass
class TriggerDetermination:
    determination_id: UUID       # always UUID
    policy_id: UUID
    trigger_id: UUID
    fired: bool
    fired_at: datetime
    data_snapshot_hash: str      # SHA-256 of raw input data
    computation_version: str     # GAD git commit hash
    determined_at: datetime
    signature: str               # Ed25519 signature by OrbitCover oracle key
    prev_hash: str               # hash of previous determination — hash chain
```

The `data_snapshot_hash` pins the exact raw DGCA or OpenSky response that produced the determination. Anyone can re-run GAD's open-source computation engine against that exact data snapshot and arrive at the same result. The signature is OrbitCover's attestation. The `prev_hash` makes the log append-only: any tampering is detectable.

This is not blockchain. It is a hash chain — the same structure as Git commits or certificate transparency logs. Simple, auditable, no token required.

GAD needs an `oracle_log` module. Every determination appended. The log public. This is the audit trail that reinsurers accept and regulators certify.

**Gap size:** Large  
**Deferrable:** Ed25519 signing can ship v0.2. The data structure — including `data_snapshot_hash`, `computation_version`, and `prev_hash` fields — must be present in v0.1, even as unsigned placeholders, because the schema cannot change after real policy determinations are written to it.

---

## Gap 3: Policy binding is absent

GAD's current model is trigger-centric: define a trigger, score it, back-test it. There are no policies in the data model.

The oracle standard requires trigger determinations to be bound to specific policies at issuance time.

**Required flow:**

```
Policy issued
  → policy_id + trigger_def_id written to oracle registry
  → oracle begins monitoring trigger_def for that policy_id
  → trigger fires
  → TriggerDetermination(policy_id=..., fired=True) signed and logged
  → settlement system consumes TriggerDetermination
  → UPI payout executes
```

**Required extension to the trigger YAML schema:**

```yaml
# Current GAD trigger definition
trigger_id: "flight-delay-indigo-60min"
peril: flight_delay
threshold: 60
data_source: dgca_api
geography:
  type: point
  lat: 12.9716
  lon: 77.5946

# Oracle extension needed
policy_binding:
  policy_id: "uuid-here"
  coverage_start: "2026-04-01T00:00:00Z"
  coverage_endInclusive: "2026-04-01T23:59:59Z"
  flight_id: "6E-203"
  payout_inr: 500
  settlement_upi: "user@upi"
```

Without policy binding, GAD is a research tool. With it, GAD is the front end of a settlement system.

Note the `coverage_endInclusive` naming — not `coverage_end`, which is ambiguous about whether the boundary is included.

**Gap size:** Large  
**Deferrable:** Live policy monitoring defers to v0.2. The `policy_binding` block in the YAML schema must ship in v0.1.

---

## Gap 4: Lloyd's alignment scoring is boolean, not treaty-ready

The current design has Lloyd's scoring as a checklist: pass/fail per criterion, fraction passing equals the score. Correct for v1 as a developer signal. Insufficient as a reinsurance treaty document.

Lloyd's coverholder agreements do not accept "7/10 Lloyd's score." They require specific documented outputs.

**What the Lloyd's scoring module must produce:**

**1. Basis risk quantification**
- Spearman rho with 95% CI (GAD has this)
- False positive rate: trigger fires, no loss (GAD has this in confusion matrix)
- False negative rate: loss occurs, trigger does not fire (GAD has this)

**2. Data source provenance** (not currently in design)
- Named primary source with URL and version
- Named fallback source
- Data latency: how stale can data be before the trigger determination is invalid?
- Historical availability: years of back-test possible

**3. Trigger definition precision** (partially present)
- Unambiguous threshold with no adjudication required
- Single authoritative data source per determination
- Documented edge cases: what if the data source is unavailable?

**4. Independent verifiability** (not currently in design)
- Can a third party re-run the computation and arrive at the same result?
- Answer must be: YES, using GAD open-source engine and the logged `data_snapshot_hash`
- This is the point that makes GAD the oracle standard — no other tool in the market can make this claim

Points 1 and 3 are partially in the current design. Points 2 and 4 are absent. Point 4 specifically is what distinguishes GAD from every proprietary basis risk tool at Willis Re, Aon, and incumbents.

**Gap size:** Medium  
**Deferrable:** Full treaty-ready output defers to v0.2. Data source provenance fields must be in the trigger schema at v0.1.

---

## Gap 5: Data pipeline is pull-only

**Current design:** Automated ingestion from ERA5, CHIRPS, NOAA. Batch. Historical. Explicitly deferred to Phase 2.

**Oracle requirement:** A listener that polls DGCA or OpenSky every 60 seconds, evaluates trigger conditions, and emits events immediately when a threshold is crossed. The real-time pipeline is not a Phase 2 deferral — it is the oracle. Flight delay parametric cannot function on a batch pipeline.

**Required architecture:**

```
Data Sources                    GAD Oracle Runtime
─────────────────               ─────────────────────────────────
OpenSky API  ── poll 60s ──────→ TriggerMonitor
DGCA API     ── poll 60s ──────→     |
METAR feed   ── subscribe ─────→     v
                                TriggerEvaluator (uses GAD engine)
                                     |
                                TriggerDetermination (signed)
                                     |
                                OracleLog (append-only, public)
                                     |
                                Webhook ──→ OrbitCover settlement
                                        ──→ Reinsurer reporting
                                        ──→ Public audit endpoint
```

**Gap size:** Medium  
**Deferrable:** Real-time polling loop defers to v0.2. The webhook interface schema and the `OracleLog` append contract must be defined in v0.1. **Defined in:** [ORACLE_WEBHOOK_AND_LOG.md](ORACLE_WEBHOOK_AND_LOG.md).

---

## Gap 6: License is undecided

This is a strategic decision, not a housekeeping one.

**Apache 2.0** allows silent proprietary forks. A well-resourced competitor (ACKO, Cover Genius) can fork GAD, make proprietary improvements, run a competing oracle, and contribute nothing back.

**AGPL** forces anyone who runs a modified GAD oracle to open-source their modifications. The specification being MIT means anyone can build tools that read and write GAD trigger definitions. The engine being AGPL means anyone running the oracle has to contribute improvements back.

**Recommendation: AGPL for the computation engine. MIT for the trigger schema specification.**

The MIT schema creates an open ecosystem. The AGPL engine creates the copyleft moat. This is the structure that lets the standard proliferate while preventing the trusted-operator position from being commoditized.

**Gap size:** Small — but it must be decided before the first public commit. Changing a license after community contribution is legally messy.

---

## Gap 7: Oracle signing key management

The self-critique from the previous analysis identified this as unresolved. Here is the full architecture.

### The threat model

OrbitCover's oracle signing key is the root of trust for every parametric trigger determination. If it is compromised, an attacker can forge trigger determinations — fabricate payouts or suppress legitimate ones. The key management architecture must treat this key as equivalent to a certificate authority root key.

### Key architecture

Use a three-tier key hierarchy:

```
Tier 1: Root Key (offline, air-gapped)
  Purpose: signs Tier 2 keys only, never signs trigger determinations
  Storage: HSM (Hardware Security Module), never network-connected
  Rotation: annually, or on compromise
  Holders: two OrbitCover directors, threshold signature (2-of-3 scheme)

Tier 2: Intermediate Key (online, HSM-backed)
  Purpose: signs Tier 3 operational keys
  Storage: Cloud HSM (AWS CloudHSM or GCP Cloud HSM)
  Rotation: every 6 months
  Revocation: publishable by Root Key

Tier 3: Operational Key (online, rotated frequently)
  Purpose: signs individual TriggerDetermination objects
  Storage: HSM-backed secrets manager (AWS Secrets Manager with HSM backing)
  Rotation: every 30 days, or on any suspected compromise
  Revocation: publishable by Intermediate Key
```

The algorithm at every tier is Ed25519. Reasons: small key size (32 bytes), fast verification, no parameter choices that can be misconfigured (unlike ECDSA with arbitrary curves), and wide library support in Python (`cryptography`, `PyNaCl`).

### Key lifecycle operations

**Key generation (Tier 3 operational, monthly rotation):**

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

def generate_operational_key() -> tuple[bytes, bytes]:
    """
    Returns (private_key_bytes, public_key_bytes).
    Private key bytes go to HSM. Public key bytes go to public key registry.
    DANGEROUS DANGEROUS DANGEROUS IF YOU CHANGE THIS THEN THE KEY FORMAT CHANGES
    AND ALL EXISTING SIGNATURES BECOME UNVERIFIABLE AGAINST NEW KEYS
    """
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes
```

**Signing a TriggerDetermination:**

```python
import hashlib
import json
from uuid import UUID
from datetime import datetime, timezone

def sign_determination(
    determination: TriggerDetermination,
    private_key_bytes: bytes,
    prev_determination_hash: str
) -> TriggerDetermination:
    """
    Produces a signed, hash-chained TriggerDetermination.
    The signing payload is the canonical JSON of the determination
    minus the signature field itself.
    """
    payload = {
        "determination_id": str(determination.determination_id),
        "policy_id": str(determination.policy_id),
        "trigger_id": str(determination.trigger_id),
        "fired": determination.fired,
        "fired_at": determination.fired_at.isoformat(),
        "data_snapshot_hash": determination.data_snapshot_hash,
        "computation_version": determination.computation_version,
        "determined_at": determination.determined_at.isoformat(),
        "prev_hash": prev_determination_hash,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    signature = private_key.sign(payload_bytes).hex()

    return TriggerDetermination(
        **{k: v for k, v in vars(determination).items()},
        signature=signature,
        prev_hash=prev_determination_hash,
    )
```

**Independent verification (the function anyone in the world can run):**

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def verify_determination(
    determination: TriggerDetermination,
    public_key_bytes: bytes,  # fetched from OrbitCover public key registry
) -> bool:
    payload = {
        "determination_id": str(determination.determination_id),
        "policy_id": str(determination.policy_id),
        "trigger_id": str(determination.trigger_id),
        "fired": determination.fired,
        "fired_at": determination.fired_at.isoformat(),
        "data_snapshot_hash": determination.data_snapshot_hash,
        "computation_version": determination.computation_version,
        "determined_at": determination.determined_at.isoformat(),
        "prev_hash": determination.prev_hash,
    }
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(bytes.fromhex(determination.signature), payload_bytes)
        return True
    except InvalidSignature:
        return False
```

### Public key registry

Every operational key ever used by OrbitCover's oracle must be permanently published, with its validity window, at a canonical URL:

```
https://oracle.parametricdata.io/.well-known/oracle-keys.json
```

Structure:

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

Any third party verifying a historical determination fetches this registry, finds the key valid at `determined_at`, and runs `verify_determination`. The entire verification chain is self-contained and requires no trust in OrbitCover beyond the initial key registry fetch.

This registry is also what reinsurers and regulators point to when auditing claims. The Lloyd's coverholder agreement should reference this URL explicitly as the authoritative key registry.

### Compromise response

If a Tier 3 operational key is suspected compromised:

1. Intermediate key publishes a revocation record to the key registry (sets `revoked: true`, adds `revoked_at` timestamp)
2. A new Tier 3 key is generated and published
3. All determinations signed by the revoked key after the suspected compromise timestamp are flagged for manual review
4. Determinations signed before the compromise timestamp remain valid — the hash chain provides the tamper-evidence needed to establish which determinations predate the compromise

The hash chain is the reason the compromise window is bounded. An attacker who steals the operational key cannot retroactively insert forged determinations into the middle of the log without breaking every `prev_hash` from that point forward. The forgery is detectable.

---

## Gap summary

| Dimension | Current GAD | Oracle standard | Gap size | Must be in v0.1 |
|-----------|-------------|-----------------|----------|-----------------|
| Analysis mode | Batch, historical | Real-time, live | Large | TriggerEvent schema |
| Trigger binding | Abstract trigger defs | Policy-bound monitoring | Large | policy_binding YAML block |
| Output artifact | BasisRiskReport | TriggerDetermination (signed) | Large | Data structure with hash fields |
| Cryptographic integrity | None | Hash-chained signed log | Large | Field definitions (signing in v0.2) |
| Data pipeline | Pull, batch | Push/poll, real-time | Medium | Webhook interface schema |
| Lloyd's output | Checklist score | Treaty-ready documentation | Medium | data_source_provenance fields |
| Policy lifecycle | Not modeled | Issuance to settlement | Large | policy_binding |
| License | Undecided | AGPL engine, MIT schema | Small | Decide before first public commit |
| Key management | None | Three-tier HSM hierarchy | Large | Key registry URL + format |

Five of nine dimensions are large gaps. None invalidate the current design. The basis risk engine, trigger registry, Lloyd's checklist, and dashboard are all correct and necessary. The oracle standard is built on top of them, not instead of them.

---

## v0.1 must-have checklist

These decisions, if deferred, create breaking changes later:

- [x] `TriggerEvent` and `TriggerDetermination` data structures defined with `data_snapshot_hash`, `computation_version`, `prev_hash`, and `signature` fields (even if `signature` is an empty string placeholder in v0.1)
- [x] `policy_binding` block added to trigger YAML schema (even if the monitoring loop is a TODO stub)
- [x] `data_source_provenance` fields added to trigger YAML schema
- [x] AGPL for computation engine, MIT for schema — committed and in LICENSE files before first public push
- [x] Public key registry URL (`oracle.parametricdata.io/.well-known/oracle-keys.json`) reserved and format documented, even if unpopulated
- [x] Webhook interface schema and OracleLog append contract defined (payload, idempotency, retries; append-only log, one record per determination, hash chain) — see [ORACLE_WEBHOOK_AND_LOG.md](ORACLE_WEBHOOK_AND_LOG.md)

---

## v0.2 target deliverables

- Ed25519 signing live on all TriggerDetermination objects
- Operational key (Tier 3) generated and published to key registry
- Real-time polling loop for DGCA and OpenSky
- Append-only OracleLog with hash-chain verification
- Webhook output to OrbitCover settlement system
- `verify_determination()` published as a standalone open-source utility

---

## v0.3 target deliverables (oracle standard threshold)

- Three-tier key hierarchy with HSM-backed Intermediate Key
- Public key registry with revocation support
- Lloyd's treaty-ready documentation output from scoring module
- Parametric Trigger Master Agreement draft referencing oracle.parametricdata.io key registry
- Independent verification guide published for reinsurer audit teams

---

## The institutional trust sequence

GAD earns technical credibility through open-source transparency.  
The certified oracle service earns institutional trust through the signed log.  
The reinsurer co-governed consortium earns governance legitimacy by co-owning the standard.

All three are necessary. GAD alone produces a useful tool. GAD plus this architecture produces a standard.

The single highest-leverage action right now: ship v0.1 with the data structures correct. Every trigger determination since the first IndiGo live policy will then be retrospectively verifiable when the signing layer ships in v0.2. That audit trail — covering months of live production data — is worth more than any claim about trustworthiness made at a Lloyd's Lab presentation.

---

*This document should be reviewed and updated to the DESIGN.md file at each version milestone. The key registry URL and signing architecture sections should be treated as security-sensitive — changes require sign-off from Nitthin*
