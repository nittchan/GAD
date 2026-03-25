"""
Centralised data paths. All file I/O goes through these constants.
On Fly.io with a mounted volume, DATA_ROOT=/data.
Locally, DATA_ROOT=./data (relative to project root).
"""

import os
from pathlib import Path

# If /data exists and is writable (Fly.io volume), use it. Otherwise use local ./data
_FLY_VOLUME = Path("/data")
if _FLY_VOLUME.is_dir():
    DATA_ROOT = _FLY_VOLUME
else:
    DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

CACHE_DIR = DATA_ROOT / "monitor_cache"
SERIES_DIR = DATA_ROOT / "series"
BASIS_RISK_DIR = DATA_ROOT / "basis_risk"
ORACLE_DIR = DATA_ROOT / "oracle"
ORACLE_LOG_DIR = DATA_ROOT / "oracle" / "determinations"
DB_PATH = DATA_ROOT / "gad.duckdb"
BACKUP_DIR = DATA_ROOT / "backups"
MODEL_DIR = DATA_ROOT / "models"
DIGEST_DIR = DATA_ROOT / "digest"
INTELLIGENCE_CACHE_DIR = DATA_ROOT / "intelligence_cache"

# Ensure directories exist
for _d in [CACHE_DIR, SERIES_DIR, BASIS_RISK_DIR, ORACLE_DIR, ORACLE_LOG_DIR,
           BACKUP_DIR, MODEL_DIR, DIGEST_DIR, INTELLIGENCE_CACHE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
