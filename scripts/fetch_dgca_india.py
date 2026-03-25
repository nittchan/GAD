#!/usr/bin/env python3
"""
DATA-03d: Fetch / parse DGCA India monthly flight performance data.

DGCA (Directorate General of Civil Aviation, India) publishes monthly performance
reports as PDFs at https://www.dgca.gov.in/digigov-portal/ → Statistical Division.

This script supports two modes:

  Mode 1 — PDF parse (requires downloaded PDFs + pdfplumber):
      python3 scripts/fetch_dgca_india.py --pdf-dir /path/to/dgca_pdfs/

  Mode 2 — CSV template (manual-input fallback):
      python3 scripts/fetch_dgca_india.py --generate-template
      # Fill in data/dgca_template.csv from DGCA reports, then:
      python3 scripts/fetch_dgca_india.py --from-template data/dgca_template.csv

Target Indian airports (top 10):
    DEL, BOM, BLR, MAA, CCU, HYD, AMD, COK, GOI, JAI

Output: data/series/flights/{IATA}_daily.csv
Format: period, index_value, loss_proxy, loss_event
  - index_value = average departure delay in minutes (or pct delayed if only that is available)
  - loss_proxy  = same as index_value (continuous measure)
  - loss_event  = 1 if delay metric exceeds threshold (45 min for tier-1, 60 for tier-2)

Author: Nitthin Chandran Nair
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gad.config import SERIES_DIR  # noqa: E402

OUTPUT_DIR = SERIES_DIR / "flights"

# Top 10 Indian airports targeted by this script
INDIA_AIRPORTS = {
    "DEL": {"name": "Delhi", "tier": 1, "threshold": 45},
    "BOM": {"name": "Mumbai", "tier": 1, "threshold": 45},
    "BLR": {"name": "Bengaluru", "tier": 1, "threshold": 45},
    "MAA": {"name": "Chennai", "tier": 1, "threshold": 45},
    "CCU": {"name": "Kolkata", "tier": 1, "threshold": 45},
    "HYD": {"name": "Hyderabad", "tier": 1, "threshold": 45},
    "AMD": {"name": "Ahmedabad", "tier": 2, "threshold": 60},
    "COK": {"name": "Kochi", "tier": 2, "threshold": 60},
    "GOI": {"name": "Goa", "tier": 2, "threshold": 60},
    "JAI": {"name": "Jaipur", "tier": 2, "threshold": 60},
}

# DGCA PDFs sometimes use city names instead of IATA codes
CITY_TO_IATA = {
    "delhi": "DEL",
    "new delhi": "DEL",
    "indira gandhi": "DEL",
    "mumbai": "BOM",
    "bombay": "BOM",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "chennai": "MAA",
    "madras": "MAA",
    "kolkata": "CCU",
    "calcutta": "CCU",
    "hyderabad": "HYD",
    "ahmedabad": "AMD",
    "kochi": "COK",
    "cochin": "COK",
    "goa": "GOI",
    "mopa": "GOI",
    "dabolim": "GOI",
    "jaipur": "JAI",
}


# ---------------------------------------------------------------------------
# Mode 1: PDF parsing with pdfplumber
# ---------------------------------------------------------------------------

def parse_dgca_pdf(pdf_path: Path) -> list[dict]:
    """
    Parse a DGCA monthly OTP (On-Time Performance) PDF.

    Expected table columns (typical DGCA format):
        Airline | Airport | Scheduled | Operated | Cancelled | Delayed | OTP%

    Returns a list of dicts:
        {"airport": "DEL", "month": "2025-01", "scheduled": 1234,
         "operated": 1200, "delayed": 100, "avg_delay_min": 35.0,
         "otp_pct": 85.0}

    Note: DGCA PDFs vary in format across months. This parser handles the
    most common layout. If parsing fails, use the CSV template mode instead.
    """
    try:
        import pdfplumber
    except ImportError:
        print("ERROR: pdfplumber is required for PDF mode.")
        print("  pip install pdfplumber>=0.10")
        sys.exit(1)

    records: list[dict] = []
    month_str = _extract_month_from_filename(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                records.extend(_parse_table_rows(table, month_str))

            # Fallback: if no tables extracted, try text-based parsing
            if not tables:
                text = page.extract_text() or ""
                records.extend(_parse_text_block(text, month_str))

    # Deduplicate by airport+month (keep first)
    seen = set()
    unique = []
    for r in records:
        key = (r["airport"], r["month"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


def _extract_month_from_filename(pdf_path: Path) -> str:
    """Try to extract YYYY-MM from filename like 'DGCA_OTP_Jan2025.pdf'."""
    stem = pdf_path.stem.lower()

    # Try patterns like "2025-01" or "jan2025" or "january_2025"
    # Pattern: explicit YYYY-MM
    match = re.search(r"(\d{4})-(\d{2})", stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}"

    # Pattern: MonYYYY or Mon_YYYY
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    for abbr, num in months.items():
        pattern = rf"{abbr}\w*[_\s-]*(\d{{4}})"
        match = re.search(pattern, stem)
        if match:
            return f"{match.group(1)}-{num}"
        # Also try YYYY_Month
        pattern2 = rf"(\d{{4}})[_\s-]*{abbr}"
        match2 = re.search(pattern2, stem)
        if match2:
            return f"{match2.group(1)}-{num}"

    # Fallback: unknown
    return "unknown"


def _match_airport(text: str) -> str | None:
    """Match a text fragment to one of our 10 Indian airports."""
    text_lower = text.strip().lower()

    # Direct IATA match
    for iata in INDIA_AIRPORTS:
        if iata.lower() in text_lower:
            return iata

    # City name match
    for city, iata in CITY_TO_IATA.items():
        if city in text_lower:
            return iata

    return None


def _safe_float(val: str | None) -> float | None:
    """Convert string to float, returning None on failure."""
    if val is None:
        return None
    val = val.strip().replace(",", "").replace("%", "")
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: str | None) -> int | None:
    """Convert string to int, returning None on failure."""
    f = _safe_float(val)
    return int(f) if f is not None else None


def _parse_table_rows(table: list[list], month_str: str) -> list[dict]:
    """Parse rows from a pdfplumber-extracted table."""
    records = []
    if not table or len(table) < 2:
        return records

    # Try to identify column indices from header row
    header = [str(c).lower().strip() if c else "" for c in table[0]]

    # Common DGCA column patterns
    airport_col = None
    scheduled_col = None
    operated_col = None
    delayed_col = None
    otp_col = None

    for i, h in enumerate(header):
        if any(k in h for k in ["airport", "station", "city"]):
            airport_col = i
        elif any(k in h for k in ["scheduled", "sched"]):
            scheduled_col = i
        elif any(k in h for k in ["operated", "actual", "departed"]):
            operated_col = i
        elif any(k in h for k in ["delayed", "delay"]):
            delayed_col = i
        elif any(k in h for k in ["otp", "on.time", "on time", "punctuality"]):
            otp_col = i

    # If we couldn't identify columns by header, try positional (common layout)
    if airport_col is None:
        # Heuristic: first text column is airport, rest are numeric
        for i, h in enumerate(header):
            if h and not h.replace(".", "").replace(",", "").isdigit():
                airport_col = i
                break
        if airport_col is None:
            airport_col = 0

    for row in table[1:]:
        if not row or len(row) <= airport_col:
            continue

        airport_text = str(row[airport_col]) if row[airport_col] else ""
        iata = _match_airport(airport_text)
        if not iata:
            continue

        record = {
            "airport": iata,
            "month": month_str,
            "scheduled": _safe_int(str(row[scheduled_col])) if scheduled_col and scheduled_col < len(row) else None,
            "operated": _safe_int(str(row[operated_col])) if operated_col and operated_col < len(row) else None,
            "delayed": _safe_int(str(row[delayed_col])) if delayed_col and delayed_col < len(row) else None,
            "otp_pct": _safe_float(str(row[otp_col])) if otp_col and otp_col < len(row) else None,
            "avg_delay_min": None,  # DGCA doesn't always publish avg delay
        }

        # Derive OTP if we have scheduled + delayed but not OTP directly
        if record["otp_pct"] is None and record["scheduled"] and record["delayed"]:
            record["otp_pct"] = round(
                100.0 * (1.0 - record["delayed"] / record["scheduled"]), 1
            )

        records.append(record)

    return records


def _parse_text_block(text: str, month_str: str) -> list[dict]:
    """
    Fallback text-based parser for when pdfplumber can't extract tables.
    Looks for lines containing airport names followed by numbers.
    """
    records = []
    lines = text.split("\n")

    for line in lines:
        iata = _match_airport(line)
        if not iata:
            continue

        # Extract numbers from the line
        numbers = re.findall(r"[\d,]+\.?\d*", line)
        numbers = [n.replace(",", "") for n in numbers]
        floats = []
        for n in numbers:
            try:
                floats.append(float(n))
            except ValueError:
                pass

        if len(floats) >= 2:
            record = {
                "airport": iata,
                "month": month_str,
                "scheduled": int(floats[0]) if len(floats) > 0 else None,
                "operated": int(floats[1]) if len(floats) > 1 else None,
                "delayed": int(floats[2]) if len(floats) > 2 else None,
                "otp_pct": floats[-1] if len(floats) > 3 and floats[-1] <= 100 else None,
                "avg_delay_min": None,
            }
            records.append(record)

    return records


# ---------------------------------------------------------------------------
# Mode 2: CSV template (manual-input fallback)
# ---------------------------------------------------------------------------

TEMPLATE_HEADER = [
    "airport_iata", "month", "scheduled_flights", "operated_flights",
    "delayed_flights", "avg_delay_minutes", "otp_percent",
]

TEMPLATE_EXAMPLE_ROWS = [
    ["DEL", "2025-01", "12000", "11800", "1500", "32", "87.3"],
    ["BOM", "2025-01", "10500", "10300", "1200", "28", "88.4"],
]


def generate_template(output_path: Path) -> None:
    """Generate a CSV template that users can fill from DGCA reports."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(TEMPLATE_HEADER)

        # Write example rows (commented instruction + 2 examples)
        writer.writerows(TEMPLATE_EXAMPLE_ROWS)

        # Add empty rows for all airports x 12 months as a scaffold
        for iata in INDIA_AIRPORTS:
            for m in range(1, 13):
                writer.writerow([iata, f"2025-{m:02d}", "", "", "", "", ""])

    print(f"Template generated: {output_path}")
    print(f"  Fill in data from DGCA monthly reports, then run:")
    print(f"  python3 scripts/fetch_dgca_india.py --from-template {output_path}")


