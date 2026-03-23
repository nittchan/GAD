"""
Pre-built trigger registry for the global monitor.
Each trigger maps to a data source, location, threshold, and peril type.
These are the markers that appear on the map.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PeriType = Literal["flight_delay", "air_quality", "wildfire", "drought", "extreme_weather"]


@dataclass(frozen=True)
class MonitorTrigger:
    """A pre-built trigger for the global monitor map."""
    id: str
    name: str
    peril: PeriType
    lat: float
    lon: float
    location_label: str
    threshold: float
    threshold_unit: str
    fires_when_above: bool
    data_source: str
    description: str


# ──────────────────────────────────────────────────────────────
# Pre-built triggers — these appear as markers on the map
# ──────────────────────────────────────────────────────────────

GLOBAL_TRIGGERS: list[MonitorTrigger] = [
    # ── Flight Delay ──
    MonitorTrigger(
        id="flight-delay-blr",
        name="IndiGo BLR Delays",
        peril="flight_delay",
        lat=13.1986, lon=77.7066,
        location_label="Kempegowda Intl, Bengaluru",
        threshold=60, threshold_unit="minutes",
        fires_when_above=True,
        data_source="opensky",
        description="Parametric trigger fires when average departure delay exceeds 60 minutes at BLR.",
    ),
    MonitorTrigger(
        id="flight-delay-del",
        name="Delhi IGI Delays",
        peril="flight_delay",
        lat=28.5562, lon=77.1000,
        location_label="Indira Gandhi Intl, Delhi",
        threshold=60, threshold_unit="minutes",
        fires_when_above=True,
        data_source="opensky",
        description="Parametric trigger fires when average departure delay exceeds 60 minutes at DEL.",
    ),
    MonitorTrigger(
        id="flight-delay-jfk",
        name="JFK Airport Delays",
        peril="flight_delay",
        lat=40.6413, lon=-73.7781,
        location_label="JFK International, New York",
        threshold=45, threshold_unit="minutes",
        fires_when_above=True,
        data_source="opensky",
        description="Parametric trigger fires when average departure delay exceeds 45 minutes at JFK.",
    ),
    MonitorTrigger(
        id="flight-delay-lhr",
        name="Heathrow Delays",
        peril="flight_delay",
        lat=51.4700, lon=-0.4543,
        location_label="Heathrow, London",
        threshold=45, threshold_unit="minutes",
        fires_when_above=True,
        data_source="opensky",
        description="Parametric trigger fires when average departure delay exceeds 45 minutes at LHR.",
    ),

    # ── Air Quality ──
    MonitorTrigger(
        id="aqi-delhi",
        name="Delhi PM2.5 Crisis",
        peril="air_quality",
        lat=28.6139, lon=77.2090,
        location_label="New Delhi, India",
        threshold=150, threshold_unit="AQI",
        fires_when_above=True,
        data_source="openaq",
        description="Parametric trigger fires when Delhi AQI exceeds 150 (unhealthy). Basis for crop/health parametrics.",
    ),
    MonitorTrigger(
        id="aqi-beijing",
        name="Beijing Air Quality",
        peril="air_quality",
        lat=39.9042, lon=116.4074,
        location_label="Beijing, China",
        threshold=150, threshold_unit="AQI",
        fires_when_above=True,
        data_source="openaq",
        description="Parametric trigger fires when Beijing AQI exceeds 150.",
    ),
    MonitorTrigger(
        id="aqi-lahore",
        name="Lahore Smog Alert",
        peril="air_quality",
        lat=31.5204, lon=74.3587,
        location_label="Lahore, Pakistan",
        threshold=200, threshold_unit="AQI",
        fires_when_above=True,
        data_source="openaq",
        description="Parametric trigger fires when Lahore AQI exceeds 200 (very unhealthy).",
    ),
    MonitorTrigger(
        id="aqi-losangeles",
        name="LA Air Quality",
        peril="air_quality",
        lat=34.0522, lon=-118.2437,
        location_label="Los Angeles, USA",
        threshold=100, threshold_unit="AQI",
        fires_when_above=True,
        data_source="openaq",
        description="Parametric trigger fires when LA AQI exceeds 100 (unhealthy for sensitive groups).",
    ),

    # ── Wildfire ──
    MonitorTrigger(
        id="fire-california",
        name="California Fire Risk",
        peril="wildfire",
        lat=36.7783, lon=-119.4179,
        location_label="Central California, USA",
        threshold=10, threshold_unit="fire_count",
        fires_when_above=True,
        data_source="firms",
        description="Parametric trigger fires when NASA detects >10 active fires within 100km radius.",
    ),
    MonitorTrigger(
        id="fire-australia-nsw",
        name="NSW Bushfire Risk",
        peril="wildfire",
        lat=-33.8688, lon=151.2093,
        location_label="New South Wales, Australia",
        threshold=10, threshold_unit="fire_count",
        fires_when_above=True,
        data_source="firms",
        description="Parametric trigger fires when NASA detects >10 active fires within 100km.",
    ),
    MonitorTrigger(
        id="fire-amazon",
        name="Amazon Deforestation Fires",
        peril="wildfire",
        lat=-3.4653, lon=-62.2159,
        location_label="Amazonas, Brazil",
        threshold=20, threshold_unit="fire_count",
        fires_when_above=True,
        data_source="firms",
        description="Parametric trigger fires when NASA detects >20 active fires in the Amazon basin.",
    ),

    # ── Drought ──
    MonitorTrigger(
        id="drought-kenya-marsabit",
        name="Kenya Drought (Marsabit)",
        peril="drought",
        lat=2.3333, lon=37.9833,
        location_label="Marsabit, Kenya",
        threshold=50, threshold_unit="mm_rainfall",
        fires_when_above=False,
        data_source="chirps",
        description="Parametric trigger fires when monthly rainfall drops below 50mm. Basis for crop insurance.",
    ),
    MonitorTrigger(
        id="drought-india-rajasthan",
        name="Rajasthan Drought Watch",
        peril="drought",
        lat=26.9124, lon=75.7873,
        location_label="Jaipur, Rajasthan",
        threshold=30, threshold_unit="mm_rainfall",
        fires_when_above=False,
        data_source="chirps",
        description="Parametric trigger fires when monthly rainfall drops below 30mm.",
    ),

    # ── Extreme Weather ──
    MonitorTrigger(
        id="weather-cyclone-bay",
        name="Bay of Bengal Cyclone Risk",
        peril="extreme_weather",
        lat=15.0, lon=85.0,
        location_label="Bay of Bengal",
        threshold=120, threshold_unit="km/h_wind",
        fires_when_above=True,
        data_source="openmeteo",
        description="Parametric trigger fires when wind speed exceeds 120 km/h (cyclone threshold).",
    ),
    MonitorTrigger(
        id="weather-flood-patna",
        name="Patna Flood Risk",
        peril="extreme_weather",
        lat=25.6093, lon=85.1376,
        location_label="Patna, Bihar",
        threshold=100, threshold_unit="mm_rainfall_24h",
        fires_when_above=True,
        data_source="openmeteo",
        description="Parametric trigger fires when 24h rainfall exceeds 100mm (flood threshold).",
    ),
    MonitorTrigger(
        id="weather-heatwave-eu",
        name="European Heatwave",
        peril="extreme_weather",
        lat=48.8566, lon=2.3522,
        location_label="Paris, France",
        threshold=40, threshold_unit="celsius",
        fires_when_above=True,
        data_source="openmeteo",
        description="Parametric trigger fires when temperature exceeds 40°C.",
    ),
    MonitorTrigger(
        id="weather-freeze-midwest",
        name="US Midwest Freeze",
        peril="extreme_weather",
        lat=41.8781, lon=-87.6298,
        location_label="Chicago, USA",
        threshold=-20, threshold_unit="celsius",
        fires_when_above=False,
        data_source="openmeteo",
        description="Parametric trigger fires when temperature drops below -20°C (crop freeze risk).",
    ),
]


def get_triggers_by_peril(peril: PeriType) -> list[MonitorTrigger]:
    return [t for t in GLOBAL_TRIGGERS if t.peril == peril]


def get_trigger_by_id(trigger_id: str) -> MonitorTrigger | None:
    return next((t for t in GLOBAL_TRIGGERS if t.id == trigger_id), None)


PERIL_LABELS: dict[PeriType, str] = {
    "flight_delay": "Flight Delay",
    "air_quality": "Air Quality",
    "wildfire": "Wildfire",
    "drought": "Drought",
    "extreme_weather": "Extreme Weather",
}

PERIL_ICONS: dict[PeriType, str] = {
    "flight_delay": "airplane",
    "air_quality": "cloud",
    "wildfire": "fire_extinguisher",
    "drought": "water_drop",
    "extreme_weather": "thunderstorm",
}
