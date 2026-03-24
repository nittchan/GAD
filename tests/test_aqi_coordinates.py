"""
Tests for BUG-01 fix — all airports have valid city coordinates for AQI.
Verifies that effective_city_lat/lon are non-zero and that explicit city
coordinates are within 50km of airport coordinates (sanity bound).
"""

from __future__ import annotations

import math

import pytest

from gad.monitor.airports import ALL_AIRPORTS, Airport
from gad.monitor.triggers import GLOBAL_TRIGGERS


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine distance between two lat/lon points in kilometres.
    Uses the standard math module only.
    """
    R = 6371.0  # Earth radius in km
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class TestEffectiveCityCoordinates:
    """Every airport must have non-zero effective city coordinates."""

    @pytest.mark.parametrize("airport", ALL_AIRPORTS, ids=lambda a: a.iata)
    def test_effective_city_lat_nonzero(self, airport: Airport):
        assert airport.effective_city_lat != 0, (
            f"{airport.iata} ({airport.name}) has effective_city_lat == 0"
        )

    @pytest.mark.parametrize("airport", ALL_AIRPORTS, ids=lambda a: a.iata)
    def test_effective_city_lon_nonzero(self, airport: Airport):
        assert airport.effective_city_lon != 0, (
            f"{airport.iata} ({airport.name}) has effective_city_lon == 0"
        )


class TestExplicitCityCoordinatesSanity:
    """
    For airports that define explicit city_lat/city_lon, the city centre
    must be within 80km of the airport (sanity check — most cities are
    much closer, but some airports like KUL ~50km and NRT ~67km from
    city centre).
    """

    _airports_with_explicit_city = [
        a for a in ALL_AIRPORTS if a.city_lat is not None and a.city_lon is not None
    ]

    @pytest.mark.parametrize(
        "airport",
        _airports_with_explicit_city,
        ids=lambda a: a.iata,
    )
    def test_city_within_80km_of_airport(self, airport: Airport):
        dist = _haversine_km(airport.lat, airport.lon, airport.city_lat, airport.city_lon)
        assert dist < 80, (
            f"{airport.iata}: city centre is {dist:.1f}km from airport (limit 80km). "
            f"Airport=({airport.lat}, {airport.lon}), City=({airport.city_lat}, {airport.city_lon})"
        )


class TestAqiTriggersUseCityCoordinates:
    """
    AQI triggers must use city centre coordinates, not airport runway
    coordinates. This is the core BUG-01 fix validation.
    """

    _KNOWN_AIRPORTS = {
        "BLR": {"city_lat": 12.9716, "city_lon": 77.5946, "airport_lat": 13.1986, "airport_lon": 77.7066},
        "DEL": {"city_lat": 28.6139, "city_lon": 77.2090, "airport_lat": 28.5562, "airport_lon": 77.1000},
        "NRT": {"city_lat": 35.6762, "city_lon": 139.6503, "airport_lat": 35.7647, "airport_lon": 140.3864},
    }

    @pytest.mark.parametrize("iata", ["BLR", "DEL", "NRT"])
    def test_aqi_trigger_uses_city_coords(self, iata: str):
        """AQI trigger lat/lon should match city coordinates, not airport coordinates."""
        aqi_trigger = next(
            (t for t in GLOBAL_TRIGGERS if t.id == f"aqi-{iata.lower()}"),
            None,
        )
        assert aqi_trigger is not None, f"No AQI trigger found for {iata}"

        expected = self._KNOWN_AIRPORTS[iata]

        # The trigger coordinates should be the city coordinates
        assert aqi_trigger.lat == pytest.approx(expected["city_lat"], abs=0.01), (
            f"AQI trigger for {iata} lat={aqi_trigger.lat} should be city_lat={expected['city_lat']}"
        )
        assert aqi_trigger.lon == pytest.approx(expected["city_lon"], abs=0.01), (
            f"AQI trigger for {iata} lon={aqi_trigger.lon} should be city_lon={expected['city_lon']}"
        )

        # And NOT the airport coordinates (for airports where they differ)
        if expected["city_lat"] != expected["airport_lat"]:
            assert aqi_trigger.lat != pytest.approx(expected["airport_lat"], abs=0.001), (
                f"AQI trigger for {iata} is using airport coordinates instead of city coordinates"
            )

    def test_aqi_triggers_exist_for_tier1_and_tier2(self):
        """AQI triggers should exist for all tier 1 and tier 2 airports."""
        tier12_airports = [a for a in ALL_AIRPORTS if a.tier <= 2]
        aqi_ids = {t.id for t in GLOBAL_TRIGGERS if t.peril == "air_quality"}

        for airport in tier12_airports:
            expected_id = f"aqi-{airport.iata.lower()}"
            assert expected_id in aqi_ids, (
                f"Missing AQI trigger for tier-{airport.tier} airport {airport.iata}"
            )


class TestAirportCoordinatesNonZero:
    """Airport lat/lon themselves must be non-zero (no default-init bugs)."""

    @pytest.mark.parametrize("airport", ALL_AIRPORTS, ids=lambda a: a.iata)
    def test_airport_lat_nonzero(self, airport: Airport):
        assert airport.lat != 0, f"{airport.iata} has lat == 0"

    @pytest.mark.parametrize("airport", ALL_AIRPORTS, ids=lambda a: a.iata)
    def test_airport_lon_nonzero(self, airport: Airport):
        assert airport.lon != 0, f"{airport.iata} has lon == 0"
