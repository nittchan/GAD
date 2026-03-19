"""
Load weather_data from CSV for compute_basis_risk.
CSV must have period, index_value (or trigger_value), and loss_proxy (or loss_event).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


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
