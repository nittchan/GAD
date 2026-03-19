from __future__ import annotations

from datetime import date
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