def load_template(template_path: Path) -> list[dict]:
    """Load a filled-in CSV template."""
    records = []
    with open(template_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iata = row.get("airport_iata", "").strip().upper()
            if iata not in INDIA_AIRPORTS:
                continue

            scheduled = _safe_int(row.get("scheduled_flights"))
            operated = _safe_int(row.get("operated_flights"))
            delayed = _safe_int(row.get("delayed_flights"))
            avg_delay = _safe_float(row.get("avg_delay_minutes"))
            otp_pct = _safe_float(row.get("otp_percent"))

            # Skip empty rows
            if not any([scheduled, operated, delayed, avg_delay, otp_pct]):
                continue

            records.append({
                "airport": iata,
                "month": row.get("month", "").strip(),
                "scheduled": scheduled,
                "operated": operated,
                "delayed": delayed,
                "avg_delay_min": avg_delay,
                "otp_pct": otp_pct,
            })

    return records


# ---------------------------------------------------------------------------
# Output: convert parsed records to per-airport daily CSVs
# ---------------------------------------------------------------------------

def _expand_monthly_to_daily(records: list[dict]) -> dict[str, list[dict]]:
    """
    Expand monthly records into synthetic daily rows.

    DGCA publishes monthly aggregates. We distribute evenly across days in
    the month so the CSV format matches BTS daily output.
    Each day gets:
      - index_value = avg_delay_minutes (if available) or delay_pct * 100
      - loss_proxy  = same as index_value
      - loss_event  = 1 if index_value >= threshold for that airport
    """
    import calendar

    airport_days: dict[str, list[dict]] = {}

    for rec in records:
        iata = rec["airport"]
        month_str = rec["month"]

        # Parse month
        try:
            parts = month_str.split("-")
            year, month = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            print(f"  WARNING: skipping record with unparseable month '{month_str}' for {iata}")
            continue

        # Determine the delay metric to use
        if rec.get("avg_delay_min") is not None:
            # Best case: actual average delay in minutes
            base_value = rec["avg_delay_min"]
        elif rec.get("otp_pct") is not None:
            # Convert OTP% to delay proxy: (100 - OTP%) scaled to minutes
            # e.g., OTP 85% → 15% delayed → proxy ~22.5 min (scaled by 1.5)
            delay_pct = 100.0 - rec["otp_pct"]
            base_value = round(delay_pct * 1.5, 1)  # rough scaling to minutes
        elif rec.get("scheduled") and rec.get("delayed"):
            delay_pct = 100.0 * rec["delayed"] / rec["scheduled"]
            base_value = round(delay_pct * 1.5, 1)
        else:
            continue  # not enough data

        threshold = INDIA_AIRPORTS[iata]["threshold"]
        days_in_month = calendar.monthrange(year, month)[1]

        if iata not in airport_days:
            airport_days[iata] = []

        for day in range(1, days_in_month + 1):
            d = date(year, month, day)
            # Add small daily variance (deterministic based on day)
            # so the series isn't perfectly flat
            variance = ((day * 7 + month * 3) % 11 - 5) * 0.5
            daily_value = round(max(0, base_value + variance), 1)

            airport_days[iata].append({
                "period": d.isoformat(),
                "index_value": daily_value,
                "loss_proxy": daily_value,
                "loss_event": 1 if daily_value >= threshold else 0,
            })

    return airport_days


def write_daily_csvs(records: list[dict]) -> dict[str, int]:
    """Convert parsed records to per-airport daily CSVs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    airport_days = _expand_monthly_to_daily(records)
    written = {}

    for iata, days in sorted(airport_days.items()):
        # Sort by date
        days.sort(key=lambda d: d["period"])

        csv_path = OUTPUT_DIR / f"{iata}_daily.csv"

        # If file exists, merge (append new dates, skip duplicates)
        existing_dates = set()
        if csv_path.exists():
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_dates.add(row["period"])

        new_days = [d for d in days if d["period"] not in existing_dates]
        all_days = []

        if csv_path.exists() and existing_dates:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_days = list(reader)

        all_days.extend(new_days)
        all_days.sort(key=lambda d: d["period"])

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["period", "index_value", "loss_proxy", "loss_event"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in all_days:
                writer.writerow({k: d[k] for k in fieldnames})

        written[iata] = len(all_days)
        print(f"  {iata}: {len(all_days)} days → {csv_path}")

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch/parse DGCA India flight performance data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse downloaded DGCA PDFs:
  python3 scripts/fetch_dgca_india.py --pdf-dir ~/Downloads/dgca_reports/

  # Generate a CSV template for manual entry:
  python3 scripts/fetch_dgca_india.py --generate-template

  # Import from filled template:
  python3 scripts/fetch_dgca_india.py --from-template data/dgca_template.csv
        """,
    )
    parser.add_argument(
        "--pdf-dir", type=Path,
        help="Directory containing downloaded DGCA PDF reports",
    )
    parser.add_argument(
        "--generate-template", action="store_true",
        help="Generate a CSV template for manual data entry",
    )
    parser.add_argument(
        "--from-template", type=Path,
        help="Import data from a filled-in CSV template",
    )
    parser.add_argument(
        "--template-output", type=Path,
        default=Path("data/dgca_template.csv"),
        help="Path for generated template (default: data/dgca_template.csv)",
    )
    args = parser.parse_args()

    if not any([args.pdf_dir, args.generate_template, args.from_template]):
        parser.print_help()
        print("\nERROR: Specify one of --pdf-dir, --generate-template, or --from-template")
        sys.exit(1)

    # Mode: generate template
    if args.generate_template:
        generate_template(args.template_output)
        return

    # Mode: import from template
    if args.from_template:
        if not args.from_template.exists():
            print(f"ERROR: Template file not found: {args.from_template}")
            sys.exit(1)
        print(f"Loading template: {args.from_template}")
        records = load_template(args.from_template)
        print(f"  Found {len(records)} records for {len(set(r['airport'] for r in records))} airports")
        if records:
            written = write_daily_csvs(records)
            print(f"\nDone: wrote {sum(written.values())} total days across {len(written)} airports")
        else:
            print("No valid records found in template.")
        return

    # Mode: parse PDFs
    if args.pdf_dir:
        if not args.pdf_dir.is_dir():
            print(f"ERROR: Directory not found: {args.pdf_dir}")
            sys.exit(1)

        pdfs = sorted(args.pdf_dir.glob("*.pdf"))
        if not pdfs:
            print(f"No PDF files found in {args.pdf_dir}")
            sys.exit(1)

        print(f"Found {len(pdfs)} PDF files in {args.pdf_dir}")
        all_records: list[dict] = []

        for pdf_path in pdfs:
            print(f"\nParsing: {pdf_path.name}")
            try:
                records = parse_dgca_pdf(pdf_path)
                print(f"  Extracted {len(records)} airport records")
                all_records.extend(records)
            except Exception as e:
                print(f"  ERROR parsing {pdf_path.name}: {e}")
                print(f"  Consider using --generate-template for manual entry instead.")

        if all_records:
            airports_found = set(r["airport"] for r in all_records)
            print(f"\nTotal: {len(all_records)} records for airports: {', '.join(sorted(airports_found))}")
            written = write_daily_csvs(all_records)
            print(f"\nDone: wrote {sum(written.values())} total days across {len(written)} airports")
        else:
            print("\nNo records extracted from PDFs.")
            print("DGCA PDF formats vary — consider using the CSV template mode instead:")
            print("  python3 scripts/fetch_dgca_india.py --generate-template")
        return


if __name__ == "__main__":
    main()
