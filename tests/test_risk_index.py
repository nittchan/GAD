"""
Tests for the Parametric Risk Exposure Index (PREI) computation.
"""

from __future__ import annotations

import pytest

from gad.monitor.risk_index import compute_prei, _trigger_country
from gad.monitor.triggers import MonitorTrigger


def _make_trigger(
    id: str,
    threshold: float = 42,
    fires_when_above: bool = True,
) -> MonitorTrigger:
    return MonitorTrigger(
        id=id,
        name="Test",
        peril="extreme_weather",
        lat=0.0,
        lon=0.0,
        location_label="Test",
        threshold=threshold,
        threshold_unit="celsius",
        fires_when_above=fires_when_above,
        data_source="openmeteo",
        description="Test trigger",
    )


class TestComputePreiBasic:
    """Test PREI formula with mock trigger_results for India."""

    def test_three_triggers_one_fired_one_normal_one_nodata(self):
        """
        3 triggers for India (via DEL, BLR, BOM IATA codes):
        - 1 fired (critical)
        - 1 normal (not near threshold)
        - 1 no_data
        PREI = (1/3)*100 + (0/3)*30 = 33.3
        """
        t1 = _make_trigger("weather-heat-del", threshold=42)
        t2 = _make_trigger("weather-heat-blr", threshold=42)
        t3 = _make_trigger("weather-heat-bom", threshold=42)

        trigger_results = {
            "weather-heat-del": (t1, {}, {"status": "critical", "value": 45}, False),
            "weather-heat-blr": (t2, {}, {"status": "normal", "value": 20}, False),
            "weather-heat-bom": (t3, {}, {"status": "no_data"}, False),
        }

        result = compute_prei(trigger_results)

        assert "India" in result
        india = result["India"]
        assert india["total"] == 3
        assert india["fired"] == 1
        assert india["normal"] == 1
        assert india["no_data"] == 1
        assert india["near_threshold"] == 0
        # PREI = (1/3)*100 + (0/3)*30 = 33.3
        assert india["prei"] == pytest.approx(33.3, abs=0.1)

    def test_all_fired(self):
        """All triggers fired: PREI = (3/3)*100 = 100."""
        t1 = _make_trigger("weather-heat-del", threshold=42)
        t2 = _make_trigger("weather-heat-blr", threshold=42)
        t3 = _make_trigger("weather-heat-bom", threshold=42)

        trigger_results = {
            "weather-heat-del": (t1, {}, {"status": "critical", "value": 50}, False),
            "weather-heat-blr": (t2, {}, {"status": "critical", "value": 48}, False),
            "weather-heat-bom": (t3, {}, {"status": "critical", "value": 45}, False),
        }

        result = compute_prei(trigger_results)
        assert result["India"]["prei"] == 100

    def test_none_fired_none_near(self):
        """No triggers fired, none near: PREI = 0."""
        t1 = _make_trigger("weather-heat-del", threshold=42)

        trigger_results = {
            "weather-heat-del": (t1, {}, {"status": "normal", "value": 20}, False),
        }

        result = compute_prei(trigger_results)
        assert result["India"]["prei"] == 0


class TestComputePreiEmptyInput:
    def test_empty_input_returns_empty_dict(self):
        result = compute_prei({})
        assert result == {}


class TestComputePreiStandalone:
    """Standalone triggers (no country mapping) are gracefully skipped."""

    def test_standalone_trigger_not_mapped(self):
        """Triggers like 'fire-california' don't map to a country via IATA."""
        t = _make_trigger("fire-california", threshold=10)

        trigger_results = {
            "fire-california": (t, {}, {"status": "critical", "value": 15}, False),
        }

        result = compute_prei(trigger_results)
        # 'california' is not an IATA code, so _trigger_country returns None
        assert len(result) == 0

    def test_earthquake_standalone_not_mapped(self):
        t = _make_trigger("quake-japan", threshold=5.0)

        trigger_results = {
            "quake-japan": (t, {}, {"status": "critical", "value": 6.5}, False),
        }

        result = compute_prei(trigger_results)
        # 'japan' is not an IATA code
        assert len(result) == 0


