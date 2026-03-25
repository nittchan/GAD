"""
FAA ATCSCC (Air Traffic Control System Command Center) Airport Status API.
https://soa.smext.faa.gov/asws/api/airport/status/{code}

Free, no API key. Returns real delay data for US airports:
- Departure delays (minutes + reason)
- Arrival delays (minutes + reason)
- Ground delays / ground stops
- Closure status

This is the authoritative source for US airport delays — real delay
minutes, not departure counts.
"""

from __future__ import annotations

import logging

import httpx

from gad.monitor.cache import write_cache

log = logging.getLogger("gad.monitor.sources.faa_atcscc")

FAA_ASWS_URL = "https://soa.smext.faa.gov/asws/api/airport/status/{code}"
TIMEOUT = 15


def fetch_airport_status(iata_code: str, trigger_id: str) -> dict | None:
    """
    Fetch real-time airport delay status from FAA ATCSCC.

    Returns dict with: avg_delay_min, delay_type, delay_reason,
    ground_delay, ground_stop, closure, total_delays, source.
    """
    try:
        url = FAA_ASWS_URL.format(code=iata_code)
        resp = httpx.get(url, timeout=TIMEOUT)

        if resp.status_code == 404:
            # Airport not in FAA system
            return None

        resp.raise_for_status()
        data = resp.json()

        # Parse delay information
        status = data.get("Status", [])
        delays = []
        max_delay_min = 0
        delay_reasons = []
        has_ground_delay = False
        has_ground_stop = False
        has_closure = False

        for s in status if isinstance(status, list) else [status]:
            if not isinstance(s, dict):
                continue

            reason = s.get("Reason", "")
            delay_type = s.get("Type", "")

            # Ground delay program
            if "Ground Delay" in delay_type or "GDP" in delay_type:
                has_ground_delay = True
                avg_min = _parse_delay_minutes(s.get("AvgDelay", ""))
                if avg_min > max_delay_min:
                    max_delay_min = avg_min

            # Ground stop
            if "Ground Stop" in delay_type or "GS" in str(s):
                has_ground_stop = True
                max_delay_min = max(max_delay_min, 60)  # Ground stop = at least 60 min

            # Closure
            if "Clos" in delay_type:
                has_closure = True
                max_delay_min = max(max_delay_min, 120)

            # Departure/arrival delays
            if "Departure" in delay_type or "Arrival" in delay_type:
                avg_min = _parse_delay_minutes(s.get("AvgDelay", s.get("Avg", "")))
                if avg_min > 0:
                    delays.append(avg_min)
                    if avg_min > max_delay_min:
                        max_delay_min = avg_min

            if reason:
                delay_reasons.append(reason)

        # Also check top-level delay fields
        if not delays and not has_ground_delay and not has_ground_stop:
            # Check for delay property at top level
            delay_flag = data.get("Delay", False)
            if isinstance(delay_flag, str):
                delay_flag = delay_flag.lower() == "true"
            if not delay_flag:
                # No delays — airport operating normally
                result = {
                    "avg_delay_min": 0,
                    "total_flights": 0,
                    "delayed_count": 0,
                    "delay_type": "none",
                    "delay_reason": "",
                    "ground_delay": False,
                    "ground_stop": False,
                    "closure": False,
                    "total_delays": 0,
                    "airport": iata_code,
                    "source": "faa_atcscc",
                }
                write_cache("flights", trigger_id, result, ttl_seconds=900)  # 15min TTL
                return result

        avg_delay = max_delay_min if max_delay_min > 0 else (sum(delays) / len(delays) if delays else 0)

        result = {
            "avg_delay_min": round(avg_delay, 1),
            "total_flights": len(delays),
            "delayed_count": sum(1 for d in delays if d > 15),
            "delay_type": "ground_stop" if has_ground_stop else "ground_delay" if has_ground_delay else "departure" if delays else "none",
            "delay_reason": "; ".join(delay_reasons[:3]) if delay_reasons else "",
            "ground_delay": has_ground_delay,
            "ground_stop": has_ground_stop,
            "closure": has_closure,
            "total_delays": len(delays),
            "airport": iata_code,
            "source": "faa_atcscc",
        }

        write_cache("flights", trigger_id, result, ttl_seconds=900)  # 15min TTL — FAA updates frequently
        return result

    except Exception as e:
        log.warning(f"FAA ATCSCC fetch failed for {iata_code}: {e}")
        return None


def _parse_delay_minutes(delay_str) -> float:
    """Parse delay string like '45 minutes' or '1 hour 15 minutes' into minutes."""
    if not delay_str:
        return 0
    delay_str = str(delay_str).lower().strip()
    minutes = 0
    try:
        if "hour" in delay_str:
            parts = delay_str.split("hour")
            hours = float(parts[0].strip())
            minutes = hours * 60
            if len(parts) > 1 and "min" in parts[1]:
                min_part = parts[1].replace("minutes", "").replace("minute", "").replace("min", "").strip()
                if min_part:
                    minutes += float(min_part)
        elif "min" in delay_str:
            min_part = delay_str.replace("minutes", "").replace("minute", "").replace("min", "").strip()
            if min_part:
                minutes = float(min_part)
        else:
            # Try direct number
            minutes = float(delay_str)
    except (ValueError, TypeError):
        pass
    return minutes


def evaluate_trigger(data: dict, threshold: float) -> dict:
    """Evaluate a flight delay trigger using FAA data."""
    source = data.get("source", "faa_atcscc")
    avg_delay = data.get("avg_delay_min", 0) or 0

    if data.get("ground_stop"):
        return {
            "fired": True,
            "value": avg_delay,
            "threshold": threshold,
            "unit": "min (GROUND STOP)",
            "status": "critical",
            "delay_reason": data.get("delay_reason", ""),
            "metric": "avg_delay",
        }

    if data.get("closure"):
        return {
            "fired": True,
            "value": avg_delay,
            "threshold": threshold,
            "unit": "min (CLOSED)",
            "status": "critical",
            "delay_reason": data.get("delay_reason", ""),
            "metric": "avg_delay",
        }

    fired = avg_delay >= threshold
    return {
        "fired": fired,
        "value": round(avg_delay, 1),
        "threshold": threshold,
        "unit": "min avg delay",
        "status": "critical" if fired else "normal",
        "delay_reason": data.get("delay_reason", ""),
        "metric": "avg_delay",
    }
