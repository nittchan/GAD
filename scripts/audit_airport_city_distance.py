#!/usr/bin/env python3
"""
Audit script: prints all airports where the distance from airport to city centre
exceeds 15km. Flags airports that still need city_lat/city_lon to be set.

Usage: PYTHONPATH=. python3 scripts/audit_airport_city_distance.py
       or: python3 -c "exec(open('scripts/audit_airport_city_distance.py').read())"
"""

import math
import sys
import os

# Add project root to path so gad.monitor.airports can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gad.monitor.airports import ALL_AIRPORTS  # noqa: E402


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def main():
    print(f"{'IATA':<6} {'City':<25} {'Country':<15} {'Dist(km)':>10}  {'city_lat/lon set?'}")
    print("-" * 80)

    needs_fix = []
    for a in ALL_AIRPORTS:
        if a.city_lat is not None and a.city_lon is not None:
            dist = haversine_km(a.lat, a.lon, a.city_lat, a.city_lon)
            marker = f"YES ({dist:.1f}km offset)"
        else:
            dist = 0.0
            marker = "NO (using airport coords)"

        if a.tier <= 2:
            print(f"{a.iata:<6} {a.city:<25} {a.country:<15} {dist:>10.1f}  {marker}")

        if a.tier <= 2 and a.city_lat is None:
            needs_fix.append(a)

    if needs_fix:
        print(f"\n--- {len(needs_fix)} tier 1-2 airports without city_lat/city_lon ---")
        print("These airports use runway coordinates for AQI queries.")
        print("If the airport is close to the city (<15km), this is acceptable.\n")
        for a in needs_fix:
            print(f"  {a.iata} — {a.city}, {a.country} (airport: {a.lat:.4f}, {a.lon:.4f})")
    else:
        print("\nAll tier 1-2 airports have city_lat/city_lon set.")


if __name__ == "__main__":
    main()