class TestNearThresholdDetection:
    """Value at 80% of threshold should be counted as near_threshold."""

    def test_near_threshold_fires_when_above(self):
        """
        Trigger fires when above 42C. Value at 80% of 42 = 33.6.
        Value of 35 is 35/42 = 0.833... >= 0.8 => near_threshold.
        """
        t = _make_trigger("weather-heat-del", threshold=42, fires_when_above=True)

        trigger_results = {
            "weather-heat-del": (t, {}, {"status": "normal", "value": 35}, False),
        }

        result = compute_prei(trigger_results)
        india = result["India"]
        assert india["near_threshold"] == 1
        assert india["normal"] == 0
        # PREI = (0/1)*100 + (1/1)*30 = 30
        assert india["prei"] == 30

    def test_not_near_threshold(self):
        """
        Value of 20 is 20/42 = 0.476... < 0.8 => normal, not near.
        """
        t = _make_trigger("weather-heat-del", threshold=42, fires_when_above=True)

        trigger_results = {
            "weather-heat-del": (t, {}, {"status": "normal", "value": 20}, False),
        }

        result = compute_prei(trigger_results)
        india = result["India"]
        assert india["near_threshold"] == 0
        assert india["normal"] == 1
        assert india["prei"] == 0

    def test_near_threshold_fires_when_below(self):
        """
        Trigger fires when below threshold (e.g. drought, threshold=50mm).
        Value=55, proximity = threshold/value = 50/55 = 0.909 >= 0.8 => near.
        """
        t = _make_trigger("drought-india-del", threshold=50, fires_when_above=False)

        trigger_results = {
            "drought-india-del": (t, {}, {"status": "normal", "value": 55}, False),
        }

        result = compute_prei(trigger_results)
        india = result["India"]
        assert india["near_threshold"] == 1

    def test_exactly_at_80_percent(self):
        """
        Value at exactly 80% of threshold. 42 * 0.8 = 33.6.
        33.6/42 = 0.8 >= 0.8 => near_threshold.
        """
        t = _make_trigger("weather-heat-del", threshold=42, fires_when_above=True)

        trigger_results = {
            "weather-heat-del": (t, {}, {"status": "normal", "value": 33.6}, False),
        }

        result = compute_prei(trigger_results)
        india = result["India"]
        assert india["near_threshold"] == 1

    def test_null_value_treated_as_normal(self):
        """If value is None, it should be counted as normal (not near)."""
        t = _make_trigger("weather-heat-del", threshold=42, fires_when_above=True)

        trigger_results = {
            "weather-heat-del": (t, {}, {"status": "normal", "value": None}, False),
        }

        result = compute_prei(trigger_results)
        india = result["India"]
        assert india["near_threshold"] == 0
        assert india["normal"] == 1


class TestTriggerCountry:
    """Test the _trigger_country helper."""

    def test_indian_airport(self):
        assert _trigger_country("flight-delay-del") == "India"

    def test_us_airport(self):
        assert _trigger_country("flight-delay-jfk") == "USA"

    def test_aqi_trigger(self):
        assert _trigger_country("aqi-blr") == "India"

    def test_weather_trigger(self):
        assert _trigger_country("weather-heat-lax") == "USA"

    def test_standalone_returns_none(self):
        assert _trigger_country("fire-california") is None

    def test_earthquake_standalone_returns_none(self):
        assert _trigger_country("quake-japan") is None


class TestPreiScoreCapping:
    """PREI should be capped at 100."""

    def test_prei_capped_at_100(self):
        """
        If PREI formula yields > 100, it should be capped at 100.
        Example: all fired + all near threshold (impossible in practice
        since a trigger can't be both, but test the cap).
        """
        # 2 fired out of 2 = 100 from fired alone
        t1 = _make_trigger("weather-heat-del", threshold=42)
        t2 = _make_trigger("weather-heat-blr", threshold=42)

        trigger_results = {
            "weather-heat-del": (t1, {}, {"status": "critical", "value": 50}, False),
            "weather-heat-blr": (t2, {}, {"status": "critical", "value": 48}, False),
        }

        result = compute_prei(trigger_results)
        assert result["India"]["prei"] <= 100
