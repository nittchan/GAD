#!/usr/bin/env python3
"""
Fetch / process European airport delay data from Eurocontrol ANS Performance data.

Data source: Eurocontrol ANS Performance Review
  - Portal:  https://ansperformance.eu/data/
  - API:     https://ansperformance.eu/api/
  - Data includes: date, airport ICAO code, average departure delay, number of
    flights, delay causes.  Free but requires registration for bulk download.

─────────────────────────────────────────────────────────────────────────────────
HOW TO USE
─────────────────────────────────────────────────────────────────────────────────

OPTION A — Process a manually downloaded CSV:
  1. Go to https://ansperformance.eu/data/  →  "Airport arrival ATFM delays"
     or https://ansperformance.eu/download/  →  download the airport-level
     daily dataset (CSV or XLSX).
  2. Save the file as  data/eurocontrol_raw/airport_delays.csv
  3. Run:
       python3 scripts/fetch_eurocontrol.py --mode csv \
           --input data/eurocontrol_raw/airport_delays.csv

OPTION B — Try the Eurocontrol API (requires a registered token):
  1. Register at https://ansperformance.eu/  →  get an API token.
  2. Set env var: export EUROCONTROL_API_TOKEN=<your-token>
  3. Run:
       python3 scripts/fetch_eurocontrol.py --mode api

OPTION C — Generate synthetic delay data from Open-Meteo weather (fallback):
  Uses historical weather at each airport as a delay proxy — airports with
  more precipitation / wind / extreme temps get higher "delay" values.
  No API key required.
       python3 scripts/fetch_eurocontrol.py --mode weather-proxy
       python3 scripts/fetch_eurocontrol.py --mode weather-proxy --years 3

All modes output: data/series/flights/{IATA}_daily.csv
Columns: period, index_value, loss_proxy, loss_event, avg_delay_min, total_flights

─────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gad.monitor.airports import ALL_AIRPORTS, Airport  # noqa: E402
from gad.config import SERIES_DIR  # noqa: E402

OUTPUT_DIR = SERIES_DIR / "flights"
TIMEOUT = 30

# ──────────────────────────────────────────────────────────────
# European airports from GAD registry
# ──────────────────────────────────────────────────────────────
EUROPEAN_IATA_CODES = {
    "LHR", "LGW", "CDG", "FRA", "AMS", "MAD", "BCN", "FCO", "MXP",
    "MUC", "ZRH", "CPH", "ARN", "HEL", "OSL", "DUB", "LIS", "VIE",
    "WAW", "PRG", "BUD", "ATH", "OTP", "SVO", "IST",
}

# IATA → ICAO mapping for European airports (from airports.py registry)
IATA_TO_ICAO: dict[str, str] = {}
EUROPEAN_AIRPORTS: list[Airport] = []

for _a in ALL_AIRPORTS:
    if _a.iata in EUROPEAN_IATA_CODES:
        IATA_TO_ICAO[_a.iata] = _a.icao
        EUROPEAN_AIRPORTS.append(_a)

ICAO_TO_IATA = {v: k for k, v in IATA_TO_ICAO.items()}

# Delay thresholds (minutes) — consistent with GAD trigger definitions
# Tier 1 airports use 45 min, others 60 min (from triggers.py)
# For loss_proxy: southern-latitude airports use 42 min, mid-latitude use 40 min
SOUTHERN_AIRPORTS = {"ATH", "LIS", "BCN", "FCO", "MXP", "IST", "OTP"}


def _get_delay_threshold(iata: str) -> float:
    """Return the loss_proxy threshold for an airport.

    Southern-latitude airports: 42 min; mid-latitude: 40 min.
    """
    return 42.0 if iata in SOUTHERN_AIRPORTS else 40.0


def _compute_loss_fields(
    avg_delay: float, iata: str,
) -> tuple[float, int]:
    """Compute loss_proxy and loss_event from average delay."""
    threshold = _get_delay_threshold(iata)
    loss_event = 1 if avg_delay >= threshold else 0
    loss_proxy = float(loss_event)
    return loss_proxy, loss_event


# ──────────────────────────────────────────────────────────────
# MODE A: Process manually downloaded Eurocontrol CSV
# ──────────────────────────────────────────────────────────────

# Eurocontrol CSVs use various column names. We try multiple variants.
_DATE_COLS = ["DATE", "FLT_DATE", "date", "Date", "ENTRY_DATE"]
_ICAO_COLS = ["APT_ICAO", "AIRPORT", "airport", "Airport", "ADEP"]
_DELAY_COLS = ["AVG_ARR_ATFM_DELAY", "AVG_DEP_DELAY", "AVG_DELAY",
               "avg_dep_delay_min", "avg_delay", "DLY_APT_ARR_1"]
_FLIGHTS_COLS = ["FLT_ARR_1", "FLT_DEP_1", "TOTAL_FLIGHTS",
                 "total_flights", "NB_FLIGHTS", "FLT_TOT_1"]


def _find_col(header: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column name from candidates."""
    header_lower = [h.strip().lower() for h in header]
    for c in candidates:
        if c.lower() in header_lower:
            idx = header_lower.index(c.lower())
            return header[idx]
    return None


