#!/usr/bin/env python3
"""
Fetch US on-time flight performance data from BTS TranStats (Bureau of
Transportation Statistics).

Data source: On-Time Reporting Carrier On-Time Performance (1987–present)
  https://transtats.bts.gov/PREZIP/

Each monthly ZIP contains a CSV with FL_DATE, OP_CARRIER, ORIGIN, DEST,
DEP_DELAY, ARR_DELAY, CANCELLED, etc.  Free, no API key needed.

Output: data/series/flights/{IATA}_daily.csv per US airport
Format: period, index_value, loss_proxy, loss_event, avg_delay_min,
        total_flights, delayed_count

Usage:
    python3 scripts/fetch_bts_transtats.py
    python3 scripts/fetch_bts_transtats.py --airports JFK,LAX,ORD
    python3 scripts/fetch_bts_transtats.py --years 2

Resumable: skips months whose data already exists in every airport CSV.
Respects a 1-second delay between downloads.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gad.config import SERIES_DIR  # noqa: E402

OUTPUT_DIR = SERIES_DIR / "flights"

# All US airports tracked by GAD
US_AIRPORTS = [
    "JFK", "LAX", "ORD", "ATL", "DFW",
    "DEN", "SFO", "MIA", "EWR", "BOS",
    "SEA", "DTW", "MSP", "IAH", "PHL",
]

# BTS PREZIP URL template
BTS_PREZIP_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present"
    "_{year}_{month}.zip"
)

# Tier-1 parametric threshold for flight delay (minutes)
DELAY_THRESHOLD = 45
# Flights with >15 min departure delay count as "delayed"
DELAYED_MIN = 15

TIMEOUT = 120  # seconds – these ZIPs can be large (~200 MB)
DOWNLOAD_DELAY = 1  # seconds between requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _month_range(years: int) -> list[tuple[int, int]]:
    """Return (year, month) pairs for the last *years* years, newest first."""
    today = date.today()
    pairs: list[tuple[int, int]] = []
    for y in range(today.year, today.year - years - 1, -1):
        end_m = today.month if y == today.year else 12
        start_m = 1
        for m in range(end_m, start_m - 1, -1):
            # Skip current month (data won't be available yet)
            if y == today.year and m >= today.month:
                continue
            pairs.append((y, m))
    return pairs


def _month_already_fetched(year: int, month: int, airports: list[str]) -> bool:
    """Check if every airport CSV already contains at least one row for this month."""
    prefix = f"{year}-{month:02d}"
    for iata in airports:
        csv_path = OUTPUT_DIR / f"{iata}_daily.csv"
        if not csv_path.exists():
            return False
        found = False
        with open(csv_path, "r") as f:
            for line in f:
                if line.startswith(prefix):
                    found = True
                    break
        if not found:
            return False
    return True


def _download_month(year: int, month: int) -> bytes | None:
    """Download the BTS ZIP for a given month. Returns bytes or None on failure."""
    url = BTS_PREZIP_URL.format(year=year, month=month)
    print(f"  Downloading {url} ...")
    try:
        resp = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
        if resp.status_code == 200:
            return resp.content
        print(f"  HTTP {resp.status_code} — skipping {year}-{month:02d}")
        return None
    except httpx.TimeoutException:
        print(f"  Timeout downloading {year}-{month:02d} — skipping")
        return None
    except httpx.HTTPError as exc:
        print(f"  HTTP error for {year}-{month:02d}: {exc} — skipping")
        return None


def _extract_csv_from_zip(zip_bytes: bytes) -> str | None:
    """Extract the first CSV file from the BTS ZIP archive."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                print("  No CSV found in ZIP")
                return None
            # Pick the largest CSV (the actual data file)
            csv_name = max(csv_names, key=lambda n: zf.getinfo(n).file_size)
            return zf.read(csv_name).decode("utf-8", errors="replace")
    except zipfile.BadZipFile:
        print("  Bad ZIP file — skipping")
        return None


def _process_csv(
    csv_text: str,
    airports: set[str],
) -> dict[str, dict[str, dict]]:
    """
    Parse the BTS CSV and aggregate per airport per day.

    Returns: {iata: {date_str: {total, delay_sum, delayed_count}}}
    """
    agg: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(
        lambda: {"total": 0, "delay_sum": 0.0, "delayed_count": 0}
    ))

    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        origin = (row.get("ORIGIN") or "").strip()
        if origin not in airports:
            continue
        fl_date = (row.get("FL_DATE") or "").strip()
        if not fl_date:
            continue

        # Parse departure delay
        dep_delay_str = (row.get("DEP_DELAY") or "").strip()
        if not dep_delay_str:
            continue
        try:
            dep_delay = float(dep_delay_str)
        except ValueError:
            continue

        bucket = agg[origin][fl_date]
        bucket["total"] += 1
        bucket["delay_sum"] += dep_delay
        if dep_delay > DELAYED_MIN:
            bucket["delayed_count"] += 1

    return dict(agg)


