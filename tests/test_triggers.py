"""
Tests for the trigger registry (gad.monitor.triggers).
Validates counts, uniqueness, field population, and peril coverage.
"""

from __future__ import annotations

import pytest

from gad.monitor.triggers import (
    GLOBAL_TRIGGERS,
    PERIL_LABELS,
    MonitorTrigger,
    get_trigger_by_id,
    get_triggers_by_peril,
)
from gad.monitor.ports import ALL_PORTS


class TestTriggerCount:
    def test_total_count(self):
        assert len(GLOBAL_TRIGGERS) == 521, (
            f"Expected 521 triggers, got {len(GLOBAL_TRIGGERS)}"
        )


class TestPerilCoverage:
    @pytest.mark.parametrize("peril", PERIL_LABELS.keys())
    def test_each_peril_has_at_least_one_trigger(self, peril: str):
        triggers = get_triggers_by_peril(peril)
        assert len(triggers) >= 1, f"Peril '{peril}' has 0 triggers"


class TestTriggerIdUniqueness:
    def test_all_trigger_ids_are_unique(self):
        ids = [t.id for t in GLOBAL_TRIGGERS]
        duplicates = [tid for tid in ids if ids.count(tid) > 1]
        assert len(ids) == len(set(ids)), (
            f"Duplicate trigger IDs found: {set(duplicates)}"
        )


class TestTriggerFieldPopulation:
    @pytest.mark.parametrize(
        "trigger",
        GLOBAL_TRIGGERS,
        ids=lambda t: t.id,
    )
    def test_id_not_empty(self, trigger: MonitorTrigger):
        assert trigger.id, f"Trigger has empty id"

    @pytest.mark.parametrize(
        "trigger",
        GLOBAL_TRIGGERS,
        ids=lambda t: t.id,
    )
    def test_name_not_empty(self, trigger: MonitorTrigger):
        assert trigger.name, f"Trigger {trigger.id} has empty name"

    @pytest.mark.parametrize(
        "trigger",
        GLOBAL_TRIGGERS,
        ids=lambda t: t.id,
    )
    def test_data_source_not_empty(self, trigger: MonitorTrigger):
        assert trigger.data_source, f"Trigger {trigger.id} has empty data_source"


class TestMarineTriggers:
    def test_marine_trigger_count(self):
        marine = [t for t in GLOBAL_TRIGGERS if t.peril == "marine"]
        expected = 2 * len(ALL_PORTS)
        assert len(marine) == expected, (
            f"Expected {expected} marine triggers (2 per port), got {len(marine)}"
        )

    def test_each_port_has_congestion_and_dwell(self):
        marine_ids = {t.id for t in GLOBAL_TRIGGERS if t.peril == "marine"}
        for port in ALL_PORTS:
            congestion_id = f"marine-congestion-{port.id}"
            dwell_id = f"marine-dwell-{port.id}"
            assert congestion_id in marine_ids, f"Missing congestion trigger for {port.id}"
            assert dwell_id in marine_ids, f"Missing dwell trigger for {port.id}"

    def test_marine_triggers_use_aisstream(self):
        marine = [t for t in GLOBAL_TRIGGERS if t.peril == "marine"]
        for t in marine:
            assert t.data_source == "aisstream", (
                f"Marine trigger {t.id} uses {t.data_source}, expected aisstream"
            )


class TestFloodTriggers:
    def test_flood_triggers_have_valid_site_ids(self):
        flood = [t for t in GLOBAL_TRIGGERS if t.peril == "flood"]
        assert len(flood) > 0, "No flood triggers found"

        for t in flood:
            # Trigger ID format: flood-{site_id}
            assert t.id.startswith("flood-"), f"Flood trigger {t.id} does not start with 'flood-'"
            site_id = t.id.replace("flood-", "")
            # USGS site IDs are numeric strings (typically 8 digits)
            assert site_id.isdigit(), (
                f"Flood trigger {t.id}: site_id '{site_id}' is not numeric"
            )
            assert len(site_id) == 8, (
                f"Flood trigger {t.id}: site_id '{site_id}' is not 8 digits"
            )

    def test_flood_triggers_use_usgs_water(self):
        flood = [t for t in GLOBAL_TRIGGERS if t.peril == "flood"]
        for t in flood:
            assert t.data_source == "usgs_water", (
                f"Flood trigger {t.id} uses {t.data_source}, expected usgs_water"
            )


class TestCycloneTriggers:
    def test_cyclone_triggers_have_valid_lat_lon(self):
        cyclone = [t for t in GLOBAL_TRIGGERS if t.peril == "cyclone"]
        assert len(cyclone) > 0, "No cyclone triggers found"

        for t in cyclone:
            assert t.lat != 0.0 or t.lon != 0.0, (
                f"Cyclone trigger {t.id} has lat/lon (0, 0)"
            )
            assert -90 <= t.lat <= 90, (
                f"Cyclone trigger {t.id} has invalid lat {t.lat}"
            )
            assert -180 <= t.lon <= 180, (
                f"Cyclone trigger {t.id} has invalid lon {t.lon}"
            )

    def test_cyclone_triggers_use_noaa_nhc(self):
        cyclone = [t for t in GLOBAL_TRIGGERS if t.peril == "cyclone"]
        for t in cyclone:
            assert t.data_source == "noaa_nhc", (
                f"Cyclone trigger {t.id} uses {t.data_source}, expected noaa_nhc"
            )


class TestGetTriggerById:
    def test_returns_correct_trigger(self):
        trigger = get_trigger_by_id("quake-japan")
        assert trigger is not None
        assert trigger.id == "quake-japan"
        assert trigger.peril == "earthquake"

    def test_returns_none_for_unknown(self):
        result = get_trigger_by_id("nonexistent-trigger-id-xyz")
        assert result is None

    def test_returns_flight_delay_trigger(self):
        trigger = get_trigger_by_id("flight-delay-jfk")
        assert trigger is not None
        assert trigger.peril == "flight_delay"
        assert trigger.data_source == "opensky"

    def test_returns_marine_trigger(self):
        trigger = get_trigger_by_id("marine-congestion-port-singapore")
        assert trigger is not None
        assert trigger.peril == "marine"
        assert trigger.data_source == "aisstream"


class TestPerilLabels:
    def test_all_perils_in_triggers_have_labels(self):
        perils_in_triggers = {t.peril for t in GLOBAL_TRIGGERS}
        for peril in perils_in_triggers:
            assert peril in PERIL_LABELS, f"Peril '{peril}' missing from PERIL_LABELS"

    def test_label_values_are_non_empty_strings(self):
        for peril, label in PERIL_LABELS.items():
            assert isinstance(label, str) and label, (
                f"PERIL_LABELS['{peril}'] is empty or not a string"
            )
