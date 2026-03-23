"""
AviationStack: real flight schedule vs actual departure times.
https://aviationstack.com/documentation

Free tier: 500 requests/month (~16/day). Use for tier-1 airports only.
Falls back to OpenSky for tier-2/3 airports.
"""

from __future__ import annotations

import os

import httpx

from gad.monitor.cache import write_cache

AVIATIONSTACK_URL = "https://api.aviationstack.com/v1/flights"
TIMEOUT = 20


def fetch_departures(iata_code: str, trigger_id: str) -> dict | None:
    """
    Fetch recent departures for an airport and compute average delay.
    Uses scheduled vs actual departure times (the key advantage over OpenSky).
    """
    api_key = os.environ.get("AVIATIONSTACK_API_KEY", "")
    if not api_key:
        return None

    try:
        params = {
            "access_key": api_key,
            "dep_iata": iata_code,
            "flight_status": "landed",
            "limit": 25,
        }
        resp = httpx.get(AVIATIONSTACK_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        flights = data.get("data", [])
        if not flights:
            result = {
                "avg_delay_min": 0,
                "delayed_count": 0,
                "total_flights": 0,
                "airport": iata_code,
                "source": "aviationstack",
            }
            write_cache("flights", trigger_id, result, ttl_seconds=7200)
            return result

        delays = []
        for f in flights:
            dep = f.get("departure", {})
            scheduled = dep.get("scheduled")
            actual = dep.get("actual")
            delay_min = dep.get("delay")  # AviationStack provides delay directly

            if delay_min is not None:
                delays.append(max(0, int(delay_min)))
            elif scheduled and actual:
                # Parse and compute if delay field is missing
                try:
                    from datetime import datetime
                    fmt = "%Y-%m-%dT%H:%M:%S+00:00"
                    sched_dt = datetime.strptime(scheduled[:25], fmt[:len(scheduled[:25])])
                    actual_dt = datetime.strptime(actual[:25], fmt[:len(actual[:25])])
                    diff = (actual_dt - sched_dt).total_seconds() / 60
                    delays.append(max(0, diff))
                except (ValueError, TypeError):
                    pass

        total = len(flights)
        avg = sum(delays) / len(delays) if delays else 0
        delayed = sum(1 for d in delays if d > 15)

        result = {
            "avg_delay_min": round(avg, 1),
            "delayed_count": delayed,
            "total_flights": total,
            "airport": iata_code,
            "source": "aviationstack",
        }
        write_cache("flights", trigger_id, result, ttl_seconds=7200)  # 2h TTL
        return result

    except Exception:
        return None
