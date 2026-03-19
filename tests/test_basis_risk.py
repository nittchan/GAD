"""compute_basis_risk(trigger, weather_data) and BasisRiskReport shape."""

from datetime import datetime, timezone
from uuid import uuid4

from gad.engine import TriggerDef, compute_basis_risk
from gad.engine.models import BasisRiskReport, DataSourceProvenance


def test_compute_basis_risk_returns_report():
    provenance = DataSourceProvenance(
        primary_source="Test",
        primary_url="https://example.com",
        max_data_latency_seconds=3600,
        historical_years_available=10,
    )
    trigger = TriggerDef(
        trigger_id=uuid4(),
        name="Test trigger",
        peril="flood",
        threshold=100.0,
        threshold_unit="mm",
        data_source="test",
        geography={"type": "Point", "coordinates": [0.0, 0.0]},
        provenance=provenance,
    )
    # >= 10 periods; trigger_value >= 100 fires
    weather_data = [
        {"period": f"2020-{i:02d}", "trigger_value": 80.0 + i * 2.0, "loss_proxy": 0.0 if i % 3 else 0.5}
        for i in range(1, 13)
    ]
    report = compute_basis_risk(trigger, weather_data)
    assert isinstance(report, BasisRiskReport)
    assert report.trigger_id == trigger.trigger_id
    assert report.backtest_periods == 12
    assert 0 <= report.lloyds_score <= 1.0
    assert "spearman_rho" in report.model_dump()
    assert report.backtest_rows is not None
    assert len(report.backtest_rows) == 12


def test_compute_basis_risk_insufficient_data_raises():
    provenance = DataSourceProvenance(
        primary_source="Test",
        primary_url="https://example.com",
        max_data_latency_seconds=3600,
        historical_years_available=10,
    )
    trigger = TriggerDef(
        trigger_id=uuid4(),
        name="Test",
        peril="drought",
        threshold=50.0,
        threshold_unit="mm",
        data_source="test",
        geography={"type": "Point", "coordinates": [0.0, 0.0]},
        provenance=provenance,
    )
    weather_data = [{"period": f"2020-{i:02d}", "trigger_value": 40.0, "loss_proxy": 0.0} for i in range(5)]
    import pytest
    with pytest.raises(ValueError, match="Insufficient data"):
        compute_basis_risk(trigger, weather_data)
