from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class PerilType(str, Enum):
    drought = "drought"
    flood = "flood"
    earthquake = "earthquake"


class AggregationPeriod(str, Enum):
    monthly = "monthly"
    daily = "daily"


class TriggerKind(str, Enum):
    threshold_above = "threshold_above"
    threshold_below = "threshold_below"


class LocationPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class BoundingBox(BaseModel):
    """Geographic bounding box for regional triggers (Phase 2)."""

    min_lat: float = Field(..., ge=-90, le=90)
    max_lat: float = Field(..., ge=-90, le=90)
    min_lon: float = Field(..., ge=-180, le=180)
    max_lon: float = Field(..., ge=-180, le=180)

    @model_validator(mode="after")
    def ordered(self) -> BoundingBox:
        if self.min_lat >= self.max_lat or self.min_lon >= self.max_lon:
            raise ValueError("min_* must be strictly less than max_*")
        return self


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def ordered(self) -> DateRange:
        if self.start >= self.end:
            raise ValueError("date_range.start must be before date_range.end")
        return self

    @model_validator(mode="after")
    def reasonable_span(self) -> DateRange:
        y0, y1 = self.start.year, self.end.year
        if y0 < 1980 or y1 > 2100:
            raise ValueError("date_range must fall within 1980-2100")
        if (self.end - self.start).days > 365 * 100:
            raise ValueError("date_range span exceeds 100 years")
        return self


class TriggerLogic(BaseModel):
    kind: TriggerKind
    threshold: float
    aggregation: AggregationPeriod = AggregationPeriod.monthly


class PolicyBinding(BaseModel):
    """
    Oracle extension: bind trigger to a specific policy at issuance.
    Monitoring loop (v0.2) uses this to track policy_id + trigger_def_id.
    """

    policy_id: str = Field(..., description="Policy UUID string")
    coverage_start: datetime = Field(..., description="Coverage start (ISO)")
    coverage_end_inclusive: datetime = Field(
        ...,
        description="Coverage end inclusive (ISO); naming avoids boundary ambiguity",
    )
    flight_id: str | None = Field(default=None, description="Optional flight identifier for flight_delay peril")
    payout_inr: int | None = Field(default=None, description="Optional payout amount in INR")
    settlement_upi: str | None = Field(default=None, description="Optional UPI id for settlement")


class DataSourceProvenance(BaseModel):
    """
    Lloyd's treaty-ready: named primary/fallback source, latency, historical availability.
    """

    primary_source_name: str = Field(..., description="Named primary data source")
    primary_source_url: str | None = Field(default=None, description="URL of primary source")
    primary_source_version: str = Field(..., description="e.g. CHIRPS v2.0")
    fallback_source_name: str | None = Field(default=None)
    fallback_source_url: str | None = Field(default=None)
    max_data_latency_seconds: int | None = Field(
        default=None,
        description="How stale data can be before determination is invalid",
    )
    historical_availability_years: tuple[int, int] | None = Field(
        default=None,
        description="e.g. (1981, 2025) for CHIRPS",
    )


class TriggerDef(BaseModel):
    """Parametric trigger definition (insurance logic only)."""

    id: str = Field(..., min_length=1, pattern=r"^[a-z0-9_]+$")
    name: str
    peril: PerilType
    location: LocationPoint
    variable: str = Field(..., min_length=1, description="Hazard variable name, e.g. rainfall_mm")
    trigger_logic: TriggerLogic
    date_range: DateRange
    payout_formula_summary: str = Field(
        default="Fixed payout when trigger condition is met for the period.",
        min_length=1,
    )
    bounding_box: BoundingBox | None = Field(
        default=None,
        description="Optional region for spatial averaging; when set, data must include lat/lon or be pre-aggregated.",
    )
    policy_binding: PolicyBinding | None = Field(
        default=None,
        description="Oracle extension: bind to specific policy; required for settlement. Monitoring in v0.2.",
    )
    data_source_provenance: DataSourceProvenance | None = Field(
        default=None,
        description="Lloyd's treaty-ready: primary/fallback source, latency, historical availability.",
    )

    @field_validator("id")
    @classmethod
    def id_lowercase(cls, v: str) -> str:
        return v.lower()


class SeriesRef(BaseModel):
    """Maps a trigger to bundled time-series files (Phase 1 flat files)."""

    primary_series_csv: str = Field(..., min_length=1)
    spatial_reference_csv: str | None = Field(
        default=None,
        description="Optional separate CSV for spatial reference; if omitted, primary must include spatial_ref column.",
    )
    loss_proxy_csv: str | None = None


class DataManifest(BaseModel):
    version: Literal["1"] = "1"
    triggers: dict[str, SeriesRef]

    @model_validator(mode="after")
    def keys_match_trigger_ids(self) -> DataManifest:
        for k in self.triggers:
            if not k or not k.replace("_", "").isalnum():
                raise ValueError(f"Invalid manifest trigger key: {k!r}")
        return self


class SpearmanBlock(BaseModel):
    rho: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int


class ConfusionCounts(BaseModel):
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int


class BacktestRow(BaseModel):
    period: str
    index_value: float
    spatial_ref: float
    trigger_fired: bool
    loss_occurred: bool


class BacktestResult(BaseModel):
    rows: list[BacktestRow]
    confusion: ConfusionCounts
    zero_trigger_fires: bool


class LloydCriterionResult(BaseModel):
    criterion_id: str
    name: str
    passed: bool
    explanation: str


class LloydsResult(BaseModel):
    criteria: list[LloydCriterionResult]
    passed_count: int
    total_count: int

    @property
    def score_fraction(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.passed_count / self.total_count


class BasisRiskReport(BaseModel):
    trigger_id: str
    trigger_name: str
    spearman_spatial: SpearmanBlock
    spearman_loss_proxy: SpearmanBlock | None
    headline_rho: float
    headline_ci_low: float
    headline_ci_high: float
    headline_p_value: float
    headline_label: Literal["loss_proxy", "spatial_basis"]
    backtest: BacktestResult
    warnings: list[str]
    lloyds: LloydsResult
