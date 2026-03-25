#!/usr/bin/env python3
"""
Precompute basis risk for all triggers that have historical data.

For each trigger in GLOBAL_TRIGGERS, checks if a matching CSV exists in
data/series/weather/ or data/series/aqi/. If so, runs compute_basis_risk()
and serializes the BasisRiskReport to data/basis_risk/{trigger_id}.json.

Usage:
    python3 scripts/precompute_basis_risk.py
    python3 scripts/precompute_basis_risk.py --peril extreme_weather  # single peril
    python3 scripts/precompute_basis_risk.py --force                  # recompute all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gad.engine.basis_risk import compute_basis_risk  # noqa: E402
from gad.engine.loader import load_weather_data_from_csv  # noqa: E402
from gad.engine.models import DataSourceProvenance, TriggerDef  # noqa: E402
from gad.monitor.triggers import GLOBAL_TRIGGERS  # noqa: E402

from gad.config import DATA_ROOT, SERIES_DIR, BASIS_RISK_DIR  # noqa: E402

WEATHER_DIR = SERIES_DIR / "weather"
AQI_DIR = SERIES_DIR / "aqi"
FLIGHTS_DIR = SERIES_DIR / "flights"
OUTPUT_DIR = BASIS_RISK_DIR

# Map monitor trigger ID to historical CSV path
PERIL_DATA_MAP = {
    "extreme_weather": ("weather", WEATHER_DIR, lambda iata: f"{iata}_daily.csv"),
    "air_quality": ("aqi", AQI_DIR, lambda iata: f"{iata}_aqi_daily.csv"),
    "flight_delay": ("flights", FLIGHTS_DIR, lambda iata: f"{iata}_daily.csv"),
}

# Map monitor peril names to provenance info
PROVENANCE_MAP = {
    "extreme_weather": DataSourceProvenance(
        primary_source="Open-Meteo Archive",
        primary_url="https://open-meteo.com/",
        max_data_latency_seconds=86400,
        historical_years_available=5,
    ),
    "air_quality": DataSourceProvenance(
        primary_source="OpenAQ v3",
        primary_url="https://openaq.org/",
        max_data_latency_seconds=3600,
        historical_years_available=2,
    ),
    "flight_delay": DataSourceProvenance(
        primary_source="DGCA India / BTS USA / OpenSky",
        primary_url="https://www.dgca.gov.in/digigov-portal/",
        max_data_latency_seconds=86400,
        historical_years_available=1,
    ),
}


def _extract_iata(trigger_id: str) -> str:
    """Extract IATA code from trigger ID like 'weather-heat-del' or 'aqi-del'."""
    return trigger_id.split("-")[-1].upper()


def _find_csv(trigger) -> Path | None:
    """Find the historical CSV for a trigger."""
    peril_info = PERIL_DATA_MAP.get(trigger.peril)
    if not peril_info:
        return None

    _, data_dir, filename_fn = peril_info
    iata = _extract_iata(trigger.id)
    csv_path = data_dir / filename_fn(iata)

    if csv_path.exists():
        return csv_path
    return None


def _build_trigger_def(trigger) -> TriggerDef:
    """Convert a MonitorTrigger to a TriggerDef for compute_basis_risk."""
    provenance = PROVENANCE_MAP.get(trigger.peril, DataSourceProvenance(
        primary_source=trigger.data_source,
        primary_url="https://parametricdata.io",
        max_data_latency_seconds=86400,
        historical_years_available=1,
    ))

    return TriggerDef(
        trigger_id=uuid4(),
        name=trigger.name,
        description=trigger.description,
        peril=trigger.peril,
        threshold=trigger.threshold,
        threshold_unit=trigger.threshold_unit,
        data_source=trigger.data_source,
        geography={"type": "Point", "coordinates": [trigger.lon, trigger.lat]},
        provenance=provenance,
        trigger_fires_when_above=trigger.fires_when_above,
        is_public=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute basis risk for all triggers")
    parser.add_argument("--peril", type=str, help="Only compute for this peril type")
    parser.add_argument("--force", action="store_true", help="Recompute even if JSON exists")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    triggers = GLOBAL_TRIGGERS
    if args.peril:
        triggers = [t for t in triggers if t.peril == args.peril]
        if not triggers:
            print(f"ERROR: No triggers found for peril '{args.peril}'")
            sys.exit(1)

    computed = 0
    skipped_exists = 0
    skipped_no_csv = 0
    errors = 0
    computed_by_peril: dict[str, int] = {}

    print(f"Precomputing basis risk for {len(triggers)} triggers...")
    print(f"Output: {OUTPUT_DIR}/")
    print()

    for i, trigger in enumerate(triggers):
        output_path = OUTPUT_DIR / f"{trigger.id}.json"

        # Skip if already computed (unless --force)
        if output_path.exists() and not args.force:
            skipped_exists += 1
            continue

        # Find historical CSV
        csv_path = _find_csv(trigger)
        if csv_path is None:
            skipped_no_csv += 1
            continue

        try:
            # Load data
            weather_data = load_weather_data_from_csv(csv_path)

            if len(weather_data) < 10:
                skipped_no_csv += 1
                continue

            # Build TriggerDef and compute
            trigger_def = _build_trigger_def(trigger)
            report = compute_basis_risk(trigger_def, weather_data)

            # Serialize to JSON
            report_json = report.model_dump_json(indent=2)
            output_path.write_text(report_json, encoding="utf-8")

            rho = report.spearman_rho
            score = report.lloyds_score
            computed += 1
            computed_by_peril[trigger.peril] = computed_by_peril.get(trigger.peril, 0) + 1

            if computed % 20 == 0 or computed <= 5:
                print(f"  [{computed}] {trigger.id}: rho={rho:.3f}, lloyds={score:.1f}, periods={len(weather_data)}")

        except Exception as e:
            errors += 1
            print(f"  ERROR {trigger.id}: {e}")

    print(f"\nDone: {computed} computed, {skipped_exists} already existed, {skipped_no_csv} no CSV, {errors} errors")
    if computed_by_peril:
        print(f"  By peril: {', '.join(f'{k}={v}' for k, v in sorted(computed_by_peril.items()))}")
    print(f"Reports at: {OUTPUT_DIR}/")

    # Summary stats
    if computed > 0:
        import statistics
        rhos = []
        for p in OUTPUT_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                r = data.get("spearman_rho")
                if r is not None and r == r:  # not NaN
                    rhos.append(r)
            except Exception:
                pass
        if rhos:
            print(f"\nRho distribution ({len(rhos)} reports):")
            print(f"  mean={statistics.mean(rhos):.3f}, median={statistics.median(rhos):.3f}")
            print(f"  min={min(rhos):.3f}, max={max(rhos):.3f}")
            high = sum(1 for r in rhos if r >= 0.7)
            mid = sum(1 for r in rhos if 0.4 <= r < 0.7)
            low = sum(1 for r in rhos if r < 0.4)
            print(f"  high (>=0.7): {high}, medium (0.4-0.7): {mid}, low (<0.4): {low}")


if __name__ == "__main__":
    main()
