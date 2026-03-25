"""
Pydantic response models for the Parametric Data API.

These models drive auto-generated OpenAPI schemas in Swagger UI
and provide runtime response validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Optional


class TriggerSummary(BaseModel):
    """Summary of a single trigger as returned in list endpoints."""

    id: str = Field(..., description="Trigger identifier, e.g. 'flight-delay-del'")
    name: str = Field(..., description="Human-readable trigger name")
    peril: str = Field(..., description="Peril category key, e.g. 'earthquake'")
    lat: float = Field(..., description="Latitude of the trigger location")
    lon: float = Field(..., description="Longitude of the trigger location")
    location_label: str = Field(..., description="Human-readable location, e.g. 'Delhi (DEL), India'")
    threshold: float = Field(..., description="Trigger threshold value")
    threshold_unit: str = Field(..., description="Unit of the threshold, e.g. 'magnitude', '% delayed'")
    data_source: str = Field(..., description="Primary data source key, e.g. 'usgs', 'opensky'")
    has_data: bool = Field(..., description="Whether cached data is currently available")
    is_stale: bool = Field(..., description="Whether the cached data is stale (older than expected)")


class TriggerListResponse(BaseModel):
    """Response for GET /v1/triggers."""

    triggers: list[TriggerSummary] = Field(..., description="List of trigger summaries")
    count: int = Field(..., description="Total number of triggers returned")


class TriggerDetailResponse(BaseModel):
    """Response for GET /v1/triggers/{trigger_id} — full trigger profile."""

    id: str
    name: str
    peril: str
    peril_label: str = Field(..., description="Human-readable peril name, e.g. 'Flight Delay'")
    lat: float
    lon: float
    location_label: str
    threshold: float
    threshold_unit: str
    fires_when_above: bool = Field(..., description="True if the trigger fires when value exceeds threshold")
    data_source: str
    description: str = Field(..., description="Plain-English description of the trigger")
    cached_data: Optional[Any] = Field(None, description="Most recent cached observation, or null")
    is_stale: bool


class BasisRiskResponse(BaseModel):
    """Response for GET /v1/triggers/{trigger_id}/basis-risk."""

    trigger_id: str
    report: dict[str, Any] = Field(..., description="Full basis risk report (Spearman rho, CI, FPR/FNR, Lloyd's score)")


class DeterminationEntry(BaseModel):
    """A single oracle determination."""

    trigger_id: Optional[str] = None
    fired: Optional[bool] = None
    timestamp: Optional[str] = None
    data_snapshot_hash: Optional[str] = None
    signature: Optional[str] = None

    model_config = {"extra": "allow"}


class DeterminationsResponse(BaseModel):
    """Response for GET /v1/triggers/{trigger_id}/determinations."""

    trigger_id: str
    determinations: list[dict[str, Any]] = Field(default_factory=list, description="Recent signed determinations")
    count: int


class PerilStatus(BaseModel):
    """Health status for a single peril category."""

    label: str = Field(..., description="Human-readable peril name")
    total: int = Field(..., description="Total trigger count for this peril")
    cached: int = Field(..., description="Number of triggers with fresh cached data")
    stale: int = Field(..., description="Number of triggers with stale data")
    no_data: int = Field(..., description="Number of triggers with no data")
    coverage_pct: int = Field(..., description="Percentage of triggers with fresh data (0-100)")


class StatusResponse(BaseModel):
    """Response for GET /v1/status."""

    perils: dict[str, PerilStatus] = Field(..., description="Per-peril health status")
    total_triggers: int = Field(..., description="Total triggers across all perils")


class PortSummary(BaseModel):
    """Summary of a monitored marine port."""

    id: str
    name: str
    city: str
    country: str
    lat: float
    lon: float
    un_locode: str = Field(..., description="UN/LOCODE identifier, e.g. 'SGSIN'")
    tier: str = Field(..., description="Port tier: 'tier1' or 'tier2'")


class PortListResponse(BaseModel):
    """Response for GET /v1/ports."""

    ports: list[PortSummary]
    count: int


class PerilListResponse(BaseModel):
    """Response for GET /v1/perils."""

    perils: dict[str, str] = Field(..., description="Map of peril key to display label")
    count: int


class ModelVersionEntry(BaseModel):
    """A single model version record."""

    model_config = {"extra": "allow"}


class ModelHistoryResponse(BaseModel):
    """Response for GET /v1/triggers/{trigger_id}/model-history."""

    trigger_id: str
    versions: list[dict[str, Any]] = Field(default_factory=list)
    count: int
    error: Optional[str] = None


# ── Intelligence models (SL-08a-d) ──

class PerilPatternEntry(BaseModel):
    """Firing pattern stats for a single peril."""

    label: str = Field(..., description="Human-readable peril name")
    total: int = Field(..., description="Total trigger count")
    fired: int = Field(..., description="Currently triggered (value past threshold)")
    normal: int = Field(..., description="Fresh data, within threshold")
    stale: int = Field(..., description="Stale cached data")
    no_data: int = Field(..., description="No cached data at all")
    firing_rate: float = Field(..., description="Fraction of evaluable triggers currently fired (0.0–1.0)")


class PerilPatternsResponse(BaseModel):
    """Response for GET /v1/intelligence/peril-patterns."""

    patterns: dict[str, PerilPatternEntry] = Field(..., description="Per-peril firing pattern stats")
    total_triggers: int


class LocationTriggerEntry(BaseModel):
    """A trigger returned from a location-based query."""

    id: str
    name: str
    peril: str
    peril_label: str
    lat: float
    lon: float
    location_label: str
    distance_km: float = Field(..., description="Distance from search centre in km")
    threshold: float
    threshold_unit: str
    data_source: str
    has_data: bool
    is_stale: bool


class LocationIntelligenceResponse(BaseModel):
    """Response for GET /v1/intelligence/location/{lat}/{lon}."""

    lat: float
    lon: float
    radius_km: float
    triggers: list[LocationTriggerEntry]
    count: int


class ClimateZoneResponse(BaseModel):
    """Response for GET /v1/intelligence/climate-zone/{zone}."""

    zone: str
    message: str
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


# ── Model drift (SL-09d) ──

class ModelDriftResponse(BaseModel):
    """Response for GET /v1/triggers/{trigger_id}/model-drift."""

    trigger_id: str
    drift_detected: bool = Field(..., description="True if accuracy dropped >5pp from baseline")
    current_accuracy: Optional[float] = Field(None, description="Latest model accuracy")
    baseline_accuracy: Optional[float] = Field(None, description="First model accuracy (baseline)")
    message: str = Field(..., description="Human-readable drift status")


# ── Data source freshness (FRESH-01a) ──

class SourceHealth(BaseModel):
    """Health status for a single data source."""

    source: str = Field(..., description="Source prefix key, e.g. 'flights'")
    name: str = Field(..., description="Human-readable source name")
    last_fetch: Optional[str] = Field(None, description="ISO-8601 timestamp of most recent cache write")
    age_seconds: Optional[float] = Field(None, description="Seconds since last_fetch")
    file_count: int = Field(0, description="Total cache files for this source")
    fresh_count: int = Field(0, description="Files where expires_at > now")
    stale_count: int = Field(0, description="Files where expires_at <= now")
    freshness: str = Field("red", description="Traffic-light status: green (>80%), amber (>50%), red")


class HealthResponse(BaseModel):
    """Response for GET /v1/health."""

    sources: list[SourceHealth] = Field(..., description="Per-source data freshness")
    total_files: int = Field(..., description="Total cache files across all sources")
    overall_freshness: str = Field(..., description="Overall traffic-light status")


# ── Product composer (CEO-10) ──

class CompositeProductRequest(BaseModel):
    """Request body for POST /v1/products/evaluate."""

    triggers: list[str] = Field(..., min_length=2, max_length=3, description="List of 2-3 trigger IDs to combine")
    logic: str = Field("AND", description="Composite logic: 'AND' (all must fire) or 'OR' (any fires)")
    name: str = Field("Composite Product", description="Optional product name")


class TriggerEvaluationEntry(BaseModel):
    """Evaluation result for a single trigger within a composite product."""

    trigger_id: str
    trigger_name: str
    peril: str
    peril_label: str
    location: str
    fired: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    unit: str = ""
    status: str
    has_data: bool


class CompositeEvaluationResponse(BaseModel):
    """Response for POST /v1/products/evaluate."""

    product_name: str = Field(..., description="Name of the composite product")
    logic: str = Field(..., description="Composite logic applied: 'AND' or 'OR'")
    fired: bool = Field(..., description="Whether the composite product has fired")
    trigger_count: int = Field(..., description="Number of component triggers")
    triggers_fired: int = Field(..., description="Number of component triggers currently fired")
    perils_covered: list[str] = Field(..., description="Distinct peril categories in this product")
    trigger_details: list[TriggerEvaluationEntry] = Field(..., description="Per-trigger evaluation results")
