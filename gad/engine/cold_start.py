"""
Cold-start inference: for triggers with <30 observations, infer distribution
from 5 nearest peers using weighted-average.
"""
import logging

from gad.engine.peer_index import compute_peers
from gad.engine.timeseries import get_trigger_stats, has_enough_observations
from gad.engine.db_read import get_observation_count

log = logging.getLogger("gad.engine.cold_start")


def infer_cold_start(trigger_id):
    """Infer distribution from peers for a trigger with insufficient data."""
    if has_enough_observations(trigger_id, minimum=30):
        return None  # Not cold-start — has enough data

    peers = compute_peers(trigger_id, top_n=5)
    if not peers:
        return None

    weighted_mean = 0
    weighted_rate = 0
    total_weight = 0
    peer_details = []

    for peer in peers:
        stats = get_trigger_stats(peer["trigger_id"], days=365)
        if stats and stats.get("mean") is not None:
            w = peer["similarity"]
            weighted_mean += stats["mean"] * w
            weighted_rate += stats["firing_rate"] * w
            total_weight += w
            peer_details.append(
                {**peer, "mean": stats["mean"], "firing_rate": stats["firing_rate"]}
            )

    if total_weight == 0:
        return None

    return {
        "trigger_id": trigger_id,
        "source": "cold_start_inference",
        "inferred_mean": round(weighted_mean / total_weight, 4),
        "inferred_firing_rate": round(weighted_rate / total_weight, 4),
        "peers_used": len(peer_details),
        "peer_details": peer_details,
    }


def check_graduation(trigger_id):
    """Check if trigger should graduate from cold-start to direct measurement."""
    if has_enough_observations(trigger_id, minimum=30):
        return {
            "trigger_id": trigger_id,
            "graduated": True,
            "message": "Sufficient observations — using direct measurement",
        }
    count = get_observation_count(trigger_id) or 0
    return {
        "trigger_id": trigger_id,
        "graduated": False,
        "observations": count,
        "needed": 30,
        "progress": round(count / 30 * 100, 1),
    }
