#!/usr/bin/env python3
"""
Fetch 5 years of daily weather data for all 144 airports from Open-Meteo Archive API.

Open-Meteo /v1/archive is free, no API key needed. Returns daily weather data
for any lat/lon and date range.

Output: data/series/weather/{iata}_daily.csv per airport
Format: period, index_value, loss_proxy, loss_event, temperature_max, temperature_min,
        windspeed_max, precipitation_sum

The loss_proxy is derived from the trigger threshold:
  - Heat triggers (fires_when_above=True): loss_event=1 when temp_max >= threshold
  - Freeze triggers (fires_when_above=False): loss_event=1 when temp_min <= threshold

Usage:
    python3 scripts/fetch_historical_openmeteo.py
    python3 scripts/fetch_historical_openmeteo.py --airports DEL,BLR,JFK  # subset
    python3 scripts/fetch_historical_openmeteo.py --years 3               # 3 years instead of 5

Respects a 1-second delay between calls. ~144 calls total, ~3 minutes.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gad.monitor.airports import ALL_AIRPORTS  # noqa: E402
from gad.monitor.triggers import GLOBAL_TRIGGERS  # noqa: E402

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "series" / "weather"
TIMEOUT = 30


def _get_weather_trigger(iata: str) -> dict | None:
    """Find the weather trigger for an airport and return its threshold info."""
    iata_lower = iata.lower()
    for t in GLOBAL_TRIGGERS:
        if t.peril == "extreme_weather" and t.id.endswith(f"-{iata_lower}"):
            return {
                "trigger_id": t.id,
                "threshold": t.threshold,
                "fires_when_above": t.fires_when_above,
                "threshold_unit": t.threshold_unit,
            }
    return None


def fetch_airport_weather(
    iata: str,
    lat: float,
    lon: float,
    years: int = 5,
    trigger_info: dict | None = None,
) -> list[dict]:
    """
    Fetch daily weather data from Open-Meteo Archive API.
    Returns list of daily records.
    """
    end_date = date.today() - timedelta(days=5)  # archive has ~5 day lag
    start_date = end_date - timedelta(days=365 * years)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,windspeed_10m_max,precipitation_sum",
        "timezone": "UTC",
    }

    resp = httpx.get(ARCHIVE_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temp_max = daily.get("temperature_2m_max", [])
    temp_min = daily.get("temperature_2m_min", [])
    wind_max = daily.get("windspeed_10m_max", [])
    precip = daily.get("precipitation_sum", [])

    if not dates:
        return []

    # Determine which metric is the index_value based on trigger type
    threshold = trigger_info["threshold"] if trigger_info else 40
    fires_above = trigger_info["fires_when_above"] if trigger_info else True

    records = []
    for i, d in enumerate(dates):
        t_max = temp_max[i] if i < len(temp_max) else None
        t_min = temp_min[i] if i < len(temp_min) else None
        w_max = wind_max[i] if i < len(wind_max) else None
        p_sum = precip[i] if i < len(precip) else None

        # Skip days with missing temperature data
        if t_max is None and t_min is None:
            continue

        # index_value: the metric being compared to threshold
        if fires_above:
            index_val = t_max if t_max is not None else 0
        else:
            index_val = t_min if t_min is not None else 0

        # loss_event: did the actual value cross the threshold?
        if fires_above:
            loss_event = 1 if (t_max is not None and t_max >= threshold) else 0
        else:
            loss_event = 1 if (t_min is not None and t_min <= threshold) else 0

        loss_proxy = float(loss_event)

        records.append({
            "period": d,
            "index_value": round(index_val, 1),
            "loss_proxy": loss_proxy,
            "loss_event": loss_event,
            "temperature_max": round(t_max, 1) if t_max is not None else "",
            "temperature_min": round(t_min, 1) if t_min is not None else "",
            "windspeed_max": round(w_max, 1) if w_max is not None else "",
            "precipitation_sum": round(p_sum, 1) if p_sum is not None else "",
        })

    return records


def write_csv(iata: str, records: list[dict]) -> Path:
    """Write records to CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{iata.upper()}_daily.csv"

    fieldnames = [
        "period", "index_value", "loss_proxy", "loss_event",
        "temperature_max", "temperature_min", "windspeed_max", "precipitation_sum",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return path


def _fetch_with_retry(
    iata: str, lat: float, lon: float, years: int,
    trigger_info: dict | None, max_retries: int = 3, base_delay: float = 2.0,
) -> list[dict]:
    """Fetch with exponential backoff on failure."""
    for attempt in range(max_retries):
        try:
            return fetch_airport_weather(iata, lat, lon, years=years, trigger_info=trigger_info)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                print(f"    retry {attempt + 1}/{max_retries} in {wait:.0f}s ({e})")
                time.sleep(wait)
            else:
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch historical weather data from Open-Meteo")
    parser.add_argument("--airports", type=str, help="Comma-separated IATA codes (default: all)")
    parser.add_argument("--years", type=int, default=5, help="Years of history (default: 5)")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between API calls in seconds")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if CSV already exists")
    args = parser.parse_args()

    airports = ALL_AIRPORTS
    if args.airports:
        codes = {c.strip().upper() for c in args.airports.split(",")}
        airports = [a for a in ALL_AIRPORTS if a.iata in codes]
        if not airports:
            print(f"ERROR: No airports found for codes: {args.airports}")
            sys.exit(1)

    print(f"Fetching {args.years}yr weather history for {len(airports)} airports...")
    print(f"Output: {OUTPUT_DIR}/")
    print()

    success = 0
    skipped = 0
    errors = 0

    for i, airport in enumerate(airports):
        # Skip if CSV already exists (unless --force)
        csv_path = OUTPUT_DIR / f"{airport.iata.upper()}_daily.csv"
        if csv_path.exists() and not args.force:
            skipped += 1
            continue

        trigger_info = _get_weather_trigger(airport.iata)
        trigger_label = f"threshold={trigger_info['threshold']}°C" if trigger_info else "no trigger"

        try:
            records = _fetch_with_retry(
                airport.iata, airport.lat, airport.lon,
                years=args.years, trigger_info=trigger_info,
            )

            if records:
                path = write_csv(airport.iata, records)
                success += 1
                print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: {len(records)} days -> {path.name} ({trigger_label})")
            else:
                errors += 1
                print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: no data returned")

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: ERROR — {e}")

        if i < len(airports) - 1:
            time.sleep(args.delay)

    print(f"\nDone: {success} fetched, {skipped} skipped (already exist), {errors} errors")
    print(f"Files at: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
