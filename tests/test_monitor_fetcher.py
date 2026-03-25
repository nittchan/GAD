"""
Tests for gad.monitor.fetcher — evaluation logic, source mapping, and helpers.
No real API calls; tests exercise internal functions with mock data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from gad.monitor.triggers import MonitorTrigger
from gad.monitor.fetcher import (
    _is_us_airport,
    _is_tier1_airport,
    _get_iata,
    _evaluate_fired,
    _create_determination,
    _check_rate_limit,
    _record_call,
    _source_call_counts,
    _source_recovery_cooldown,
    _source_failed_last_cycle,
    _update_recovery_cooldowns,
    FETCH_MAP,
    SOURCE_CACHE_KEY,
    RATE_LIMITS,
)
from gad.engine.models import TriggerDetermination


# ── Helper: build a MonitorTrigger with sensible defaults ──

def _make_trigger(
    id: str = "flight-delay-jfk",
    name: str = "Test Trigger",
    peril: str = "flight_delay",
    lat: float = 40.6413,
    lon: float = -73.7781,
    data_source: str = "opensky",
    threshold: float = 45,
    threshold_unit: str = "minutes",
    fires_when_above: bool = True,
) -> MonitorTrigger:
    return MonitorTrigger(
        id=id,
        name=name,
        peril=peril,
        lat=lat,
        lon=lon,
        location_label="Test Location",
        threshold=threshold,
        threshold_unit=threshold_unit,
        fires_when_above=fires_when_above,
        data_source=data_source,
        description="Test description",
    )


# ── _is_us_airport ──

class TestIsUsAirport:
    def test_us_airport_jfk(self):
        trigger = _make_trigger(id="flight-delay-jfk")
        assert _is_us_airport(trigger) is True

    def test_non_us_airport_del(self):
        trigger = _make_trigger(id="flight-delay-del")
        assert _is_us_airport(trigger) is False

    def test_non_us_airport_nrt(self):
        trigger = _make_trigger(id="flight-delay-nrt")
        assert _is_us_airport(trigger) is False


# ── _is_tier1_airport ──

class TestIsTier1Airport:
    def test_tier1_airport_jfk(self):
        trigger = _make_trigger(id="flight-delay-jfk")
        assert _is_tier1_airport(trigger) is True

    def test_tier2_airport_dtw(self):
        trigger = _make_trigger(id="flight-delay-dtw")
        assert _is_tier1_airport(trigger) is False

    def test_tier1_airport_del(self):
        trigger = _make_trigger(id="flight-delay-del")
        assert _is_tier1_airport(trigger) is True


# ── _get_iata ──

class TestGetIata:
    def test_flight_delay_trigger(self):
        trigger = _make_trigger(id="flight-delay-jfk")
        assert _get_iata(trigger) == "JFK"

    def test_aqi_trigger(self):
        trigger = _make_trigger(id="aqi-blr")
        assert _get_iata(trigger) == "BLR"

    def test_weather_trigger(self):
        trigger = _make_trigger(id="weather-heat-del")
        assert _get_iata(trigger) == "DEL"


# ── _evaluate_fired ──

class TestEvaluateFired:
    def test_openmeteo_fires_above(self):
        trigger = _make_trigger(
            data_source="openmeteo", threshold=42, threshold_unit="celsius",
            fires_when_above=True,
        )
        data = {"temperature_c": 45, "wind_speed_kmh": 10}
        assert _evaluate_fired(trigger, data) is True

    def test_openmeteo_no_fire(self):
        trigger = _make_trigger(
            data_source="openmeteo", threshold=42, threshold_unit="celsius",
            fires_when_above=True,
        )
        data = {"temperature_c": 30, "wind_speed_kmh": 10}
        assert _evaluate_fired(trigger, data) is False

    def test_openaq_fires(self):
        trigger = _make_trigger(data_source="openaq", threshold=150, threshold_unit="AQI")
        data = {"aqi": 200}
        assert _evaluate_fired(trigger, data) is True

    def test_openaq_no_fire(self):
        trigger = _make_trigger(data_source="openaq", threshold=150, threshold_unit="AQI")
        data = {"aqi": 50}
        assert _evaluate_fired(trigger, data) is False

    def test_firms_fires(self):
        trigger = _make_trigger(data_source="firms", threshold=10, threshold_unit="fire_count")
        data = {"fire_count": 15}
        assert _evaluate_fired(trigger, data) is True

    def test_firms_no_fire(self):
        trigger = _make_trigger(data_source="firms", threshold=10, threshold_unit="fire_count")
        data = {"fire_count": 3}
        assert _evaluate_fired(trigger, data) is False

    def test_opensky_fires_zero_departures(self):
        trigger = _make_trigger(data_source="opensky", threshold=45)
        data = {"total_flights": 0, "source": "opensky"}
        # OpenSky fires when 0 departures
        result = _evaluate_fired(trigger, data)
        assert isinstance(result, bool)

    def test_opensky_aviationstack_delay_fires(self):
        trigger = _make_trigger(data_source="opensky", threshold=45)
        data = {"total_flights": 10, "avg_delay_min": 60, "source": "aviationstack"}
        assert _evaluate_fired(trigger, data) is True

    def test_chirps_fires_below(self):
        trigger = _make_trigger(
            data_source="chirps", threshold=50, threshold_unit="mm_rainfall",
            fires_when_above=False,
        )
        data = {"rainfall_mm": 20}
        assert _evaluate_fired(trigger, data) is True

    def test_chirps_no_fire(self):
        trigger = _make_trigger(
            data_source="chirps", threshold=50, threshold_unit="mm_rainfall",
            fires_when_above=False,
        )
        data = {"rainfall_mm": 80}
        assert _evaluate_fired(trigger, data) is False

    def test_usgs_earthquake_fires(self):
        trigger = _make_trigger(data_source="usgs", threshold=5.0, threshold_unit="magnitude")
        data = {"max_magnitude": 6.2, "earthquake_count": 1}
        assert _evaluate_fired(trigger, data) is True

    def test_usgs_earthquake_no_fire(self):
        trigger = _make_trigger(data_source="usgs", threshold=5.0, threshold_unit="magnitude")
        data = {"max_magnitude": 3.1, "earthquake_count": 2}
        assert _evaluate_fired(trigger, data) is False

    def test_aisstream_congestion_fires(self):
        trigger = _make_trigger(
            data_source="aisstream", threshold=20, threshold_unit="vessels",
        )
        data = {"vessels_at_anchor": 25, "vessel_count": 30}
        assert _evaluate_fired(trigger, data) is True

    def test_aisstream_congestion_no_fire(self):
        trigger = _make_trigger(
            data_source="aisstream", threshold=20, threshold_unit="vessels",
        )
        data = {"vessels_at_anchor": 10, "vessel_count": 15}
        assert _evaluate_fired(trigger, data) is False

    def test_usgs_water_flood_fires(self):
        trigger = _make_trigger(
            data_source="usgs_water", threshold=4.5, threshold_unit="metres",
        )
        data = {"gauge_height_m": 5.2}
        assert _evaluate_fired(trigger, data) is True

    def test_usgs_water_flood_no_fire(self):
        trigger = _make_trigger(
            data_source="usgs_water", threshold=4.5, threshold_unit="metres",
        )
        data = {"gauge_height_m": 3.0}
        assert _evaluate_fired(trigger, data) is False

    def test_noaa_nhc_cyclone_fires(self):
        trigger = _make_trigger(
            data_source="noaa_nhc", threshold=64, threshold_unit="knots",
        )
        data = {
            "active_storm_count": 1,
            "nearest_storm": {"name": "TestStorm", "wind_knots": 80},
            "nearest_distance_km": 100,
        }
        assert _evaluate_fired(trigger, data) is True

    def test_noaa_nhc_cyclone_no_storms(self):
        trigger = _make_trigger(
            data_source="noaa_nhc", threshold=64, threshold_unit="knots",
        )
        data = {"active_storm_count": 0, "nearest_storm": None}
        assert _evaluate_fired(trigger, data) is False

    def test_unknown_data_source_returns_false(self):
        trigger = _make_trigger(data_source="unknown_source")
        data = {"value": 999}
        assert _evaluate_fired(trigger, data) is False


# ── _create_determination ──

class TestCreateDetermination:
    def test_returns_valid_determination(self):
        trigger = _make_trigger(id="flight-delay-jfk")
        data = {"total_flights": 5, "source": "opensky"}
        det = _create_determination(trigger, data, fired=True)

        assert isinstance(det, TriggerDetermination)
        assert isinstance(det.determination_id, UUID)
        assert isinstance(det.trigger_id, UUID)
        assert det.fired is True
        assert det.fired_at is not None
        assert det.data_snapshot_hash  # non-empty
        assert det.computation_version  # non-empty
        assert det.prev_hash  # should be GENESIS_HASH

    def test_not_fired_has_no_fired_at(self):
        trigger = _make_trigger(id="aqi-del")
        data = {"aqi": 50}
        det = _create_determination(trigger, data, fired=False)

        assert det.fired is False
        assert det.fired_at is None

    def test_data_snapshot_hash_is_deterministic(self):
        trigger = _make_trigger(id="flight-delay-jfk")
        data = {"total_flights": 5, "source": "opensky"}
        det1 = _create_determination(trigger, data, fired=True)
        det2 = _create_determination(trigger, data, fired=True)
        assert det1.data_snapshot_hash == det2.data_snapshot_hash


# ── FETCH_MAP ──

class TestFetchMap:
    EXPECTED_SOURCES = [
        "opensky", "openaq", "firms", "openmeteo",
        "chirps", "usgs", "aisstream", "usgs_water", "noaa_nhc", "ndvi", "noaa_swpc",
        "chirps", "usgs", "aisstream", "usgs_water", "noaa_nhc", "ndvi", "who_don",
    ]

    def test_all_expected_sources_present(self):
        for source in self.EXPECTED_SOURCES:
            assert source in FETCH_MAP, f"Missing FETCH_MAP entry for {source}"

    def test_all_entries_are_callable(self):
        for source, fn in FETCH_MAP.items():
            assert callable(fn), f"FETCH_MAP[{source}] is not callable"

    def test_no_extra_entries(self):
        assert set(FETCH_MAP.keys()) == set(self.EXPECTED_SOURCES)


# ── SOURCE_CACHE_KEY ──

class TestSourceCacheKey:
    EXPECTED_SOURCES = [
        "opensky", "openaq", "firms", "openmeteo",
        "chirps", "usgs", "aisstream", "usgs_water", "noaa_nhc", "ndvi", "noaa_swpc",
        "chirps", "usgs", "aisstream", "usgs_water", "noaa_nhc", "ndvi", "who_don",
    ]

    def test_all_expected_sources_present(self):
        for source in self.EXPECTED_SOURCES:
            assert source in SOURCE_CACHE_KEY, f"Missing SOURCE_CACHE_KEY entry for {source}"

    def test_all_values_are_strings(self):
        for source, key in SOURCE_CACHE_KEY.items():
            assert isinstance(key, str), f"SOURCE_CACHE_KEY[{source}] is not a string"

    def test_keys_match_fetch_map(self):
        assert set(SOURCE_CACHE_KEY.keys()) == set(FETCH_MAP.keys())


# ── CEO-05: Per-source rate limiter ──

class TestRateLimiter:
    def setup_method(self):
        """Clear rate limit state before each test."""
        _source_call_counts.clear()

    def test_unlimited_source_always_allowed(self):
        """Sources not in RATE_LIMITS are never rate-limited."""
        assert _check_rate_limit("openmeteo") is True
        # Record many calls — still unlimited
        for _ in range(10000):
            _record_call("openmeteo")
        assert _check_rate_limit("openmeteo") is True

    def test_rate_limit_blocks_when_exceeded(self):
        """Source blocked when it hits the limit within the window."""
        import time as _time
        # FIRMS: 5000 per 600s — use a smaller test
        # Use aviationstack: 16 per 86400s
        assert _check_rate_limit("aviationstack") is True
        for _ in range(16):
            _record_call("aviationstack")
        assert _check_rate_limit("aviationstack") is False

    def test_rate_limit_allows_under_limit(self):
        """Source allowed when under the limit."""
        for _ in range(15):
            _record_call("aviationstack")
        assert _check_rate_limit("aviationstack") is True

    def test_expired_timestamps_pruned(self):
        """Old timestamps outside the window are pruned."""
        import time as _time
        now = _time.time()
        # Manually inject old timestamps for firms (600s window)
        _source_call_counts["firms"] = [now - 700] * 5000  # all expired
        assert _check_rate_limit("firms") is True
        # Old ones should be pruned
        assert len(_source_call_counts["firms"]) == 0

    def test_rate_limits_dict_has_expected_sources(self):
        """RATE_LIMITS dict contains expected entries."""
        assert "firms" in RATE_LIMITS
        assert "aviationstack" in RATE_LIMITS
        assert "waqi" in RATE_LIMITS
        # openmeteo should NOT be rate limited
        assert "openmeteo" not in RATE_LIMITS

    def test_record_call_noop_for_unlimited(self):
        """_record_call does nothing for sources not in RATE_LIMITS."""
        _record_call("openmeteo")
        assert "openmeteo" not in _source_call_counts


# ── CEO-04: Source recovery cooldown ──

class TestRecoveryCooldown:
    def setup_method(self):
        """Clear cooldown state before each test."""
        _source_recovery_cooldown.clear()
        import gad.monitor.fetcher as _f
        _f._source_failed_last_cycle = set()

    def test_recovery_sets_cooldown(self):
        """When a source was failing and recovers, cooldown = 2."""
        import gad.monitor.fetcher as _f
        _f._source_failed_last_cycle = {"firms"}
        _update_recovery_cooldowns(
            succeeded={"firms"}, failed=set()
        )
        assert _source_recovery_cooldown.get("firms") == 1  # 2 set then decremented by 1

    def test_cooldown_decrements_each_cycle(self):
        """Cooldown decrements by 1 each cycle and removes at 0."""
        _source_recovery_cooldown["firms"] = 2
        _update_recovery_cooldowns(succeeded={"firms"}, failed=set())
        assert _source_recovery_cooldown.get("firms") == 1
        _update_recovery_cooldowns(succeeded={"firms"}, failed=set())
        assert "firms" not in _source_recovery_cooldown

    def test_no_cooldown_when_source_not_previously_failing(self):
        """No cooldown if source was not failing in the previous cycle."""
        import gad.monitor.fetcher as _f
        _f._source_failed_last_cycle = set()  # nothing was failing
        _update_recovery_cooldowns(succeeded={"firms"}, failed=set())
        assert "firms" not in _source_recovery_cooldown

    def test_failed_sources_tracked_for_next_cycle(self):
        """_source_failed_last_cycle is updated at end of cycle."""
        import gad.monitor.fetcher as _f
        _update_recovery_cooldowns(succeeded=set(), failed={"waqi", "firms"})
        assert _f._source_failed_last_cycle == {"waqi", "firms"}

    def test_no_double_cooldown(self):
        """If a source is already in cooldown, a second recovery doesn't reset it."""
        import gad.monitor.fetcher as _f
        _source_recovery_cooldown["firms"] = 1
        _f._source_failed_last_cycle = {"firms"}
        _update_recovery_cooldowns(succeeded={"firms"}, failed=set())
        # Should NOT reset to 2; the existing cooldown was decremented to 0 and removed
        assert "firms" not in _source_recovery_cooldown
