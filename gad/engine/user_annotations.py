"""User trigger annotations with state snapshots."""
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("gad.engine.user_annotations")


def save_trigger_annotation(user_id: str, trigger_id: str, note: str = ""):
    """Save a trigger to user's watchlist with current state snapshot."""
    try:
        from supabase import create_client

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return None

        client = create_client(url, key)

        # Get current state for snapshot
        from gad.engine.timeseries import get_trigger_stats

        stats = get_trigger_stats(trigger_id, days=90)

        data = {
            "user_id": user_id,
            "trigger_id": trigger_id,
            "note": note,
            "firing_rate": stats["firing_rate"] if stats else None,
            "spearman_rho": None,  # Would need basis risk lookup
            "model_version_id": None,
            "threshold_percentile": None,
        }

        # Upsert
        result = (
            client.table("user_trigger_annotations")
            .upsert(data, on_conflict="user_id,trigger_id")
            .execute()
        )
        return result.data
    except Exception as e:
        log.warning(f"Failed to save annotation: {e}")
        return None


def get_user_annotations(user_id: str):
    """Get all annotations for a user."""
    try:
        from supabase import create_client

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return []
        client = create_client(url, key)
        result = (
            client.table("user_trigger_annotations")
            .select("*")
            .eq("user_id", user_id)
            .order("saved_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        log.warning(f"Failed to get annotations: {e}")
        return []


def delete_trigger_annotation(user_id: str, trigger_id: str):
    """Remove a trigger from user's watchlist."""
    try:
        from supabase import create_client

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return False
        client = create_client(url, key)
        client.table("user_trigger_annotations").delete().eq(
            "user_id", user_id
        ).eq("trigger_id", trigger_id).execute()
        return True
    except Exception as e:
        log.warning(f"Failed to delete annotation: {e}")
        return False


def get_watchlist_drift(user_id: str):
    """Check calibration drift since save for all user's watched triggers."""
    annotations = get_user_annotations(user_id)
    if not annotations:
        return []

    from gad.engine.timeseries import get_trigger_stats

    drift_items = []
    for ann in annotations:
        trigger_id = ann["trigger_id"]
        saved_rate = ann.get("firing_rate")

        current_stats = get_trigger_stats(trigger_id, days=90)
        current_rate = current_stats["firing_rate"] if current_stats else None

        drift = None
        if saved_rate is not None and current_rate is not None:
            drift = round(current_rate - saved_rate, 4)

        drift_items.append(
            {
                "trigger_id": trigger_id,
                "note": ann.get("note", ""),
                "saved_at": ann.get("saved_at"),
                "saved_firing_rate": saved_rate,
                "current_firing_rate": current_rate,
                "drift": drift,
            }
        )
    return drift_items
