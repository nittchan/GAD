# Supabase scope: profiles, saved_triggers, api_keys, gad_events, auth only.
# All analytical/learning tables are in DuckDB (this file).
"""
DuckDB analytical datastore. Single-writer (fetcher), read-only dashboard.
"""
import duckdb
import logging
import os
from pathlib import Path

log = logging.getLogger("gad.engine.db")

_conn = None  # Singleton connection (lazy init per eng review)


def get_connection(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Get or create singleton DuckDB connection."""
    global _conn
    if _conn is not None:
        return _conn
    if db_path is None:
        from gad.config import DB_PATH
        db_path = str(DB_PATH)
    _conn = duckdb.connect(str(db_path))
    init_db(_conn)
    return _conn


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they don't exist."""
    conn.execute("CREATE SEQUENCE IF NOT EXISTS obs_seq START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_observations (
            trigger_id VARCHAR NOT NULL,
            observed_at TIMESTAMP NOT NULL,
            value DOUBLE,
            fired BOOLEAN,
            data_source VARCHAR,
            raw_json VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_distributions (
            trigger_id VARCHAR NOT NULL,
            window VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL,
            mean DOUBLE, std DOUBLE, median DOUBLE,
            p5 DOUBLE, p25 DOUBLE, p75 DOUBLE, p95 DOUBLE,
            firing_rate DOUBLE, observation_count INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drift_alerts (
            trigger_id VARCHAR NOT NULL,
            detected_at TIMESTAMP NOT NULL,
            drift_type VARCHAR NOT NULL,
            old_value DOUBLE, new_value DOUBLE,
            severity VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS threshold_suggestions (
            trigger_id VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL,
            current_threshold DOUBLE,
            suggested_threshold DOUBLE,
            method VARCHAR,
            confidence VARCHAR,
            observation_count INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_peers (
            trigger_id VARCHAR NOT NULL,
            peer_trigger_id VARCHAR NOT NULL,
            similarity DOUBLE,
            computed_at TIMESTAMP NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trigger_correlations (
            trigger_a VARCHAR NOT NULL,
            trigger_b VARCHAR NOT NULL,
            phi_coefficient DOUBLE,
            overlap_count INTEGER,
            computed_at TIMESTAMP NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            version_id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,
            trigger_id VARCHAR,
            model_type VARCHAR,
            parameters VARCHAR,
            metrics VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seasonal_profiles (
            trigger_id VARCHAR NOT NULL,
            month INTEGER NOT NULL,
            mean DOUBLE, std DOUBLE,
            firing_rate DOUBLE,
            computed_at TIMESTAMP NOT NULL
        )
    """)
    log.info("DuckDB schema initialized (8 tables)")
