"""
Oracle / settlement data structures (v0.1 schema only).
Real-time monitoring and Ed25519 signing ship in v0.2; these models define
the stable schema so the log is retrospectively verifiable.
See docs/GAP_ANALYSIS_ORACLE.md and, in v0.2, sign_determination() / verify_determination().
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ObservationPayload(BaseModel):
    """Minimal payload for a real-time observation (source, value, timestamp)."""

    source: str = Field(..., description="Data source identifier, e.g. dgca_api, opensky")
    value: float = Field(..., description="Observed value used for trigger evaluation")
    timestamp: datetime = Field(..., description="When the observation was recorded")


class TriggerEvent(BaseModel):
    """
    Real-time detection output when a trigger condition is evaluated against a live observation.
    Not yet produced by GAD's batch engine; required for the oracle event loop in v0.2.
    """

    event_id: UUID = Field(..., description="Unique event identifier")
    policy_id: UUID = Field(..., description="Policy this evaluation is bound to")
    trigger_id: str = Field(..., description="Trigger definition id")
    fired: bool = Field(..., description="Whether the trigger condition was met")
    fired_at: datetime = Field(..., description="When the condition was evaluated / observation timestamp")
    observation: ObservationPayload | None = Field(
        default=None,
        description="Raw observation that drove the evaluation",
    )
    condition_met: bool = Field(
        default=True,
        description="Explicit flag for condition outcome; aligned with fired for clarity",
    )


class TriggerDetermination(BaseModel):
    """
    Signed settlement artifact: one irrefutable record that a trigger did or did not fire
    for a specific policy at a specific time. v0.1: schema only; signature may be empty.
    v0.2: Ed25519 signing and prev_hash chain; verify_determination() uses public key registry.
    """

    determination_id: UUID = Field(..., description="Unique determination identifier")
    policy_id: UUID = Field(..., description="Policy this determination is for")
    trigger_id: str = Field(..., description="Trigger definition id (or UUID when standardised)")
    fired: bool = Field(..., description="Whether the trigger fired")
    fired_at: datetime = Field(..., description="When the trigger fired (or evaluation time)")
    data_snapshot_hash: str = Field(
        ...,
        description="SHA-256 hex of raw input data; pins exact DGCA/OpenSky/etc. response",
    )
    computation_version: str = Field(
        ...,
        description="GAD git commit hash (or version tag) used for this computation",
    )
    determined_at: datetime = Field(..., description="When this determination was produced")
    signature: str = Field(
        default="",
        description="Ed25519 signature hex; empty string placeholder in v0.1",
    )
    prev_hash: str = Field(
        ...,
        description="Hash of previous determination in the log (hash chain); genesis uses fixed value",
    )