def process_eurocontrol_csv(csv_path: Path) -> dict[str, list[dict]]:
    """Parse a Eurocontrol CSV and return {iata: [records]} for European airports."""
    results: dict[str, list[dict]] = {}

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []

        date_col = _find_col(header, _DATE_COLS)
        icao_col = _find_col(header, _ICAO_COLS)
        delay_col = _find_col(header, _DELAY_COLS)
        flights_col = _find_col(header, _FLIGHTS_COLS)

        if not date_col:
            print(f"ERROR: No date column found. Available: {header}")
            print(f"  Expected one of: {_DATE_COLS}")
            sys.exit(1)
        if not icao_col:
            print(f"ERROR: No airport ICAO column found. Available: {header}")
            print(f"  Expected one of: {_ICAO_COLS}")
            sys.exit(1)
        if not delay_col:
            print(f"ERROR: No delay column found. Available: {header}")
            print(f"  Expected one of: {_DELAY_COLS}")
            sys.exit(1)

        print(f"Detected columns — date: {date_col}, airport: {icao_col}, "
              f"delay: {delay_col}, flights: {flights_col or '(not found)'}")

        row_count = 0
        matched = 0
        for row in reader:
            row_count += 1
            icao = row.get(icao_col, "").strip().upper()
            iata = ICAO_TO_IATA.get(icao)
            if not iata:
                continue

            matched += 1
            period = row.get(date_col, "").strip()
            # Normalize date formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
            if "/" in period:
                parts = period.split("/")
                if len(parts[0]) == 4:  # YYYY/MM/DD
                    period = f"{parts[0]}-{parts[1]}-{parts[2]}"
                else:  # DD/MM/YYYY
                    period = f"{parts[2]}-{parts[1]}-{parts[0]}"
            elif "-" in period and len(period.split("-")[0]) != 4:
                parts = period.split("-")
                period = f"{parts[2]}-{parts[1]}-{parts[0]}"

            try:
                avg_delay = float(row.get(delay_col, "0") or "0")
            except ValueError:
                avg_delay = 0.0

            try:
                total_flights = int(float(row.get(flights_col, "0") or "0")) if flights_col else 0
            except ValueError:
                total_flights = 0

            loss_proxy, loss_event = _compute_loss_fields(avg_delay, iata)

            if iata not in results:
                results[iata] = []

            results[iata].append({
                "period": period,
                "index_value": round(avg_delay, 1),
                "loss_proxy": loss_proxy,
                "loss_event": loss_event,
                "avg_delay_min": round(avg_delay, 1),
                "total_flights": total_flights,
            })

        print(f"Parsed {row_count} rows, {matched} matched European airports, "
              f"{len(results)} airports found.")

    # Sort each airport's records by date
    for iata in results:
        results[iata].sort(key=lambda r: r["period"])

    return results


# ──────────────────────────────────────────────────────────────
# MODE B: Eurocontrol API
# ──────────────────────────────────────────────────────────────

EUROCONTROL_API_BASE = "https://ansperformance.eu/api"


