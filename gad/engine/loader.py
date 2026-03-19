"""
Load weather_data from CSV for compute_basis_risk.
CSV must have period, index_value (or trigger_value), and loss_proxy (or loss_event).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_weather_data_from_csv(
    csv_path: str | Path,
) -> list[dict]:
    """
    Read a series CSV and return list of {period, trigger_value, loss_proxy}.
    Expects columns: period, index_value (or trigger_value), and loss_proxy or loss_event.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    df = pd.read_csv(path)
    if "index_value" in df.columns:
        trigger_col = "index_value"
    elif "trigger_value" in df.columns:
        trigger_col = "trigger_value"
    else:
        raise ValueError("CSV must have 'index_value' or 'trigger_value'")
    if "loss_proxy" not in df.columns:
        if "loss_event" in df.columns:
            df = df.assign(loss_proxy=df["loss_event"].astype(float))
        else:
            raise ValueError("CSV must have 'loss_proxy' or 'loss_event'")
    out: list[dict] = []
    for _, row in df.iterrows():
        out.append({
            "period": str(row["period"]),
            "trigger_value": float(row[trigger_col]),
            "loss_proxy": float(row["loss_proxy"]),
        })
    return out


def load_from_manifest(
    manifest_path: str | Path,
    trigger_key: str,
    data_root: str | Path,
) -> list[dict]:
    """
    Compatibility adapter for legacy manifest-driven datasets.
    Reads data/manifest.yaml-style mapping and returns weather_data list
    suitable for gad.engine.compute_basis_risk(trigger, weather_data).
    """
    manifest_file = Path(manifest_path)
    if not manifest_file.is_file():
        raise FileNotFoundError(str(manifest_file))

    raw = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Manifest YAML root must be a mapping")

    triggers = raw.get("triggers")
    if not isinstance(triggers, dict):
        raise ValueError("Manifest must include a 'triggers' mapping")

    ref = triggers.get(trigger_key)
    if not isinstance(ref, dict):
        raise KeyError(f"Trigger key {trigger_key!r} not found in manifest")

    primary_series_csv = ref.get("primary_series_csv")
    if not isinstance(primary_series_csv, str) or not primary_series_csv.strip():
        raise ValueError(
            f"Manifest trigger {trigger_key!r} must define non-empty primary_series_csv"
        )

    csv_path = Path(data_root) / primary_series_csv
    return load_weather_data_from_csv(csv_path)
