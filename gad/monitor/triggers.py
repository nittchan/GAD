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
    # ── Flight Delay — 30 Tier-1 Airports ──
    # Asia
    MonitorTrigger(id="flight-delay-del", name="Delhi IGI", peril="flight_delay", lat=28.5562, lon=77.1000, location_label="Indira Gandhi Intl, Delhi", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    MonitorTrigger(id="flight-delay-bom", name="Mumbai CSIA", peril="flight_delay", lat=19.0896, lon=72.8656, location_label="Chhatrapati Shivaji Intl, Mumbai", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    MonitorTrigger(id="flight-delay-blr", name="Bengaluru KIA", peril="flight_delay", lat=13.1986, lon=77.7066, location_label="Kempegowda Intl, Bengaluru", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    MonitorTrigger(id="flight-delay-sin", name="Singapore Changi", peril="flight_delay", lat=1.3644, lon=103.9915, location_label="Changi Airport, Singapore", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-hkg", name="Hong Kong Intl", peril="flight_delay", lat=22.3080, lon=113.9185, location_label="Hong Kong International", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-nrt", name="Tokyo Narita", peril="flight_delay", lat=35.7647, lon=140.3864, location_label="Narita International, Tokyo", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-icn", name="Seoul Incheon", peril="flight_delay", lat=37.4602, lon=126.4407, location_label="Incheon International, Seoul", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-bkk", name="Bangkok Suvarnabhumi", peril="flight_delay", lat=13.6900, lon=100.7501, location_label="Suvarnabhumi, Bangkok", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-pek", name="Beijing Capital", peril="flight_delay", lat=40.0799, lon=116.6031, location_label="Capital International, Beijing", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    MonitorTrigger(id="flight-delay-pvg", name="Shanghai Pudong", peril="flight_delay", lat=31.1443, lon=121.8083, location_label="Pudong International, Shanghai", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    # Middle East
    MonitorTrigger(id="flight-delay-dxb", name="Dubai Intl", peril="flight_delay", lat=25.2532, lon=55.3657, location_label="Dubai International", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-doh", name="Doha Hamad", peril="flight_delay", lat=25.2731, lon=51.6081, location_label="Hamad International, Doha", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-auh", name="Abu Dhabi", peril="flight_delay", lat=24.4330, lon=54.6511, location_label="Zayed International, Abu Dhabi", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    # Europe
    MonitorTrigger(id="flight-delay-lhr", name="London Heathrow", peril="flight_delay", lat=51.4700, lon=-0.4543, location_label="Heathrow, London", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-cdg", name="Paris CDG", peril="flight_delay", lat=49.0097, lon=2.5479, location_label="Charles de Gaulle, Paris", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-fra", name="Frankfurt", peril="flight_delay", lat=50.0379, lon=8.5622, location_label="Frankfurt Airport", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-ams", name="Amsterdam Schiphol", peril="flight_delay", lat=52.3105, lon=4.7683, location_label="Schiphol, Amsterdam", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-ist", name="Istanbul", peril="flight_delay", lat=41.2753, lon=28.7519, location_label="Istanbul Airport", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-mad", name="Madrid Barajas", peril="flight_delay", lat=40.4983, lon=-3.5676, location_label="Barajas, Madrid", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    # North America
    MonitorTrigger(id="flight-delay-jfk", name="New York JFK", peril="flight_delay", lat=40.6413, lon=-73.7781, location_label="JFK International, New York", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-lax", name="Los Angeles LAX", peril="flight_delay", lat=33.9416, lon=-118.4085, location_label="LAX, Los Angeles", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-ord", name="Chicago O'Hare", peril="flight_delay", lat=41.9742, lon=-87.9073, location_label="O'Hare International, Chicago", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-atl", name="Atlanta Hartsfield", peril="flight_delay", lat=33.6407, lon=-84.4277, location_label="Hartsfield-Jackson, Atlanta", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-dfw", name="Dallas/Fort Worth", peril="flight_delay", lat=32.8998, lon=-97.0403, location_label="DFW International, Dallas", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-yyz", name="Toronto Pearson", peril="flight_delay", lat=43.6777, lon=-79.6248, location_label="Pearson International, Toronto", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-mex", name="Mexico City", peril="flight_delay", lat=19.4363, lon=-99.0721, location_label="Benito Juárez, Mexico City", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    # South America
    MonitorTrigger(id="flight-delay-gru", name="São Paulo Guarulhos", peril="flight_delay", lat=-23.4356, lon=-46.4731, location_label="Guarulhos, São Paulo", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    # Africa
    MonitorTrigger(id="flight-delay-jnb", name="Johannesburg OR Tambo", peril="flight_delay", lat=-26.1392, lon=28.2460, location_label="OR Tambo, Johannesburg", threshold=60, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 60 minutes."),
    # Oceania
    MonitorTrigger(id="flight-delay-syd", name="Sydney Kingsford", peril="flight_delay", lat=-33.9461, lon=151.1772, location_label="Kingsford Smith, Sydney", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),
    MonitorTrigger(id="flight-delay-mel", name="Melbourne Tullamarine", peril="flight_delay", lat=-37.6690, lon=144.8410, location_label="Tullamarine, Melbourne", threshold=45, threshold_unit="minutes", fires_when_above=True, data_source="opensky", description="Parametric trigger fires when average departure delay exceeds 45 minutes."),

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
