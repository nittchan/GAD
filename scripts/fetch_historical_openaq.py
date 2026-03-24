#!/usr/bin/env python3
"""
Fetch 2 years of daily AQI data for all tier 1-2 airports from OpenAQ.

Strategy:
1. Find nearest PM2.5 monitoring station per city (using city_lat/city_lon)
2. Download daily average PM2.5 from that station
3. Convert PM2.5 to AQI using EPA breakpoints
4. Output CSV compatible with load_weather_data_from_csv

OpenAQ v2 API: https://docs.openaq.org/
Rate limit: conservative 1 req/sec. API key recommended but not required.

Output: data/series/aqi/{IATA}_aqi_daily.csv
Format: period, index_value, loss_proxy, loss_event

Usage:
    python3 scripts/fetch_historical_openaq.py
    python3 scripts/fetch_historical_openaq.py --airports DEL,BLR  # subset
    python3 scripts/fetch_historical_openaq.py --years 1           # 1 year
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from gad.monitor.airports import ALL_AIRPORTS  # noqa: E402

OPENAQ_URL = "https://api.openaq.org/v3"
TIMEOUT = 20
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "series" / "aqi"
AQI_THRESHOLD = 150  # AQI triggers fire at 150 (unhealthy)


def _headers() -> dict:
    api_key = os.environ.get("OPENAQ_API_KEY", "")
    if api_key:
        return {"X-API-Key": api_key}
    return {}


def _pm25_to_aqi(pm25: float) -> int:
    """EPA PM2.5 to AQI conversion."""
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            return round(((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo)
    return 500 if pm25 > 500 else 0


def find_nearest_station(lat: float, lon: float, radius_km: int = 25) -> dict | None:
    """Find the nearest PM2.5 monitoring station via OpenAQ v3 locations.
    Prefers stations with recent data (datetimeLast within last 90 days)."""
    try:
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": radius_km * 1000,  # meters
            "limit": 20,
        }
        resp = httpx.get(
            f"{OPENAQ_URL}/locations",
            params=params,
            headers=_headers(),
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

        from datetime import datetime, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        # Collect all PM2.5 sensors, then probe the best ones for actual day counts
        pm25_sensors = []
        for loc in results:
            sensors = loc.get("sensors", [])
            for sensor in sensors:
                param = sensor.get("parameter", {})
                if param.get("name") == "pm25":
                    pm25_sensors.append({
                        "location_id": loc.get("id"),
                        "sensor_id": sensor.get("id"),
                        "name": loc.get("name"),
                        "coordinates": loc.get("coordinates", {}),
                    })

        if not pm25_sensors:
            return None

        # Probe each sensor's /days endpoint to find the one with most recent data
        best = None
        best_score = 0  # score = recency + coverage

        for s in pm25_sensors[:8]:  # limit probes to first 8 candidates
            try:
                time.sleep(0.3)
                probe = httpx.get(
                    f"{OPENAQ_URL}/sensors/{s['sensor_id']}/days",
                    params={"limit": 1000},
                    headers=_headers(),
                    timeout=TIMEOUT,
                )
                if probe.status_code != 200:
                    continue
                days = probe.json().get("results", [])
                if not days:
                    continue

                # Check last day date
                last_day_dt = (days[-1].get("period", {}).get("datetimeFrom") or {})
                last_local = last_day_dt.get("local", "") if isinstance(last_day_dt, dict) else ""
                if not last_local:
                    continue

                try:
                    last_date = date.fromisoformat(last_local[:10])
                except ValueError:
                    continue

                if last_date < (date.today() - timedelta(days=90)):
                    continue  # skip sensors that stopped reporting

                day_count = len(days)
                # Score: prefer more days of recent data
                recency_days = (date.today() - last_date).days
                score = day_count * 1000 - recency_days

                if score > best_score:
                    best_score = score
                    best = {
                        **s,
                        "pm25_count": day_count,
                        "last_date": last_local[:10],
                    }

            except Exception:
                continue

        return best

    except Exception as e:
        print(f"    Station lookup error: {e}")
        return None


def fetch_daily_pm25(sensor_id: int, years: int = 2) -> list[dict]:
    """
    Fetch daily average PM2.5 from OpenAQ v3 sensors/{id}/days endpoint.
    The v3 API returns daily aggregates chronologically from the earliest data.
    We page through until we have records within our target date range.
    """
    target_start = date.today() - timedelta(days=365 * years)
    target_end = date.today()

    daily = []
    page = 1
    max_pages = 20  # ~20k days max = ~55 years, more than enough

    while page <= max_pages:
        try:
            resp = httpx.get(
                f"{OPENAQ_URL}/sensors/{sensor_id}/days",
                params={"limit": 1000, "page": page},
                headers=_headers(),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            if not results:
                break

            for r in results:
                summary = r.get("summary") or {}
                avg = summary.get("avg")
                if avg is None:
                    continue
                try:
                    avg = float(avg)
                except (TypeError, ValueError):
                    continue
                if avg < 0:
                    continue

                period = r.get("period", {})
                dt_from = period.get("datetimeFrom") or {}
                dt_local = dt_from.get("local", "") if isinstance(dt_from, dict) else ""
                if not dt_local:
                    continue
                day_str = dt_local[:10]

                try:
                    day_date = date.fromisoformat(day_str)
                except ValueError:
                    continue

                if day_date < target_start:
                    continue  # skip dates before our range
                if day_date > target_end:
                    continue

                aqi = _pm25_to_aqi(avg)
                daily.append({
                    "period": day_str,
                    "pm25_avg": round(avg, 1),
                    "aqi": aqi,
                })

            # If the last result is past our target end, stop
            if results:
                last_dt = (results[-1].get("period", {}).get("datetimeFrom") or {})
                last_local = last_dt.get("local", "") if isinstance(last_dt, dict) else ""
                if last_local and last_local[:10] >= target_end.isoformat():
                    break

            if len(results) < 1000:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"    Days page {page} error: {e}")
            break

    # Sort by date and deduplicate
    seen = set()
    unique = []
    for d in sorted(daily, key=lambda x: x["period"]):
        if d["period"] not in seen:
            seen.add(d["period"])
            unique.append(d)

    return unique


def write_csv(iata: str, records: list[dict]) -> Path:
    """Write AQI records to CSV in engine-compatible format."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{iata.upper()}_aqi_daily.csv"

    fieldnames = ["period", "index_value", "loss_proxy", "loss_event", "pm25_avg", "aqi"]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "period": r["period"],
                "index_value": r["aqi"],  # AQI as the trigger index
                "loss_proxy": 1.0 if r["aqi"] >= AQI_THRESHOLD else 0.0,
                "loss_event": 1 if r["aqi"] >= AQI_THRESHOLD else 0,
                "pm25_avg": r["pm25_avg"],
                "aqi": r["aqi"],
            })

    return path


