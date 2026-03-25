"""Read helpers for DuckDB. Fast analytical queries."""
import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger("gad.engine.db_read")


def get_observations(trigger_id, days=90):
    """Return observations for a trigger as a DataFrame."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return conn.execute(
            "SELECT * FROM trigger_observations WHERE trigger_id = ? AND observed_at >= ? ORDER BY observed_at",
            [trigger_id, cutoff]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read observations for {trigger_id}: {e}")
        return None


def get_distribution(trigger_id, window="30d"):
    """Return the latest distribution summary for a trigger and window."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        return conn.execute(
            "SELECT * FROM trigger_distributions WHERE trigger_id = ? AND window = ? ORDER BY computed_at DESC LIMIT 1",
            [trigger_id, window]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read distribution for {trigger_id}: {e}")
        return None


def get_drift_alerts(trigger_id, days=30):
    """Return recent drift alerts for a trigger."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return conn.execute(
            "SELECT * FROM drift_alerts WHERE trigger_id = ? AND detected_at >= ? ORDER BY detected_at DESC",
            [trigger_id, cutoff]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read drift alerts for {trigger_id}: {e}")
        return None


def get_threshold_suggestion(trigger_id):
    """Return the latest threshold suggestion for a trigger."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        return conn.execute(
            "SELECT * FROM threshold_suggestions WHERE trigger_id = ? ORDER BY computed_at DESC LIMIT 1",
            [trigger_id]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read threshold suggestion for {trigger_id}: {e}")
        return None


def get_peers(trigger_id, limit=10):
    """Return peer triggers ranked by similarity."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        return conn.execute(
            "SELECT * FROM trigger_peers WHERE trigger_id = ? ORDER BY similarity DESC LIMIT ?",
            [trigger_id, limit]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read peers for {trigger_id}: {e}")
        return None


def get_correlations(trigger_id, min_phi=0.3):
    """Return correlated triggers above a phi threshold."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        return conn.execute(
            "SELECT * FROM trigger_correlations WHERE (trigger_a = ? OR trigger_b = ?) AND phi_coefficient >= ? ORDER BY phi_coefficient DESC",
            [trigger_id, trigger_id, min_phi]
        ).fetchdf()
    except Exception as e:
        log.warning(f"Failed to read correlations for {trigger_id}: {e}")
        return None


def get_observation_count(trigger_id):
    """Return total observation count for a trigger."""
    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        result = conn.execute(
            "SELECT COUNT(*) AS cnt FROM trigger_observations WHERE trigger_id = ?",
            [trigger_id]
        ).fetchone()
        return result[0] if result else 0
    except Exception as e:
        log.warning(f"Failed to read observation count for {trigger_id}: {e}")
        return 0
