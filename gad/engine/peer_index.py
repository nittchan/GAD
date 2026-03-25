"""
Peer index: find similar triggers using cosine similarity on feature vectors.
Features: lat, lon, threshold, firing_rate, mean_value, peril_type (one-hot).
Top-5 peers per trigger. Weekly recompute.
"""
import logging

import numpy as np

from gad.monitor.triggers import GLOBAL_TRIGGERS, PERIL_LABELS
from gad.monitor.climate_zones import get_climate_zone
from gad.engine.db_read import get_observation_count, get_peers
from gad.engine.db_write import write_peer
from gad.engine.model_registry import register_model_version

log = logging.getLogger("gad.engine.peer_index")


def _build_feature_vector(trigger, climate_zone, obs_stats):
    """Build a numeric feature vector for cosine similarity."""
    peril_list = list(PERIL_LABELS.keys())
    peril_onehot = [1.0 if trigger.peril == p else 0.0 for p in peril_list]

    lat_norm = trigger.lat / 90.0
    lon_norm = trigger.lon / 180.0
    threshold_norm = min(trigger.threshold / 1000.0, 1.0)  # crude normalization

    firing_rate = obs_stats.get("firing_rate", 0) if obs_stats else 0
    mean_val = obs_stats.get("mean", 0) if obs_stats else 0
    mean_norm = min(abs(mean_val) / 500.0, 1.0) if mean_val else 0

    return np.array(
        [lat_norm, lon_norm, threshold_norm, firing_rate, mean_norm] + peril_onehot
    )


def compute_peers(trigger_id, top_n=5):
    """Find top-N most similar triggers using cosine similarity."""
    target = next((t for t in GLOBAL_TRIGGERS if t.id == trigger_id), None)
    if not target:
        return []

    from gad.engine.timeseries import get_trigger_stats

    target_stats = get_trigger_stats(trigger_id, days=365)
    target_zone = get_climate_zone(target.lat, target.lon)
    target_vec = _build_feature_vector(target, target_zone, target_stats)

    similarities = []
    for t in GLOBAL_TRIGGERS:
        if t.id == trigger_id:
            continue
        try:
            stats = get_trigger_stats(t.id, days=365)
            zone = get_climate_zone(t.lat, t.lon)
            vec = _build_feature_vector(t, zone, stats)

            # Cosine similarity
            dot = np.dot(target_vec, vec)
            norm = np.linalg.norm(target_vec) * np.linalg.norm(vec)
            sim = float(dot / norm) if norm > 0 else 0

            similarities.append({"trigger_id": t.id, "similarity": round(sim, 4)})
        except Exception:
            continue

    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    top_peers = similarities[:top_n]

    # Write to DuckDB
    for peer in top_peers:
        write_peer(trigger_id, peer["trigger_id"], peer["similarity"])

    return top_peers


def compute_all_peers():
    """Compute peers for all triggers with observations. Weekly job."""
    count = 0
    for t in GLOBAL_TRIGGERS:
        try:
            obs_count = get_observation_count(t.id)
            if obs_count and obs_count >= 10:
                compute_peers(t.id)
                count += 1
        except Exception:
            continue
    log.info(f"Peer index: computed for {count} triggers")
    register_model_version(
        None, "peer_index", {"top_n": 5}, {"triggers_computed": count}
    )


def detect_outliers():
    """Flag triggers >2 sigma from peer median firing rate."""
    from gad.engine.timeseries import get_trigger_stats

    outliers = []
    for t in GLOBAL_TRIGGERS:
        try:
            peers_df = get_peers(t.id)
            if peers_df is None or peers_df.empty:
                continue
            # Get firing rates of peers
            peer_rates = []
            for _, row in peers_df.iterrows():
                ps = get_trigger_stats(row["peer_trigger_id"], days=90)
                if ps and ps.get("firing_rate") is not None:
                    peer_rates.append(ps["firing_rate"])
            if len(peer_rates) < 3:
                continue
            median_rate = np.median(peer_rates)
            std_rate = np.std(peer_rates)
            my_stats = get_trigger_stats(t.id, days=90)
            if (
                my_stats
                and my_stats.get("firing_rate") is not None
                and std_rate > 0
            ):
                z = abs(my_stats["firing_rate"] - median_rate) / std_rate
                if z > 2.0:
                    outliers.append(
                        {
                            "trigger_id": t.id,
                            "z_score": round(z, 2),
                            "firing_rate": my_stats["firing_rate"],
                            "peer_median": round(median_rate, 4),
                        }
                    )
        except Exception:
            continue
    log.info(f"Outlier detection: {len(outliers)} outliers found")
    return outliers
