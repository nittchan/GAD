"""
Koppen climate zone lookup using lat/lon coordinates.
Simplified classification based on latitude/altitude bands.
Full Beck et al. 2018 raster deferred — this uses a rule-based approximation.
"""

KOPPEN_ZONES = {
    "Af": "Tropical rainforest",
    "Am": "Tropical monsoon",
    "Aw": "Tropical savanna",
    "BWh": "Hot desert",
    "BWk": "Cold desert",
    "BSh": "Hot semi-arid",
    "BSk": "Cold semi-arid",
    "Cfa": "Humid subtropical",
    "Cfb": "Oceanic",
    "Csa": "Mediterranean hot summer",
    "Csb": "Mediterranean warm summer",
    "Dfa": "Hot-summer humid continental",
    "Dfb": "Warm-summer humid continental",
    "Dfc": "Subarctic",
    "ET": "Tundra",
    "EF": "Ice cap",
}


def get_climate_zone(lat: float, lon: float) -> str:
    """Rule-based Koppen zone approximation from lat/lon."""
    abs_lat = abs(lat)
    if abs_lat < 15:
        return "Af" if lon > 0 and abs_lat < 10 else "Aw"
    elif abs_lat < 25:
        if -30 < lon < 60:  # Africa/Middle East
            return "BWh"
        return "BSh"
    elif abs_lat < 35:
        return "Csa" if lon > -10 and lon < 40 else "Cfa"
    elif abs_lat < 50:
        return "Cfb" if lon > -10 and lon < 30 else "Dfb"
    elif abs_lat < 60:
        return "Dfc"
    else:
        return "ET"


def get_zone_label(zone_code: str) -> str:
    """Return human-readable label for a Koppen zone code."""
    return KOPPEN_ZONES.get(zone_code, zone_code)