def fetch_eurocontrol_api(
    token: str, years: int = 3,
) -> dict[str, list[dict]]:
    """Fetch delay data from Eurocontrol API for all European airports."""
    results: dict[str, list[dict]] = {}

    end_date = date.today() - timedelta(days=2)
    start_date = end_date - timedelta(days=365 * years)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    for airport in EUROPEAN_AIRPORTS:
        icao = airport.icao
        iata = airport.iata

        print(f"  Fetching {iata} ({icao}) ...")

        # Try the airport ATFM delay endpoint
        # Eurocontrol API endpoints may vary; this is the best-known pattern.
        try:
            url = f"{EUROCONTROL_API_BASE}/airport/{icao}/delays"
            params = {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            }
            resp = httpx.get(url, headers=headers, params=params, timeout=TIMEOUT)

            if resp.status_code == 401:
                print(f"  ERROR: Authentication failed. Check EUROCONTROL_API_TOKEN.")
                sys.exit(1)
            elif resp.status_code == 404:
                print(f"    {iata}: endpoint not found, trying alternative ...")
                # Try alternative endpoint pattern
                url = f"{EUROCONTROL_API_BASE}/v1/airport-delays"
                params["airport"] = icao
                resp = httpx.get(url, headers=headers, params=params, timeout=TIMEOUT)

            if resp.status_code != 200:
                print(f"    {iata}: HTTP {resp.status_code}, skipping")
                time.sleep(1)
                continue

            data = resp.json()

            # Parse response — adapt to actual Eurocontrol API structure
            records = []
            entries = data if isinstance(data, list) else data.get("data", data.get("results", []))
            for entry in entries:
                period = entry.get("date", entry.get("flt_date", ""))
                avg_delay = float(entry.get("avg_dep_delay", entry.get("avg_delay", 0)))
                total_flights = int(entry.get("total_flights", entry.get("nb_flights", 0)))

                loss_proxy, loss_event = _compute_loss_fields(avg_delay, iata)

                records.append({
                    "period": period,
                    "index_value": round(avg_delay, 1),
                    "loss_proxy": loss_proxy,
                    "loss_event": loss_event,
                    "avg_delay_min": round(avg_delay, 1),
                    "total_flights": total_flights,
                })

            if records:
                records.sort(key=lambda r: r["period"])
                results[iata] = records
                print(f"    {iata}: {len(records)} days fetched")
            else:
                print(f"    {iata}: no records returned")

        except Exception as e:
            print(f"    {iata}: ERROR — {e}")

        time.sleep(1)  # Rate limit

    return results


# ──────────────────────────────────────────────────────────────
# MODE C: Weather-proxy fallback (Open-Meteo historical weather)
# ──────────────────────────────────────────────────────────────

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def _weather_to_delay_proxy(
    temp_max: float | None,
    temp_min: float | None,
    precip: float | None,
    wind_max: float | None,
) -> tuple[float, int]:
    """Convert weather conditions into a synthetic delay estimate (minutes).

    This is a heuristic proxy — NOT real delay data. It models the well-known
    relationship between adverse weather and flight delays:
      - Precipitation > 10mm      → +15-30 min delay
      - Wind > 40 km/h            → +10-25 min delay
      - Extreme cold (< -10°C)    → +8-15 min (de-icing)
      - Extreme heat (> 38°C)     → +5-10 min (runway limits)
      - Base delay                 → 8-12 min (normal ops)

    Returns (avg_delay_minutes, estimated_flight_count).
    """
    base_delay = 10.0  # Typical European airport base delay
    flight_count = 450  # Rough average daily departures for major EU airports

    delay = base_delay

    # Precipitation impact
    if precip is not None and precip > 0:
        if precip > 20:
            delay += 25 + min(precip - 20, 20)  # Heavy rain/snow
            flight_count = max(200, flight_count - 150)
        elif precip > 10:
            delay += 15 + (precip - 10)
            flight_count = max(300, flight_count - 80)
        elif precip > 2:
            delay += 5 + (precip - 2) * 0.8
        else:
            delay += precip * 1.5

    # Wind impact
    if wind_max is not None:
        if wind_max > 60:
            delay += 30 + min((wind_max - 60) * 0.5, 30)
            flight_count = max(100, flight_count - 250)
        elif wind_max > 40:
            delay += 12 + (wind_max - 40) * 0.6
            flight_count = max(250, flight_count - 100)
        elif wind_max > 25:
            delay += (wind_max - 25) * 0.3

    # Temperature extremes
    if temp_min is not None and temp_min < -10:
        delay += 8 + min(abs(temp_min + 10) * 0.5, 12)  # De-icing delays
        flight_count = max(200, flight_count - 80)
    if temp_max is not None and temp_max > 38:
        delay += 5 + min((temp_max - 38) * 1.5, 10)

    # Add small noise-like variation based on day hash (deterministic)
    delay = max(0, delay)
    flight_count = max(50, flight_count)

    return round(delay, 1), flight_count