def _fetch_with_retry(
    sensor_id: int, years: int, max_retries: int = 3, base_delay: float = 3.0,
) -> list[dict]:
    """Fetch with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fetch_daily_pm25(sensor_id, years=years)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                print(f"    retry {attempt + 1}/{max_retries} in {wait:.0f}s ({e})")
                time.sleep(wait)
            else:
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch historical AQI data from OpenAQ")
    parser.add_argument("--airports", type=str, help="Comma-separated IATA codes (default: all tier 1-2)")
    parser.add_argument("--years", type=int, default=2, help="Years of history (default: 2)")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between airports in seconds")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if CSV already exists")
    parser.add_argument("--radius", type=int, default=25, help="Station search radius in km (default: 25)")
    args = parser.parse_args()

    # Only tier 1-2 airports have AQI triggers
    airports = [a for a in ALL_AIRPORTS if a.tier <= 2]
    if args.airports:
        codes = {c.strip().upper() for c in args.airports.split(",")}
        airports = [a for a in airports if a.iata in codes]
        if not airports:
            print(f"ERROR: No tier 1-2 airports found for codes: {args.airports}")
            sys.exit(1)

    print(f"Fetching {args.years}yr AQI history for {len(airports)} airports...")
    print(f"Output: {OUTPUT_DIR}/")
    if os.environ.get("OPENAQ_API_KEY"):
        print("OpenAQ API key: configured")
    else:
        print("OpenAQ API key: NOT SET (may be rate-limited)")
    print()

    success = 0
    skipped = 0
    no_station = 0
    errors = 0
    station_log = []

    for i, airport in enumerate(airports):
        csv_path = OUTPUT_DIR / f"{airport.iata.upper()}_aqi_daily.csv"
        if csv_path.exists() and not args.force:
            skipped += 1
            continue

        # Use city coordinates for station lookup (BUG-01 fix)
        city_lat = airport.effective_city_lat
        city_lon = airport.effective_city_lon

        try:
            # Step 1: Find nearest PM2.5 station
            station = find_nearest_station(city_lat, city_lon, radius_km=args.radius)
            if not station:
                no_station += 1
                print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: no PM2.5 station within {args.radius}km")
                station_log.append(f"{airport.iata},{airport.city},{city_lat},{city_lon},NO_STATION")
                time.sleep(args.delay)
                continue

            station_name = station["name"]
            sensor_id = station["sensor_id"]
            print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: station={station_name} (sensor={sensor_id}, {station['pm25_count']} measurements)")

            # Step 2: Fetch daily PM2.5
            time.sleep(args.delay)
            records = _fetch_with_retry(sensor_id, years=args.years)

            if records:
                path = write_csv(airport.iata, records)
                success += 1
                high_days = sum(1 for r in records if r["aqi"] >= AQI_THRESHOLD)
                print(f"           -> {len(records)} days, {high_days} days AQI>=150 -> {path.name}")
                station_log.append(f"{airport.iata},{airport.city},{city_lat},{city_lon},{station_name},{sensor_id},{len(records)}")
            else:
                errors += 1
                print(f"           -> no measurement data returned")
                station_log.append(f"{airport.iata},{airport.city},{city_lat},{city_lon},{station_name},{sensor_id},0")

        except Exception as e:
            errors += 1
            print(f"  [{i+1}/{len(airports)}] {airport.iata} {airport.city}: ERROR — {e}")

        time.sleep(args.delay)

    print(f"\nDone: {success} fetched, {skipped} skipped, {no_station} no station, {errors} errors")
    print(f"Files at: {OUTPUT_DIR}/")

    # Write station mapping log for audit
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUTPUT_DIR / "_station_mapping.csv"
    with open(log_path, "w") as f:
        f.write("iata,city,city_lat,city_lon,station_name,location_id,days\n")
        for line in station_log:
            f.write(line + "\n")
    print(f"Station mapping: {log_path}")


if __name__ == "__main__":
    main()
