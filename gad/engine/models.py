"""
Engine data models (spec-aligned). Pydantic v2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DataSourceProvenance(BaseModel):
    """Required for Lloyd's treaty documentation."""

    primary_source: str = Field(..., description="e.g. DGCA API v2.1")
    primary_url: str = Field(..., description="Canonical URL")
    fallback_source: Optional[str] = None
    max_data_latency_seconds: int = Field(
        ...,
        description="How stale before determination is invalid",
    )
    historical_years_available: int = Field(
        ...,
        description="Years of back-test possible",
    )


class PolicyBinding(BaseModel):
    """Binds a trigger definition to a specific policy instance."""

    policy_id: UUID
    coverage_start: datetime
    coverage_end_inclusive: datetime = Field(
        ...,
        description="Never coverage_end — always explicit",
    )
    flight_id: Optional[str] = None
    payout_inr: Optional[float] = None
    settlement_upi: Optional[str] = None


class TriggerDef(BaseModel):
    """Parametric trigger definition (spec shape)."""

    trigger_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = Field(
        default="",
        description="Plain English — shown in guided mode",
    )
    peril: Literal["flight_delay", "drought", "flood", "earthquake", "wind", "extreme_weather", "air_quality", "wildfire", "marine", "cyclone", "crop", "solar", "health"]
    threshold: float
    threshold_unit: str = Field(..., description="e.g. minutes, mm_rainfall, knots")
    data_source: str
    geography: dict = Field(..., description="GeoJSON point (v0.1 point-only)")
    provenance: DataSourceProvenance
    policy_binding: Optional[PolicyBinding] = None
    trigger_fires_when_above: bool = Field(
        default=True,
        description="If True, fire when trigger_value >= threshold; if False, when <= threshold (e.g. drought).",
    )
    created_by: Optional[UUID] = Field(default=None, description="user_id from Supabase auth")
    is_public: bool = Field(default=False, description="Private by default")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TriggerDetermination(BaseModel):
    """
    Every determination is a signed, hash-chained artifact.
    prev_hash makes the log append-only — any field change affects future hashes.
    New optional fields (like key_id) are safe because they serialize as null
    and don't break the chain for existing entries.
    """

    determination_id: UUID = Field(default_factory=uuid4)
    policy_id: UUID
    trigger_id: UUID
    fired: bool
    fired_at: Optional[datetime] = None
    data_snapshot_hash: str = Field(
        ...,
        description="SHA-256 of raw API response bytes",
    )
    computation_version: str = Field(
        ...,
        description="GAD git commit hash at determination time",
    )
    determined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: str = Field(..., description="SHA-256 of previous determination JSON")
    signature: str = Field(
        default="",
        description="Ed25519 hex signature — empty string in v0.1",
    )
    key_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the signing key from the key registry. None in v0.1 (unsigned).",
    )
    model_version_id: Optional[UUID] = Field(
        default=None,
        description="Links determination to calibration state",
    )


class BacktestRow(BaseModel):
    """One period in the back-test (for UI timeline/scatter)."""

    period: str
    trigger_value: float
    trigger_fired: bool
    loss_occurred: bool


class BasisRiskReport(BaseModel):
    """Spec-aligned basis risk output."""

    report_id: UUID = Field(default_factory=uuid4)
    trigger_id: UUID
    spearman_rho: float
    spearman_ci_lower: float = Field(..., description="95% confidence interval")
    spearman_ci_upper: float
    p_value: float
    false_positive_rate: float = Field(..., description="Trigger fires, no loss")
    false_negative_rate: float = Field(..., description="Loss occurs, trigger does not fire")
    backtest_periods: int
    backtest_start: datetime
    backtest_end_inclusive: datetime
    lloyds_score: float = Field(..., description="Fraction of criteria passing (0.0-1.0)")
    lloyds_detail: dict = Field(..., description="Per-criterion pass/fail")
    independent_verifiable: bool = Field(
        ...,
        description="True only if data_snapshot_hash is present",
    )
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    backtest_rows: Optional[list[BacktestRow]] = Field(
        default=None,
        description="Period-level rows for UI (timeline, scatter); set by compute_basis_risk.",
    )
    gad_version: str = Field(
        ...,
        description="GAD git commit hash or package version at computation time — required for independent verifiability",
    )


class ModelVersion(BaseModel):
    """Append-only audit trail for learning layer model state."""

    version_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_id: Optional[str] = None  # None = global model
    model_type: str = ""  # e.g. "distribution_90d", "threshold_optimizer", "peer_index"
    parameters: Optional[str] = None  # JSON string of model parameters
    metrics: Optional[str] = None  # JSON string of model metrics/scores


class TriggerObservation(BaseModel):
    """Atomic unit of the learning layer. One observation per trigger per fetch cycle."""

    trigger_id: str
    observed_at: datetime
    value: Optional[float] = None
    fired: bool = False
    data_source: str = ""
    raw_json: Optional[str] = None


class GadEvent(BaseModel):
    """Activity event — written to Supabase on every meaningful user action."""

    event_id: UUID = Field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    session_id: str = Field(..., description="Anonymous session token")
    event_type: str = Field(..., description="See EVENT TYPES in analytics")
    trigger_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
