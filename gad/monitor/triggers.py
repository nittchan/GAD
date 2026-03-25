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

PerilType = Literal["flight_delay", "air_quality", "wildfire", "drought", "extreme_weather", "earthquake", "marine", "flood", "cyclone", "crop", "solar", "health", "disaster", "eonet"]


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

    # ── Flood (USGS river gauges) ──
    # site_id is stored in the trigger ID: flood-{site_id}
    # Thresholds in metres — calibrated per gauge to minor/moderate flood stage
    MonitorTrigger(id="flood-02089500", name="Neuse River, NC", peril="flood", lat=35.7722, lon=-78.5467, location_label="Neuse River at Goldsboro, NC", threshold=4.5, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 4.5m (minor flood stage)."),
    MonitorTrigger(id="flood-07010000", name="Mississippi, St. Louis", peril="flood", lat=38.6270, lon=-90.1994, location_label="Mississippi River at St. Louis, MO", threshold=9.1, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 9.1m (flood stage 30ft)."),
    MonitorTrigger(id="flood-07289000", name="Mississippi, Vicksburg", peril="flood", lat=32.3526, lon=-90.8779, location_label="Mississippi River at Vicksburg, MS", threshold=13.1, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 13.1m (flood stage 43ft)."),
    MonitorTrigger(id="flood-03611500", name="Ohio River, Paducah", peril="flood", lat=37.0834, lon=-88.6001, location_label="Ohio River at Paducah, KY", threshold=11.6, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 11.6m (flood stage 38ft)."),
    MonitorTrigger(id="flood-01463500", name="Delaware River, Trenton", peril="flood", lat=40.2206, lon=-74.7806, location_label="Delaware River at Trenton, NJ", threshold=6.1, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 6.1m (flood stage 20ft)."),
    MonitorTrigger(id="flood-08066500", name="Trinity River, TX", peril="flood", lat=30.3419, lon=-94.8900, location_label="Trinity River at Romayor, TX", threshold=7.6, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 7.6m (flood stage 25ft)."),
    MonitorTrigger(id="flood-12340000", name="Clark Fork, MT", peril="flood", lat=46.8722, lon=-113.9933, location_label="Clark Fork above Missoula, MT", threshold=2.7, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 2.7m (flood stage 9ft)."),
    MonitorTrigger(id="flood-11377100", name="Sacramento River, CA", peril="flood", lat=40.3957, lon=-122.0467, location_label="Sacramento River at Bend Bridge, CA", threshold=5.5, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.5m (flood stage 18ft)."),
    MonitorTrigger(id="flood-02358000", name="Apalachicola River, FL", peril="flood", lat=30.2319, lon=-85.0253, location_label="Apalachicola River near Blountstown, FL", threshold=5.8, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.8m (flood stage 19ft)."),
    MonitorTrigger(id="flood-05587450", name="Missouri River, IL", peril="flood", lat=38.8817, lon=-90.1778, location_label="Missouri River at Chain of Rocks, IL", threshold=7.9, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 7.9m (flood stage 26ft)."),
    MonitorTrigger(id="flood-06610000", name="Missouri River, Omaha", peril="flood", lat=41.2586, lon=-95.9378, location_label="Missouri River at Omaha, NE", threshold=8.8, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 8.8m (flood stage 29ft)."),
    MonitorTrigger(id="flood-02223000", name="Oconee River, GA", peril="flood", lat=33.0804, lon=-83.4287, location_label="Oconee River near Milledgeville, GA", threshold=6.7, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 6.7m (flood stage 22ft)."),
    MonitorTrigger(id="flood-05474500", name="Des Moines River, IA", peril="flood", lat=40.3986, lon=-91.3824, location_label="Des Moines River at Keosauqua, IA", threshold=5.5, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.5m (flood stage 18ft)."),
    MonitorTrigger(id="flood-01570500", name="Susquehanna River, PA", peril="flood", lat=40.2548, lon=-76.8867, location_label="Susquehanna River at Harrisburg, PA", threshold=5.2, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.2m (flood stage 17ft)."),
    MonitorTrigger(id="flood-02136000", name="Pee Dee River, SC", peril="flood", lat=34.2932, lon=-79.8756, location_label="Pee Dee River at Peedee, SC", threshold=4.3, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 4.3m (flood stage 14ft)."),
    MonitorTrigger(id="flood-07032000", name="Mississippi, Memphis", peril="flood", lat=35.1495, lon=-90.0490, location_label="Mississippi River at Memphis, TN", threshold=10.4, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 10.4m (flood stage 34ft)."),
    MonitorTrigger(id="flood-06807000", name="Missouri River, NE City", peril="flood", lat=40.6756, lon=-95.8522, location_label="Missouri River at Nebraska City, NE", threshold=5.5, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.5m (flood stage 18ft)."),
    MonitorTrigger(id="flood-05420500", name="Mississippi, Clinton", peril="flood", lat=41.7817, lon=-90.2519, location_label="Mississippi River at Clinton, IA", threshold=5.2, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 5.2m (flood stage 17ft)."),
    MonitorTrigger(id="flood-07374000", name="Mississippi, Baton Rouge", peril="flood", lat=30.4493, lon=-91.1916, location_label="Mississippi River at Baton Rouge, LA", threshold=11.0, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 11.0m (flood stage 36ft)."),
    MonitorTrigger(id="flood-05587000", name="Illinois River, IL", peril="flood", lat=38.9778, lon=-90.6483, location_label="Illinois River at Meredosia, IL", threshold=4.3, threshold_unit="metres", fires_when_above=True, data_source="usgs_water", description="Gauge height exceeds 4.3m (flood stage 14ft)."),

    # ── Tropical Cyclone (NOAA NHC) ──
    # Location-based: fires when active storm wind > 64 knots within 200km
    MonitorTrigger(id="cyclone-miami", name="Miami Cyclone", peril="cyclone", lat=25.7617, lon=-80.1918, location_label="Miami, FL", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Miami."),
    MonitorTrigger(id="cyclone-new-orleans", name="New Orleans Cyclone", peril="cyclone", lat=29.9511, lon=-90.0715, location_label="New Orleans, LA", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of New Orleans."),
    MonitorTrigger(id="cyclone-houston", name="Houston Cyclone", peril="cyclone", lat=29.7604, lon=-95.3698, location_label="Houston, TX", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Houston."),
    MonitorTrigger(id="cyclone-tokyo", name="Tokyo Cyclone", peril="cyclone", lat=35.6762, lon=139.6503, location_label="Tokyo, Japan", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Tokyo."),
    MonitorTrigger(id="cyclone-manila", name="Manila Cyclone", peril="cyclone", lat=14.5995, lon=120.9842, location_label="Manila, Philippines", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Manila."),
    MonitorTrigger(id="cyclone-dhaka", name="Dhaka Cyclone", peril="cyclone", lat=23.8103, lon=90.4125, location_label="Dhaka, Bangladesh", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Dhaka."),
    MonitorTrigger(id="cyclone-mumbai", name="Mumbai Cyclone", peril="cyclone", lat=19.0760, lon=72.8777, location_label="Mumbai, India", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Mumbai."),
    MonitorTrigger(id="cyclone-colombo", name="Colombo Cyclone", peril="cyclone", lat=6.9271, lon=79.8612, location_label="Colombo, Sri Lanka", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Colombo."),
    MonitorTrigger(id="cyclone-taipei", name="Taipei Cyclone", peril="cyclone", lat=25.0330, lon=121.5654, location_label="Taipei, Taiwan", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Taipei."),
    MonitorTrigger(id="cyclone-guangzhou", name="Guangzhou Cyclone", peril="cyclone", lat=23.1291, lon=113.2644, location_label="Guangzhou, China", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Guangzhou."),
    MonitorTrigger(id="cyclone-hcmc", name="Ho Chi Minh Cyclone", peril="cyclone", lat=10.8231, lon=106.6297, location_label="Ho Chi Minh City, Vietnam", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of HCMC."),
    MonitorTrigger(id="cyclone-bangkok", name="Bangkok Cyclone", peril="cyclone", lat=13.7563, lon=100.5018, location_label="Bangkok, Thailand", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Bangkok."),
    MonitorTrigger(id="cyclone-kolkata", name="Kolkata Cyclone", peril="cyclone", lat=22.5726, lon=88.3639, location_label="Kolkata, India", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Kolkata."),
    MonitorTrigger(id="cyclone-osaka", name="Osaka Cyclone", peril="cyclone", lat=34.6937, lon=135.5023, location_label="Osaka, Japan", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Osaka."),
    MonitorTrigger(id="cyclone-shanghai", name="Shanghai Cyclone", peril="cyclone", lat=31.2304, lon=121.4737, location_label="Shanghai, China", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Shanghai."),
    MonitorTrigger(id="cyclone-hong-kong", name="Hong Kong Cyclone", peril="cyclone", lat=22.3193, lon=114.1694, location_label="Hong Kong, China", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Hong Kong."),
    MonitorTrigger(id="cyclone-darwin", name="Darwin Cyclone", peril="cyclone", lat=-12.4634, lon=130.8456, location_label="Darwin, Australia", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Darwin."),
    MonitorTrigger(id="cyclone-cairns", name="Cairns Cyclone", peril="cyclone", lat=-16.9186, lon=145.7781, location_label="Cairns, Australia", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Cairns."),
    MonitorTrigger(id="cyclone-nadi", name="Nadi Cyclone", peril="cyclone", lat=-17.7765, lon=177.9649, location_label="Nadi, Fiji", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Nadi."),
    MonitorTrigger(id="cyclone-yangon", name="Yangon Cyclone", peril="cyclone", lat=16.8661, lon=96.1951, location_label="Yangon, Myanmar", threshold=64, threshold_unit="knots", fires_when_above=True, data_source="noaa_nhc", description="Active tropical cyclone with wind >64 knots within 200km of Yangon."),

    # ── Crop / NDVI (agricultural zones) ──
    # NDVI < threshold during growing season = crop stress / drought
    MonitorTrigger(id="crop-punjab-wheat", name="Punjab Wheat", peril="crop", lat=30.9010, lon=75.8573, location_label="Punjab, India", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating wheat crop stress in Punjab."),
    MonitorTrigger(id="crop-maharashtra-sugarcane", name="Maharashtra Sugarcane", peril="crop", lat=19.7515, lon=75.7139, location_label="Maharashtra, India", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating sugarcane crop stress in Maharashtra."),
    MonitorTrigger(id="crop-andhra-rice", name="Andhra Pradesh Rice", peril="crop", lat=15.9129, lon=79.7400, location_label="Andhra Pradesh, India", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating rice crop stress in Andhra Pradesh."),
    MonitorTrigger(id="crop-iowa-corn", name="Iowa Corn Belt", peril="crop", lat=42.0046, lon=-93.2140, location_label="Iowa, USA", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating corn crop stress in Iowa."),
    MonitorTrigger(id="crop-kansas-wheat", name="Kansas Wheat", peril="crop", lat=38.5266, lon=-96.7265, location_label="Kansas, USA", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating wheat crop stress in Kansas."),
    MonitorTrigger(id="crop-mato-grosso-soy", name="Mato Grosso Soy", peril="crop", lat=-12.6819, lon=-56.9211, location_label="Mato Grosso, Brazil", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating soy crop stress in Mato Grosso."),
    MonitorTrigger(id="crop-pampas-wheat", name="Pampas Wheat", peril="crop", lat=-35.6566, lon=-63.3667, location_label="La Pampa, Argentina", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating wheat crop stress in Argentine Pampas."),
    MonitorTrigger(id="crop-ukraine-grain", name="Ukraine Chernozem Grain", peril="crop", lat=49.4444, lon=32.0598, location_label="Cherkasy, Ukraine", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating grain crop stress in Ukrainian chernozem."),
    MonitorTrigger(id="crop-sahel-millet", name="Sahel Millet/Sorghum", peril="crop", lat=13.5116, lon=2.1254, location_label="Niamey region, Niger", threshold=0.2, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.2 indicating millet/sorghum crop failure in the Sahel."),
    MonitorTrigger(id="crop-ethiopia-coffee", name="Ethiopia Coffee/Teff", peril="crop", lat=9.1450, lon=40.4897, location_label="Ethiopian Highlands", threshold=0.3, threshold_unit="NDVI", fires_when_above=False, data_source="ndvi", description="NDVI drops below 0.3 indicating coffee/teff crop stress in Ethiopian highlands."),

    # ── Solar / Space Weather (NOAA SWPC) ──
    # Planetary Kp index: global geomagnetic storm detection
    MonitorTrigger(id="solar-global-storm", name="Global Geomagnetic Storm", peril="solar", lat=0.0, lon=0.0, location_label="Global", threshold=5, threshold_unit="Kp", fires_when_above=True, data_source="noaa_swpc", description="NOAA SWPC Kp index >= 5 (G1 minor geomagnetic storm). Affects HF radio, satellite drag, power grid fluctuations."),
    MonitorTrigger(id="solar-severe", name="Severe Geomagnetic Storm", peril="solar", lat=0.0, lon=0.0, location_label="Global", threshold=7, threshold_unit="Kp", fires_when_above=True, data_source="noaa_swpc", description="NOAA SWPC Kp index >= 7 (G3 strong storm). Widespread HF radio blackout, satellite surface charging, power grid alerts."),
    MonitorTrigger(id="solar-extreme", name="Extreme Geomagnetic Storm", peril="solar", lat=0.0, lon=0.0, location_label="Global", threshold=8, threshold_unit="Kp", fires_when_above=True, data_source="noaa_swpc", description="NOAA SWPC Kp index >= 8 (G4 severe storm). GPS degraded, widespread voltage control problems, satellite orientation anomalies."),
    MonitorTrigger(id="solar-aviation-polar", name="Polar Route Aviation Risk", peril="solar", lat=70.0, lon=0.0, location_label="Polar Route (Arctic)", threshold=5, threshold_unit="Kp", fires_when_above=True, data_source="noaa_swpc", description="Kp >= 5 affects polar aviation routes. HF radio blackout forces rerouting of transpolar flights, increasing fuel costs and delays."),
    MonitorTrigger(id="solar-grid-risk", name="Power Grid Risk (North America)", peril="solar", lat=40.0, lon=-90.0, location_label="North America Grid", threshold=7, threshold_unit="Kp", fires_when_above=True, data_source="noaa_swpc", description="Kp >= 7 creates geomagnetically induced currents (GICs) that stress high-voltage transformers in mid-latitude power grids."),
    # ── Health / Pandemic (WHO DON) ──
    MonitorTrigger(id="health-delhi", name="Delhi Health Alert", peril="health", lat=28.6139, lon=77.2090, location_label="Delhi, India", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in India within 7 days."),
    MonitorTrigger(id="health-mumbai", name="Mumbai Health Alert", peril="health", lat=19.0760, lon=72.8777, location_label="Mumbai, India", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in India within 7 days."),
    MonitorTrigger(id="health-lagos", name="Lagos Health Alert", peril="health", lat=6.5244, lon=3.3792, location_label="Lagos, Nigeria", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Nigeria within 7 days."),
    MonitorTrigger(id="health-dhaka", name="Dhaka Health Alert", peril="health", lat=23.8103, lon=90.4125, location_label="Dhaka, Bangladesh", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Bangladesh within 7 days."),
    MonitorTrigger(id="health-jakarta", name="Jakarta Health Alert", peril="health", lat=-6.2088, lon=106.8456, location_label="Jakarta, Indonesia", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Indonesia within 7 days."),
    MonitorTrigger(id="health-cairo", name="Cairo Health Alert", peril="health", lat=30.0444, lon=31.2357, location_label="Cairo, Egypt", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Egypt within 7 days."),
    MonitorTrigger(id="health-kinshasa", name="Kinshasa Health Alert", peril="health", lat=-4.4419, lon=15.2663, location_label="Kinshasa, DRC", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in DRC within 7 days."),
    MonitorTrigger(id="health-lima", name="Lima Health Alert", peril="health", lat=-12.0464, lon=-77.0428, location_label="Lima, Peru", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Peru within 7 days."),
    MonitorTrigger(id="health-bangkok", name="Bangkok Health Alert", peril="health", lat=13.7563, lon=100.5018, location_label="Bangkok, Thailand", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Thailand within 7 days."),
    MonitorTrigger(id="health-nairobi", name="Nairobi Health Alert", peril="health", lat=-1.2921, lon=36.8219, location_label="Nairobi, Kenya", threshold=1, threshold_unit="outbreaks", fires_when_above=True, data_source="who_don", description="WHO Disease Outbreak News reports >= 1 outbreak in Kenya within 7 days."),

    # ── Disaster (GDACS) ──
    # Multi-hazard disaster alerts from the Global Disaster Alert and Coordination System
    MonitorTrigger(id="disaster-ring-of-fire-japan", name="Japan Disaster Alert", peril="disaster", lat=35.68, lon=139.65, location_label="Tokyo, Japan", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event (earthquake, flood, cyclone, volcano) within 500km of Tokyo."),
    MonitorTrigger(id="disaster-ring-of-fire-indonesia", name="Indonesia Disaster Alert", peril="disaster", lat=-6.21, lon=106.85, location_label="Jakarta, Indonesia", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Jakarta."),
    MonitorTrigger(id="disaster-ring-of-fire-chile", name="Chile Disaster Alert", peril="disaster", lat=-33.45, lon=-70.67, location_label="Santiago, Chile", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Santiago."),
    MonitorTrigger(id="disaster-mediterranean-italy", name="Italy Disaster Alert", peril="disaster", lat=42.35, lon=13.40, location_label="L'Aquila, Italy", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of L'Aquila."),
    MonitorTrigger(id="disaster-caribbean-haiti", name="Haiti Disaster Alert", peril="disaster", lat=18.54, lon=-72.34, location_label="Port-au-Prince, Haiti", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Port-au-Prince."),
    MonitorTrigger(id="disaster-south-asia-bangladesh", name="Bangladesh Disaster Alert", peril="disaster", lat=23.81, lon=90.41, location_label="Dhaka, Bangladesh", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Dhaka."),
    MonitorTrigger(id="disaster-east-africa-mozambique", name="Mozambique Disaster Alert", peril="disaster", lat=-25.97, lon=32.57, location_label="Maputo, Mozambique", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Maputo."),
    MonitorTrigger(id="disaster-central-america-guatemala", name="Guatemala Disaster Alert", peril="disaster", lat=14.63, lon=-90.51, location_label="Guatemala City, Guatemala", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Guatemala City."),
    MonitorTrigger(id="disaster-pacific-philippines", name="Philippines Disaster Alert", peril="disaster", lat=14.60, lon=120.98, location_label="Manila, Philippines", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Manila."),
    MonitorTrigger(id="disaster-indian-ocean-sri-lanka", name="Sri Lanka Disaster Alert", peril="disaster", lat=6.93, lon=79.85, location_label="Colombo, Sri Lanka", threshold=1, threshold_unit="disaster events", fires_when_above=True, data_source="gdacs", description="GDACS reports >= 1 disaster event within 500km of Colombo."),

    # ── EONET (NASA Earth Observatory Natural Event Tracker) ──
    # Covers volcanoes, dust storms, sea/lake ice, landslides — perils not in other sources
    MonitorTrigger(id="eonet-volcano-iceland", name="Iceland Volcanic Activity", peril="eonet", lat=64.13, lon=-21.90, location_label="Reykjavik, Iceland", threshold=1, threshold_unit="natural events", fires_when_above=True, data_source="nasa_eonet", description="NASA EONET detects >= 1 active natural event (volcano, ice, storm) within 500km of Iceland."),
    MonitorTrigger(id="eonet-volcano-hawaii", name="Hawaii Volcanic Activity", peril="eonet", lat=19.90, lon=-155.60, location_label="Big Island, Hawaii", threshold=1, threshold_unit="natural events", fires_when_above=True, data_source="nasa_eonet", description="NASA EONET detects >= 1 active natural event within 500km of Hawaii."),
    MonitorTrigger(id="eonet-dust-sahara", name="Sahara Dust Storm", peril="eonet", lat=23.00, lon=3.00, location_label="Central Sahara", threshold=1, threshold_unit="natural events", fires_when_above=True, data_source="nasa_eonet", description="NASA EONET detects >= 1 dust/haze event within 500km of the Sahara."),
    MonitorTrigger(id="eonet-ice-arctic", name="Arctic Sea Ice Event", peril="eonet", lat=75.00, lon=0.00, location_label="Arctic Ocean", threshold=1, threshold_unit="natural events", fires_when_above=True, data_source="nasa_eonet", description="NASA EONET detects >= 1 sea/lake ice event within 500km of the Arctic."),
    MonitorTrigger(id="eonet-volcano-indonesia", name="Indonesia Volcanic Activity", peril="eonet", lat=-7.54, lon=110.45, location_label="Central Java, Indonesia", threshold=1, threshold_unit="natural events", fires_when_above=True, data_source="nasa_eonet", description="NASA EONET detects >= 1 volcanic event within 500km of Central Java."),
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
    "flood": "Flood",
    "cyclone": "Tropical Cyclone",
    "crop": "Crop / NDVI",
    "solar": "Solar / Space Weather",
    "health": "Health / Pandemic",
    "disaster": "Disaster",
    "eonet": "Natural Events (EONET)",
}

PERIL_ICONS: dict[PerilType, str] = {
    "flight_delay": "airplane",
    "air_quality": "cloud",
    "wildfire": "fire_extinguisher",
    "drought": "water_drop",
    "extreme_weather": "thunderstorm",
    "earthquake": "globe_with_meridians",
    "marine": "anchor",
    "flood": "water_drop",
    "cyclone": "cyclone",
    "crop": "eco",
    "solar": "sunny",
    "health": "medical_services",
    "disaster": "warning",
    "eonet": "public",
}
