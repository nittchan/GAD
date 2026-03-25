#!/usr/bin/env python3
"""
Backfill DuckDB trigger_observations from historical CSV files.

Reads all CSVs from data/series/weather/ and data/series/aqi/,
parses period/index_value/loss_event columns, and writes each row
as a TriggerObservation via write_observation().

Usage:
    python scripts/backfill_observations.py
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gad.config import SERIES_DIR
from gad.engine.db_read import get_observation_count
from gad.engine.db_write import write_observation


def _csv_to_trigger_id_weather(filename: str) -> str:
    """Map weather CSV filename to trigger_id.
    e.g. DEL_daily.csv -> weather-heat-del
    """
    iata = filename.replace("_daily.csv", "").lower()
    return f"weather-heat-{iata}"


def _csv_to_trigger_id_aqi(filename: str) -> str:
    """Map AQI CSV filename to trigger_id.
    e.g. DEL_aqi_daily.csv -> aqi-pm25-del
    """
    iata = filename.replace("_aqi_daily.csv", "").lower()
    return f"aqi-pm25-{iata}"


def _parse_datetime(period_str: str) -> datetime:
    """Parse a period string into a timezone-aware datetime."""
    dt = datetime.strptime(period_str.strip(), "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


def _backfill_csv(csv_path: Path, trigger_id: str, data_source: str) -> int:
    """Backfill a single CSV file. Returns count of rows written."""
    count = 0
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                period = row.get("period", "").strip()
                if not period:
                    continue
                observed_at = _parse_datetime(period)
                value_str = row.get("index_value", "")
                value = float(value_str) if value_str.strip() else None
                loss_event_str = row.get("loss_event", "0")
                fired = bool(int(float(loss_event_str.strip()))) if loss_event_str.strip() else False
                write_observation(trigger_id, value, fired, data_source, None)
                count += 1
            except Exception:
                continue  # Skip malformed rows
    return count


def main():
    weather_dir = SERIES_DIR / "weather"
    aqi_dir = SERIES_DIR / "aqi"

    # Collect all CSV files to process
    tasks: list[tuple[Path, str, str]] = []

    if weather_dir.exists():
        for csv_path in sorted(weather_dir.glob("*_daily.csv")):
            trigger_id = _csv_to_trigger_id_weather(csv_path.name)
            tasks.append((csv_path, trigger_id, "openmeteo"))

    if aqi_dir.exists():
        for csv_path in sorted(aqi_dir.glob("*_aqi_daily.csv")):
            trigger_id = _csv_to_trigger_id_aqi(csv_path.name)
            tasks.append((csv_path, trigger_id, "openaq"))

    total = len(tasks)
    if total == 0:
        print("No CSV files found to backfill.")
        return

    print(f"Found {total} CSV files to backfill.")

    for i, (csv_path, trigger_id, data_source) in enumerate(tasks, 1):
        # Skip if observations already exist for this trigger
        existing = get_observation_count(trigger_id)
        if existing and existing > 0:
            print(f"[{i}/{total}] {trigger_id}: skipped ({existing} observations already exist)")
            continue

        count = _backfill_csv(csv_path, trigger_id, data_source)
        print(f"[{i}/{total}] {trigger_id}: {count} observations backfilled")

    print("Backfill complete.")


if __name__ == "__main__":
    main()
