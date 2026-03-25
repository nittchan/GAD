#!/usr/bin/env python3
"""
Download historical flight data from OpenSky Network's Zenodo datasets and
produce per-airport daily departure counts for the GAD flight-delay triggers.

Data source: OpenSky Network publishes monthly crowd-sourced flight-list CSVs
on Zenodo.  The canonical record is https://zenodo.org/records/7923702
(covers 2019-11 through 2023-01).  Each file has columns:
  callsign, number, icao24, registration, typecode,
  origin, destination, firstseen, lastseen, day

The script:
  1. Queries the Zenodo API for available monthly files.
  2. Downloads each file (1-5 GB) to a temp directory.
  3. Filters rows whose ORIGIN ICAO code belongs to our airport registry.
  4. Aggregates departures per airport per day.
  5. Writes data/series/flights/{IATA}_daily.csv with columns:
       period, index_value, loss_proxy, loss_event, departure_count
  6. Deletes the raw file after processing.

Supports Parquet (preferred) and CSV fallback.  Resumable — skips airports
that already have a CSV file on disk.

Usage:
    python3 scripts/fetch_opensky_zenodo.py
    python3 scripts/fetch_opensky_zenodo.py --months 2022-01,2022-02
    python3 scripts/fetch_opensky_zenodo.py --record 7923702
    python3 scripts/fetch_opensky_zenodo.py --skip-existing   # default
    python3 scripts/fetch_opensky_zenodo.py --no-skip-existing

Requires: pandas, pyarrow (for parquet), requests
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

# ── allow running from repo root: `python scripts/fetch_opensky_zenodo.py`
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import requests

from gad.monitor.airports import ALL_AIRPORTS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZENODO_API = "https://zenodo.org/api/records"
DEFAULT_RECORD_ID = "7923702"
OUTPUT_DIR = REPO_ROOT / "data" / "series" / "flights"

# Build lookup tables from the airport registry
ICAO_TO_IATA: dict[str, str] = {a.icao: a.iata for a in ALL_AIRPORTS}
ALL_ICAO_CODES: set[str] = set(ICAO_TO_IATA.keys())


# ---------------------------------------------------------------------------
# Zenodo helpers
# ---------------------------------------------------------------------------


def fetch_zenodo_files(record_id: str) -> list[dict]:
    """Return the list of file entries from a Zenodo record."""
    url = f"{ZENODO_API}/{record_id}"
    print(f"[zenodo] Fetching record metadata from {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    files = data.get("files", [])
    print(f"[zenodo] Found {len(files)} file(s) in record {record_id}")
    return files


def filter_monthly_files(
    files: list[dict], months: list[str] | None = None
) -> list[dict]:
    """
    Keep only flight-list data files.  If *months* is given (e.g. ['2022-01']),
    keep only files whose name contains one of those month strings.
    """
    # The typical naming pattern is something like:
    #   flightlist_20220101_20220201.csv.gz  or  .parquet
    data_files: list[dict] = []
    for f in files:
        key = f.get("key", "")
        # Skip non-data files (readmes, checksums, …)
        if not key.startswith("flightlist"):
            continue
        if months:
            # Match if any requested month appears as YYYYMM01 in the filename
            matched = False
            for m in months:
                # "2022-01" -> "20220101"
                compact = m.replace("-", "") + "01"
                if compact in key:
                    matched = True
                    break
            if not matched:
                continue
        data_files.append(f)

    # Sort chronologically by filename
    data_files.sort(key=lambda f: f["key"])
    return data_files


def download_file(url: str, dest: Path) -> None:
    """Stream-download a (potentially large) file with progress."""
    print(f"[download] {url}")
    print(f"           -> {dest}")
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 8 * 1024 * 1024  # 8 MB
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            fh.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded * 100 / total
                print(f"\r           {downloaded / 1e6:.0f} / {total / 1e6:.0f} MB ({pct:.1f}%)", end="", flush=True)
            else:
                print(f"\r           {downloaded / 1e6:.0f} MB", end="", flush=True)
    print()  # newline after progress


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------


def load_dataframe(filepath: Path):
    """Load a flight-list file as a pandas DataFrame.

    Tries Parquet first, then gzipped CSV, then plain CSV.
    Only loads the columns we need (origin, day) to save memory.
    """
    import pandas as pd

    name = filepath.name.lower()

    # --- Parquet ---
    if name.endswith(".parquet"):
        print(f"[load] Reading parquet: {filepath.name}")
        try:
            df = pd.read_parquet(filepath, columns=["origin", "day"])
            print(f"[load] {len(df):,} rows loaded")
            return df
        except Exception as e:
            print(f"[load] Parquet read failed ({e}), cannot fall back")
            raise

    # --- CSV (possibly gzipped) ---
    compression = "gzip" if name.endswith(".gz") else None
    print(f"[load] Reading CSV (compression={compression}): {filepath.name}")
    try:
        df = pd.read_csv(
            filepath,
            usecols=["origin", "day"],
            dtype={"origin": str},
            compression=compression,
            low_memory=False,
        )
        print(f"[load] {len(df):,} rows loaded")
        return df
    except Exception as e:
        print(f"[load] CSV read failed: {e}")
        raise


def process_file(filepath: Path, aggregated: dict[str, dict[str, int]]) -> None:
    """
    Read one monthly file and merge departure counts into *aggregated*.

    aggregated structure: { icao: { "YYYY-MM-DD": count, ... }, ... }
    """
    import pandas as pd

    df = load_dataframe(filepath)

    # Keep only rows for airports in our registry
    df = df[df["origin"].isin(ALL_ICAO_CODES)].copy()
    if df.empty:
        print("[process] No rows match our airport registry in this file")
        return

    # Normalise the day column to date strings
    df["day"] = pd.to_datetime(df["day"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["day"])

    # Count departures per (origin_icao, day)
    counts = df.groupby(["origin", "day"]).size().reset_index(name="departures")
    print(f"[process] {len(counts):,} (airport, day) pairs for {counts['origin'].nunique()} airports")

    for _, row in counts.iterrows():
        icao = row["origin"]
        day = row["day"]
        dep = int(row["departures"])
        aggregated.setdefault(icao, {})
        aggregated[icao][day] = aggregated[icao].get(day, 0) + dep


def write_airport_csvs(
    aggregated: dict[str, dict[str, int]], skip_existing: bool = True
) -> int:
    """
    Write per-airport daily CSVs to data/series/flights/{IATA}_daily.csv.
    Returns the number of files written.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0

    for icao, daily in sorted(aggregated.items()):
        iata = ICAO_TO_IATA.get(icao)
        if iata is None:
            continue
        out_path = OUTPUT_DIR / f"{iata}_daily.csv"
        if skip_existing and out_path.exists():
            print(f"[skip] {out_path.name} already exists")
            continue

        # Sort by date
        sorted_days = sorted(daily.items())

        with open(out_path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["period", "index_value", "loss_proxy", "loss_event", "departure_count"])
            for day, dep_count in sorted_days:
                loss = 1.0 if dep_count == 0 else 0.0
                loss_int = 1 if dep_count == 0 else 0
                writer.writerow([day, dep_count, loss, loss_int, dep_count])

        print(f"[write] {out_path.name}: {len(sorted_days)} days")
        written += 1

    return written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download OpenSky Zenodo flight data and build per-airport daily departure CSVs."
    )
    parser.add_argument(
        "--record",
        default=DEFAULT_RECORD_ID,
        help=f"Zenodo record ID (default: {DEFAULT_RECORD_ID})",
    )
    parser.add_argument(
        "--months",
        default=None,
        help="Comma-separated month filters, e.g. 2022-01,2022-06. Default: all available.",
    )
    parser.add_argument(
        "--skip-existing",
        dest="skip_existing",
        action="store_true",
        default=True,
        help="Skip airports whose CSV already exists (default).",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Overwrite existing airport CSVs.",
    )
    parser.add_argument(
        "--tmpdir",
        default=None,
        help="Temp directory for downloads (default: system temp).",
    )
    args = parser.parse_args()

    months = args.months.split(",") if args.months else None

    # 1. Fetch Zenodo record metadata
    files = fetch_zenodo_files(args.record)
    data_files = filter_monthly_files(files, months)
    if not data_files:
        print("[error] No matching flight-list files found in Zenodo record.")
        sys.exit(1)

    print(f"\n[plan] Will process {len(data_files)} file(s):")
    for f in data_files:
        size_mb = f.get("size", 0) / 1e6
        print(f"       {f['key']}  ({size_mb:.0f} MB)")
    print()

    # 2. Download and process each file
    aggregated: dict[str, dict[str, int]] = {}
    tmpdir_base = Path(args.tmpdir) if args.tmpdir else None

    for idx, fmeta in enumerate(data_files, 1):
        fname = fmeta["key"]
        # Zenodo v2 API: download link is in fmeta["links"]["self"] or construct it
        download_url = fmeta.get("links", {}).get("self")
        if not download_url:
            download_url = f"https://zenodo.org/records/{args.record}/files/{fname}?download=1"

        print(f"\n{'='*60}")
        print(f"[file {idx}/{len(data_files)}] {fname}")
        print(f"{'='*60}")

        # Download to temp directory
        with tempfile.TemporaryDirectory(dir=tmpdir_base) as tmpdir:
            local_path = Path(tmpdir) / fname
            download_file(download_url, local_path)

            # Process
            try:
                process_file(local_path, aggregated)
            except Exception as e:
                print(f"[error] Failed to process {fname}: {e}")
                continue

            # File is auto-deleted when TemporaryDirectory exits
            print(f"[cleanup] Deleted temp file for {fname}")

    # 3. Write per-airport CSVs
    if not aggregated:
        print("\n[warn] No departure data found for any registered airport.")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"[output] Writing per-airport CSVs to {OUTPUT_DIR}")
    print(f"{'='*60}")
    written = write_airport_csvs(aggregated, skip_existing=args.skip_existing)

    total_airports = len(aggregated)
    total_days = sum(len(d) for d in aggregated.values())
    print(f"\n[done] {total_airports} airports, {total_days:,} total (airport, day) records")
    print(f"[done] {written} CSV files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