def _append_to_csv(iata: str, daily_data: dict[str, dict]) -> None:
    """Append daily aggregated rows to the airport's CSV file."""
    csv_path = OUTPUT_DIR / f"{iata}_daily.csv"
    header = [
        "period", "index_value", "loss_proxy", "loss_event",
        "avg_delay_min", "total_flights", "delayed_count",
    ]

    # Read existing dates to avoid duplicates
    existing_dates: set[str] = set()
    if csv_path.exists():
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dates.add(row.get("period", ""))

    # Sort new dates
    new_dates = sorted(d for d in daily_data if d not in existing_dates)
    if not new_dates:
        return

    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        for dt in new_dates:
            bucket = daily_data[dt]
            avg_delay = bucket["delay_sum"] / bucket["total"] if bucket["total"] else 0.0
            avg_delay = round(avg_delay, 2)
            loss = 1.0 if avg_delay >= DELAY_THRESHOLD else 0.0
            writer.writerow({
                "period": dt,
                "index_value": avg_delay,
                "loss_proxy": loss,
                "loss_event": int(loss),
                "avg_delay_min": avg_delay,
                "total_flights": bucket["total"],
                "delayed_count": bucket["delayed_count"],
            })


def _sort_csv(iata: str) -> None:
    """Sort the airport CSV by date to keep it ordered after appends."""
    csv_path = OUTPUT_DIR / f"{iata}_daily.csv"
    if not csv_path.exists():
        return
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    rows.sort(key=lambda r: r.get("period", ""))

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch BTS TranStats US on-time flight performance data"
    )
    parser.add_argument(
        "--years", type=int, default=3,
        help="Number of years of history to fetch (default: 3)",
    )
    parser.add_argument(
        "--airports", type=str, default=None,
        help="Comma-separated IATA codes to fetch (default: all 15 US airports)",
    )
    args = parser.parse_args()

    airports = US_AIRPORTS
    if args.airports:
        airports = [a.strip().upper() for a in args.airports.split(",")]
        invalid = [a for a in airports if a not in US_AIRPORTS]
        if invalid:
            print(f"Warning: unknown airports ignored: {invalid}")
            airports = [a for a in airports if a in US_AIRPORTS]

    airports_set = set(airports)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    months = _month_range(args.years)
    print(f"Fetching {len(months)} months for {len(airports)} US airports")
    print(f"Airports: {', '.join(airports)}")
    print(f"Output:   {OUTPUT_DIR}/")
    print()

    fetched = 0
    skipped = 0

    for year, month in months:
        label = f"{year}-{month:02d}"

        if _month_already_fetched(year, month, airports):
            print(f"[{label}] already fetched — skipping")
            skipped += 1
            continue

        print(f"[{label}] Fetching ...")
        zip_bytes = _download_month(year, month)
        if zip_bytes is None:
            continue

        print(f"  ZIP size: {len(zip_bytes) / 1024 / 1024:.1f} MB — extracting CSV ...")
        csv_text = _extract_csv_from_zip(zip_bytes)
        if csv_text is None:
            continue

        print(f"  Aggregating by airport and day ...")
        agg = _process_csv(csv_text, airports_set)

        for iata in airports:
            if iata in agg:
                daily = agg[iata]
                total_flights = sum(d["total"] for d in daily.values())
                total_delay = sum(d["delay_sum"] for d in daily.values())
                avg = total_delay / total_flights if total_flights else 0
                print(f"  [{label}] {iata}: {total_flights} flights, avg delay {avg:.1f} min")
                _append_to_csv(iata, daily)

        fetched += 1

        # Respect rate limiting
        time.sleep(DOWNLOAD_DELAY)

    # Final sort of all CSVs
    print()
    print("Sorting CSV files by date ...")
    for iata in airports:
        _sort_csv(iata)

    print()
    print(f"Done. Fetched {fetched} months, skipped {skipped} (already present).")
    print(f"Output files in {OUTPUT_DIR}/")
    for iata in airports:
        csv_path = OUTPUT_DIR / f"{iata}_daily.csv"
        if csv_path.exists():
            # Count data rows
            with open(csv_path) as f:
                lines = sum(1 for _ in f) - 1  # subtract header
            print(f"  {iata}_daily.csv: {lines} days")


if __name__ == "__main__":
    main()