def fetch_weather_proxy(years: int = 3) -> dict[str, list[dict]]:
    """Generate synthetic delay data from Open-Meteo historical weather."""
    results: dict[str, list[dict]] = {}

    end_date = date.today() - timedelta(days=5)
    start_date = end_date - timedelta(days=365 * years)

    for i, airport in enumerate(EUROPEAN_AIRPORTS):
        iata = airport.iata
        print(f"  [{i+1}/{len(EUROPEAN_AIRPORTS)}] {iata} ({airport.city}) ...")

        try:
            params = {
                "latitude": airport.lat,
                "longitude": airport.lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "windspeed_10m_max,precipitation_sum",
                "timezone": "UTC",
            }
            resp = httpx.get(OPEN_METEO_ARCHIVE, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            temp_max = daily.get("temperature_2m_max", [])
            temp_min = daily.get("temperature_2m_min", [])
            wind_max = daily.get("windspeed_10m_max", [])
            precip = daily.get("precipitation_sum", [])

            if not dates:
                print(f"    {iata}: no data returned")
                continue

            records = []
            for j, d in enumerate(dates):
                t_max = temp_max[j] if j < len(temp_max) else None
                t_min = temp_min[j] if j < len(temp_min) else None
                w_max = wind_max[j] if j < len(wind_max) else None
                p_sum = precip[j] if j < len(precip) else None

                avg_delay, flight_count = _weather_to_delay_proxy(
                    t_max, t_min, p_sum, w_max,
                )

                # Add day-of-week variation (deterministic)
                # Weekdays are busier, weekends slightly less delay
                dt = datetime.strptime(d, "%Y-%m-%d")
                dow = dt.weekday()
                if dow >= 5:  # Weekend
                    flight_count = int(flight_count * 0.7)
                    avg_delay = avg_delay * 0.85
                elif dow in (0, 4):  # Mon/Fri — peak travel
                    flight_count = int(flight_count * 1.15)
                    avg_delay = avg_delay * 1.1

                # Seasonal variation: summer months busier
                month = dt.month
                if month in (6, 7, 8):
                    flight_count = int(flight_count * 1.2)
                elif month in (1, 2, 11, 12):
                    flight_count = int(flight_count * 0.85)

                # Tier-based scaling (hub airports have more flights)
                tier_multiplier = {1: 1.0, 2: 0.6, 3: 0.35}
                flight_count = int(flight_count * tier_multiplier.get(airport.tier, 0.5))

                avg_delay = round(avg_delay, 1)
                loss_proxy, loss_event = _compute_loss_fields(avg_delay, iata)

                records.append({
                    "period": d,
                    "index_value": avg_delay,
                    "loss_proxy": loss_proxy,
                    "loss_event": loss_event,
                    "avg_delay_min": avg_delay,
                    "total_flights": flight_count,
                })

            results[iata] = records
            print(f"    {iata}: {len(records)} days generated")

        except Exception as e:
            print(f"    {iata}: ERROR — {e}")

        if i < len(EUROPEAN_AIRPORTS) - 1:
            time.sleep(1.5)  # Rate limit for Open-Meteo

    return results


# ──────────────────────────────────────────────────────────────
# CSV output
# ──────────────────────────────────────────────────────────────

FIELDNAMES = [
    "period", "index_value", "loss_proxy", "loss_event",
    "avg_delay_min", "total_flights",
]


def write_csv(iata: str, records: list[dict]) -> Path:
    """Write records to data/series/flights/{IATA}_daily.csv."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{iata.upper()}_daily.csv"

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

    return path


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch / process European airport delay data from Eurocontrol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode", choices=["csv", "api", "weather-proxy"],
        default="weather-proxy",
        help="Data source mode (default: weather-proxy)",
    )
    parser.add_argument(
        "--input", type=str,
        help="Path to Eurocontrol CSV file (required for --mode csv)",
    )
    parser.add_argument(
        "--airports", type=str,
        help="Comma-separated IATA codes to process (default: all 25 European)",
    )
    parser.add_argument(
        "--years", type=int, default=3,
        help="Years of history for API/weather-proxy modes (default: 3)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing CSVs (default: skip existing)",
    )
    args = parser.parse_args()

    # Filter airports if --airports specified
    global EUROPEAN_AIRPORTS
    if args.airports:
        codes = {c.strip().upper() for c in args.airports.split(",")}
        EUROPEAN_AIRPORTS = [a for a in EUROPEAN_AIRPORTS if a.iata in codes]
        if not EUROPEAN_AIRPORTS:
            print(f"ERROR: No European airports found for: {args.airports}")
            print(f"  Available: {sorted(EUROPEAN_IATA_CODES)}")
            sys.exit(1)

    print(f"Eurocontrol flight delay fetch — mode: {args.mode}")
    print(f"Airports: {len(EUROPEAN_AIRPORTS)} European airports")
    print(f"Output: {OUTPUT_DIR}/")
    print()

    # ── Fetch / parse data ──
    if args.mode == "csv":
        if not args.input:
            print("ERROR: --input required for csv mode.")
            print("  Download data from https://ansperformance.eu/data/")
            print("  Then run: python3 scripts/fetch_eurocontrol.py --mode csv "
                  "--input path/to/airport_delays.csv")
            sys.exit(1)
        csv_path = Path(args.input)
        if not csv_path.exists():
            print(f"ERROR: File not found: {csv_path}")
            sys.exit(1)
        print(f"Processing Eurocontrol CSV: {csv_path}")
        all_data = process_eurocontrol_csv(csv_path)

    elif args.mode == "api":
        token = os.environ.get("EUROCONTROL_API_TOKEN", "")
        if not token:
            print("ERROR: EUROCONTROL_API_TOKEN env var not set.")
            print("  Register at https://ansperformance.eu/ to get an API token.")
            print("  Then: export EUROCONTROL_API_TOKEN=<your-token>")
            print()
            print("  Alternatively, use --mode weather-proxy for synthetic data.")
            sys.exit(1)
        print(f"Fetching from Eurocontrol API ({args.years} years) ...")
        all_data = fetch_eurocontrol_api(token, years=args.years)

    elif args.mode == "weather-proxy":
        print(f"Generating weather-proxy delay data ({args.years} years) ...")
        print("  NOTE: This produces synthetic data based on weather conditions.")
        print("  For real delay data, use --mode csv with Eurocontrol download.")
        print()
        all_data = fetch_weather_proxy(years=args.years)

    else:
        print(f"ERROR: Unknown mode: {args.mode}")
        sys.exit(1)

    # ── Write CSVs ──
    print()
    written = 0
    skipped = 0
    for iata, records in sorted(all_data.items()):
        csv_path = OUTPUT_DIR / f"{iata.upper()}_daily.csv"
        if csv_path.exists() and not args.force:
            skipped += 1
            print(f"  SKIP {iata}: {csv_path.name} already exists (use --force)")
            continue

        path = write_csv(iata, records)
        written += 1
        firing_days = sum(1 for r in records if r["loss_event"] == 1)
        print(f"  WRITE {iata}: {len(records)} days, {firing_days} firing days "
              f"({firing_days/len(records)*100:.1f}%) -> {path.name}")

    # ── Summary ──
    print()
    print(f"Done: {written} files written, {skipped} skipped")
    if written:
        print(f"Output: {OUTPUT_DIR}/")
    if skipped:
        print(f"  (use --force to overwrite existing files)")

    # Report missing airports
    found = set(all_data.keys())
    expected = {a.iata for a in EUROPEAN_AIRPORTS}
    missing = expected - found
    if missing:
        print(f"\nMissing airports (no data): {sorted(missing)}")


if __name__ == "__main__":
    main()
