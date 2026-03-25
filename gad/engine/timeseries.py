"""Thin read abstraction over DuckDB trigger observations."""
from datetime import datetime, timedelta, timezone
from gad.engine.db_read import get_observations, get_observation_count


def get_trigger_timeseries(trigger_id: str, days: int = 90):
    """Get observations as a list of dicts for a trigger."""
    df = get_observations(trigger_id, days=days)
    if df is None or df.empty:
        return []
    return df.to_dict('records')


def get_trigger_stats(trigger_id: str, days: int = 90):
    """Quick stats: count, mean, std, firing_rate."""
    df = get_observations(trigger_id, days=days)
    if df is None or df.empty:
        return None
    values = df['value'].dropna()
    fired = df['fired'].sum()
    total = len(df)
    return {
        'count': total,
        'mean': float(values.mean()) if len(values) > 0 else None,
        'std': float(values.std()) if len(values) > 1 else None,
        'firing_rate': float(fired / total) if total > 0 else 0,
        'first_observation': str(df['observed_at'].min()),
        'last_observation': str(df['observed_at'].max()),
    }


def has_enough_observations(trigger_id: str, minimum: int = 30) -> bool:
    """Check if trigger has enough data for statistical analysis."""
    count = get_observation_count(trigger_id)
    return count is not None and count >= minimum
