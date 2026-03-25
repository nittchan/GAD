"""Write helpers for DuckDB. One function per table. All wrapped in try/except."""
import json
import logging
from datetime import datetime, timezone

log = logging.getLogger("gad.engine.db_write")


def write_observation(trigger_id, value, fired, data_source, raw_data=None):
    """Insert a single trigger observation."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO trigger_observations (trigger_id, observed_at, value, fired, data_source, raw_json) VALUES (?, ?, ?, ?, ?, ?)",
            [trigger_id, datetime.now(timezone.utc), value, fired, data_source, json.dumps(raw_data) if raw_data else None]
        )
    except Exception as e:
        log.warning(f"Failed to write observation for {trigger_id}: {e}")


def write_distribution(trigger_id, time_window, mean, std, median, p5, p25, p75, p95, firing_rate, observation_count):
    """Insert or update a trigger distribution summary."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO trigger_distributions (trigger_id, time_window, computed_at, mean, std, median, p5, p25, p75, p95, firing_rate, observation_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [trigger_id, time_window, datetime.now(timezone.utc), mean, std, median, p5, p25, p75, p95, firing_rate, observation_count]
        )
    except Exception as e:
        log.warning(f"Failed to write distribution for {trigger_id}: {e}")


def write_drift_alert(trigger_id, drift_type, old_value, new_value, severity="medium"):
    """Insert a drift alert."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO drift_alerts (trigger_id, detected_at, drift_type, old_value, new_value, severity) VALUES (?, ?, ?, ?, ?, ?)",
            [trigger_id, datetime.now(timezone.utc), drift_type, old_value, new_value, severity]
        )
    except Exception as e:
        log.warning(f"Failed to write drift alert for {trigger_id}: {e}")


def write_threshold_suggestion(trigger_id, current_threshold, suggested_threshold, method, confidence, observation_count):
    """Insert a threshold suggestion."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO threshold_suggestions (trigger_id, computed_at, current_threshold, suggested_threshold, method, confidence, observation_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [trigger_id, datetime.now(timezone.utc), current_threshold, suggested_threshold, method, confidence, observation_count]
        )
    except Exception as e:
        log.warning(f"Failed to write threshold suggestion for {trigger_id}: {e}")


def write_peer(trigger_id, peer_trigger_id, similarity):
    """Insert a peer relationship."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO trigger_peers (trigger_id, peer_trigger_id, similarity, computed_at) VALUES (?, ?, ?, ?)",
            [trigger_id, peer_trigger_id, similarity, datetime.now(timezone.utc)]
        )
    except Exception as e:
        log.warning(f"Failed to write peer for {trigger_id}: {e}")


def write_correlation(trigger_a, trigger_b, phi_coefficient, overlap_count):
    """Insert a trigger correlation."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO trigger_correlations (trigger_a, trigger_b, phi_coefficient, overlap_count, computed_at) VALUES (?, ?, ?, ?, ?)",
            [trigger_a, trigger_b, phi_coefficient, overlap_count, datetime.now(timezone.utc)]
        )
    except Exception as e:
        log.warning(f"Failed to write correlation for {trigger_a}-{trigger_b}: {e}")


def write_model_version(version_id, trigger_id, model_type, parameters, metrics):
    """Insert a model version record."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO model_versions (version_id, created_at, trigger_id, model_type, parameters, metrics) VALUES (?, ?, ?, ?, ?, ?)",
            [version_id, datetime.now(timezone.utc), trigger_id, model_type,
             json.dumps(parameters) if isinstance(parameters, dict) else parameters,
             json.dumps(metrics) if isinstance(metrics, dict) else metrics]
        )
    except Exception as e:
        log.warning(f"Failed to write model version {version_id}: {e}")


def write_seasonal_profile(trigger_id, month, mean, std, firing_rate):
    """Insert a seasonal profile entry."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO seasonal_profiles (trigger_id, month, mean, std, firing_rate, computed_at) VALUES (?, ?, ?, ?, ?, ?)",
            [trigger_id, month, mean, std, firing_rate, datetime.now(timezone.utc)]
        )
    except Exception as e:
        log.warning(f"Failed to write seasonal profile for {trigger_id} month {month}: {e}")
