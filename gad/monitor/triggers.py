"""
Pre-built trigger registry for the global monitor.
Auto-generates flight delay, weather, and AQI triggers for all 200+ airports.
Plus standalone wildfire, drought, and extreme weather triggers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from gad.monitor.airports import ALL_AIRPORTS, Airport
from gad.monitor.ports import ALL_PORTS, Port

PerilType = Literal["flight_delay", "air_quality", "wildfire", "drought", "extreme_weather", "earthquake", "marine"]


@dataclass(frozen=True)
class MonitorTrigger:
    """A pre-built trigger for the global monitor map."""
    id: str
    name: str
    peril: PerilType
    lat: float
    lon: float
    location_label: str
    threshold: float
    threshold_unit: str
    fires_when_above: bool
    data_source: str
    description: str


def _generate_airport_triggers(airports: list[Airport]) -> list[MonitorTrigger]:
    """Generate flight delay + weather + AQI triggers for each airport."""
    triggers = []
    for a in airports:
        # Flight delay trigger
        # Tier-1 airports use AviationStack (real delay in minutes) with OpenSky fallback.
        # Tier-2/3 airports use OpenSky only (departure count — disruption proxy).
        threshold = 45 if a.tier == 1 else 60
        if a.tier == 1:
            description = f"Parametric trigger: fires when average departure delay exceeds {threshold} min at {a.iata} (AviationStack), or when 0 departures in 2h (OpenSky fallback)."
        else:
            description = f"Parametric trigger: fires when 0 departures observed in 2h at {a.iata} (airport disruption via OpenSky)."
        triggers.append(MonitorTrigger(
            id=f"flight-delay-{a.iata.lower()}",
            name=f"{a.city} {a.iata}",
            peril="flight_delay",
            lat=a.lat, lon=a.lon,
            location_label=f"{a.name}, {a.city}",
            threshold=threshold,
            threshold_unit="minutes",
            fires_when_above=True,
            data_source="opensky",
            description=description,
        ))

        # Weather trigger (extreme heat/cold based on latitude)
        if abs(a.lat) > 45:
            # High latitude — freeze risk
            triggers.append(MonitorTrigger(
                id=f"weather-freeze-{a.iata.lower()}",
                name=f"{a.city} Freeze Risk",
                peril="extreme_weather",
                lat=a.lat, lon=a.lon,
                location_label=f"{a.city}, {a.country}",
                threshold=-15,
                threshold_unit="celsius",
                fires_when_above=False,
                data_source="openmeteo",
                description=f"Parametric trigger fires when temperature drops below -15°C at {a.city}.",
            ))
        elif abs(a.lat) < 35:
            # Tropical/subtropical — heat risk
            triggers.append(MonitorTrigger(
                id=f"weather-heat-{a.iata.lower()}",
                name=f"{a.city} Heat Risk",
                peril="extreme_weather",
                lat=a.lat, lon=a.lon,
                location_label=f"{a.city}, {a.country}",
                threshold=42,
                threshold_unit="celsius",
                fires_when_above=True,
                data_source="openmeteo",
                description=f"Parametric trigger fires when temperature exceeds 42°C at {a.city}.",
            ))
        else:
            # Mid-latitude — both risks, use heat as default
            triggers.append(MonitorTrigger(
                id=f"weather-heat-{a.iata.lower()}",
                name=f"{a.city} Extreme Weather",
                peril="extreme_weather",
                lat=a.lat, lon=a.lon,
                location_label=f"{a.city}, {a.country}",
                threshold=40,
                threshold_unit="celsius",
                fires_when_above=True,
                data_source="openmeteo",
                description=f"Parametric trigger fires when temperature exceeds 40°C at {a.city}.",
            ))

        # AQI trigger (only for tier 1 and 2 airports to stay within rate limits)
        # Uses city centre coordinates, not airport runway coordinates — AQI monitors
        # are in urban areas, not at airfields (see BUG-01).
        if a.tier <= 2:
            triggers.append(MonitorTrigger(
                id=f"aqi-{a.iata.lower()}",
                name=f"{a.city} AQI",
                peril="air_quality",
                lat=a.effective_city_lat, lon=a.effective_city_lon,
                location_label=f"{a.city}, {a.country}",
                threshold=150,
                threshold_unit="AQI",
                fires_when_above=True,
                data_source="openaq",
                description=f"Parametric trigger fires when AQI exceeds 150 (unhealthy) at {a.city}.",
            ))

    return triggers


# ──────────────────────────────────────────────────────────────
# Standalone triggers (not airport-derived)
# ──────────────────────────────────────────────────────────────

STANDALONE_TRIGGERS: list[MonitorTrigger] = [
    # ── Wildfire ──
    MonitorTrigger(id="fire-california", name="California Wildfire", peril="wildfire", lat=36.7783, lon=-119.4179, location_label="Central California, USA", threshold=10, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >10 active fires within 100km radius."),
    MonitorTrigger(id="fire-australia-nsw", name="NSW Bushfire", peril="wildfire", lat=-33.8688, lon=151.2093, location_label="New South Wales, Australia", threshold=10, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >10 active fires within 100km radius."),
    MonitorTrigger(id="fire-amazon", name="Amazon Fires", peril="wildfire", lat=-3.4653, lon=-62.2159, location_label="Amazonas, Brazil", threshold=20, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >20 active fires in the Amazon basin."),
    MonitorTrigger(id="fire-siberia", name="Siberia Wildfire", peril="wildfire", lat=62.0, lon=130.0, location_label="Yakutia, Russia", threshold=15, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >15 active fires in Siberian taiga."),
    MonitorTrigger(id="fire-portugal", name="Portugal Wildfire", peril="wildfire", lat=39.5, lon=-8.0, location_label="Central Portugal", threshold=5, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >5 active fires in Portugal."),
    MonitorTrigger(id="fire-canada-bc", name="BC Wildfire", peril="wildfire", lat=53.7267, lon=-127.6476, location_label="British Columbia, Canada", threshold=10, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >10 active fires in British Columbia."),
    MonitorTrigger(id="fire-greece", name="Greece Wildfire", peril="wildfire", lat=38.0, lon=23.7, location_label="Attica, Greece", threshold=5, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >5 active fires in Greece."),
    MonitorTrigger(id="fire-indonesia", name="Indonesia Peat Fires", peril="wildfire", lat=-2.5, lon=110.0, location_label="Kalimantan, Indonesia", threshold=20, threshold_unit="fire_count", fires_when_above=True, data_source="firms", description="NASA VIIRS detects >20 active peat fires in Kalimantan."),

    # ── Drought ──
    MonitorTrigger(id="drought-kenya-marsabit", name="Kenya Marsabit Drought", peril="drought", lat=2.3333, lon=37.9833, location_label="Marsabit, Kenya", threshold=50, threshold_unit="mm_rainfall", fires_when_above=False, data_source="chirps", description="Monthly rainfall drops below 50mm."),
    MonitorTrigger(id="drought-india-rajasthan", name="Rajasthan Drought", peril="drought", lat=26.9124, lon=75.7873, location_label="Jaipur, Rajasthan", threshold=30, threshold_unit="mm_rainfall", fires_when_above=False, data_source="chirps", description="Monthly rainfall drops below 30mm."),
    MonitorTrigger(id="drought-ethiopia", name="Ethiopia Drought", peril="drought", lat=9.0, lon=38.7, location_label="Addis Ababa region, Ethiopia", threshold=40, threshold_unit="mm_rainfall", fires_when_above=False, data_source="chirps", description="Monthly rainfall drops below 40mm."),
    MonitorTrigger(id="drought-sahel", name="Sahel Drought", peril="drought", lat=14.0, lon=2.0, location_label="Sahel region, Niger", threshold=30, threshold_unit="mm_rainfall", fires_when_above=False, data_source="chirps", description="Monthly rainfall drops below 30mm in the Sahel."),
    MonitorTrigger(id="drought-northeast-brazil", name="NE Brazil Drought", peril="drought", lat=-8.0, lon=-36.0, location_label="Pernambuco, Brazil", threshold=40, threshold_unit="mm_rainfall", fires_when_above=False, data_source="chirps", description="Monthly rainfall drops below 40mm."),

    # ── Earthquake ──
    MonitorTrigger(id="quake-japan", name="Japan Earthquake", peril="earthquake", lat=35.6762, lon=139.6503, location_label="Tokyo region, Japan", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-turkey", name="Turkey Earthquake", peril="earthquake", lat=39.9334, lon=32.8597, location_label="Ankara region, Turkey", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-california", name="California Earthquake", peril="earthquake", lat=34.0522, lon=-118.2437, location_label="Los Angeles, USA", threshold=4.5, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M4.5+ earthquake within 200km."),
    MonitorTrigger(id="quake-chile", name="Chile Earthquake", peril="earthquake", lat=-33.4489, lon=-70.6693, location_label="Santiago, Chile", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-indonesia", name="Indonesia Earthquake", peril="earthquake", lat=-6.2088, lon=106.8456, location_label="Jakarta, Indonesia", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-nepal", name="Nepal Earthquake", peril="earthquake", lat=27.7172, lon=85.3240, location_label="Kathmandu, Nepal", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-italy", name="Italy Earthquake", peril="earthquake", lat=42.3498, lon=13.3996, location_label="L'Aquila, Italy", threshold=4.5, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M4.5+ earthquake within 200km."),
    MonitorTrigger(id="quake-iran", name="Iran Earthquake", peril="earthquake", lat=35.6892, lon=51.3890, location_label="Tehran, Iran", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
    MonitorTrigger(id="quake-india-delhi", name="Delhi NCR Earthquake", peril="earthquake", lat=28.6139, lon=77.2090, location_label="Delhi NCR, India", threshold=4.5, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M4.5+ earthquake within 200km."),
    MonitorTrigger(id="quake-nz", name="New Zealand Earthquake", peril="earthquake", lat=-41.2866, lon=174.7756, location_label="Wellington, New Zealand", threshold=5.0, threshold_unit="magnitude", fires_when_above=True, data_source="usgs", description="USGS detects M5.0+ earthquake within 200km."),
]


# ──────────────────────────────────────────────────────────────
# Marine triggers (auto-generated from port registry)
# ──────────────────────────────────────────────────────────────

def _generate_marine_triggers(ports: list[Port]) -> list[MonitorTrigger]:
    """Generate congestion and dwell-time triggers for each port."""
    triggers = []
    for p in ports:
        # Port congestion: vessel count at anchor > threshold
        triggers.append(MonitorTrigger(
            id=f"marine-congestion-{p.id}",
            name=f"{p.name} Congestion",
            peril="marine",
            lat=p.lat, lon=p.lon,
            location_label=f"{p.name}, {p.country}",
            threshold=20,
            threshold_unit="vessels",
            fires_when_above=True,
            data_source="aisstream",
            description=f"Parametric trigger fires when more than 20 vessels are at anchor in {p.name} anchorage area.",
        ))
        # Port dwell time: mean time at anchor > threshold hours
        triggers.append(MonitorTrigger(
            id=f"marine-dwell-{p.id}",
            name=f"{p.name} Dwell Time",
            peril="marine",
            lat=p.lat, lon=p.lon,
            location_label=f"{p.name}, {p.country}",
            threshold=48,
            threshold_unit="hours",
            fires_when_above=True,
            data_source="aisstream",
            description=f"Parametric trigger fires when mean vessel dwell time exceeds 48 hours at {p.name} anchorage.",
        ))
    return triggers


# ──────────────────────────────────────────────────────────────
# Assemble all triggers
# ──────────────────────────────────────────────────────────────

GLOBAL_TRIGGERS: list[MonitorTrigger] = (
    _generate_airport_triggers(ALL_AIRPORTS)
    + STANDALONE_TRIGGERS
    + _generate_marine_triggers(ALL_PORTS)
)


def get_triggers_by_peril(peril: PerilType) -> list[MonitorTrigger]:
    return [t for t in GLOBAL_TRIGGERS if t.peril == peril]


def get_trigger_by_id(trigger_id: str) -> MonitorTrigger | None:
    return next((t for t in GLOBAL_TRIGGERS if t.id == trigger_id), None)


PERIL_LABELS: dict[PerilType, str] = {
    "flight_delay": "Flight Delay",
    "air_quality": "Air Quality",
    "wildfire": "Wildfire",
    "drought": "Drought",
    "extreme_weather": "Extreme Weather",
    "earthquake": "Earthquake",
    "marine": "Marine / Shipping",
}

PERIL_ICONS: dict[PerilType, str] = {
    "flight_delay": "airplane",
    "air_quality": "cloud",
    "wildfire": "fire_extinguisher",
    "drought": "water_drop",
    "extreme_weather": "thunderstorm",
    "earthquake": "globe_with_meridians",
    "marine": "anchor",
}
