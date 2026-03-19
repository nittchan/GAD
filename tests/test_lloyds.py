"""lloyds_check(trigger, rho, fpr, fnr) score and detail."""

from uuid import uuid4

from gad.engine import lloyds_check
from gad.engine.models import TriggerDef, DataSourceProvenance


def test_lloyds_check_returns_score_and_detail():
    provenance = DataSourceProvenance(
        primary_source="CHIRPS v2.0",
        primary_url="https://example.com",
        max_data_latency_seconds=86400,
        historical_years_available=40,
    )
    trigger = TriggerDef(
        trigger_id=uuid4(),
        name="Kenya drought",
        peril="drought",
        threshold=50.0,
        threshold_unit="mm",
        data_source="CHIRPS",
        geography={"type": "Point", "coordinates": [37.99, 2.33]},
        provenance=provenance,
    )
    result = lloyds_check(trigger, 0.72, 0.15, 0.10)
    assert "score" in result
    assert "detail" in result
    assert 0 <= result["score"] <= 1.0
    assert "acceptable_basis_risk" in result["detail"]
    assert "false_positive_rate_acceptable" in result["detail"]
    assert result["detail"]["acceptable_basis_risk"]["pass"] is True
    assert result["detail"]["false_positive_rate_acceptable"]["pass"] is True


def test_lloyds_check_low_rho_fails_acceptable_basis_risk():
    provenance = DataSourceProvenance(
        primary_source="Test",
        primary_url="https://example.com",
        max_data_latency_seconds=3600,
        historical_years_available=10,
    )
    trigger = TriggerDef(
        trigger_id=uuid4(),
        name="Test",
        peril="flood",
        threshold=100.0,
        threshold_unit="mm",
        data_source="test",
        geography={"type": "Point", "coordinates": [0.0, 0.0]},
        provenance=provenance,
    )
    result = lloyds_check(trigger, 0.3, 0.05, 0.05)
    assert result["detail"]["acceptable_basis_risk"]["pass"] is False
