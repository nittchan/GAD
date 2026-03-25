"""Searchable trigger selector helpers.

With 521+ triggers the raw selectbox is hard to navigate.  These helpers
build rich display labels that Streamlit's built-in type-to-filter can
match against city, peril, country, and trigger name.

Format examples:
  "Delhi DEL — Flight Delay (India)"
  "California Wildfire — Wildfire (USA)"
  "Singapore Changi Congestion — Marine / Shipping"
"""

from __future__ import annotations

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS, MonitorTrigger


def build_trigger_label(t: MonitorTrigger) -> str:
    """Return a human-friendly, searchable label for a trigger."""
    peril = PERIL_LABELS.get(t.peril, t.peril)

    # Extract country hint from location_label (typically after last comma)
    country = ""
    if t.location_label and "," in t.location_label:
        country = t.location_label.rsplit(",", 1)[-1].strip()

    # Append country if it adds searchable info not already in the name
    if country and country.lower() not in t.name.lower():
        return f"{t.name} — {peril} ({country})"
    return f"{t.name} — {peril}"


def build_trigger_options() -> tuple[list[str], dict[str, str]]:
    """Return (sorted_labels, label_to_id_map) for all global triggers.

    Labels are sorted alphabetically so the selectbox is easy to scan.
    """
    label_map: dict[str, str] = {}
    for t in GLOBAL_TRIGGERS:
        label = build_trigger_label(t)
        # Guard against unlikely duplicate labels
        if label in label_map:
            label = f"{label} [{t.id}]"
        label_map[label] = t.id

    sorted_labels = sorted(label_map.keys())
    return sorted_labels, label_map
