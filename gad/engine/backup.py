"""DuckDB backup to R2. CHECKPOINT before copy. Gzip and upload."""
import gzip
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("gad.engine.backup")


def backup_to_r2():
    """CHECKPOINT, gzip, upload to R2."""
    from gad.config import DB_PATH, BACKUP_DIR

    try:
        from gad.engine.db import get_connection
        conn = get_connection()
        conn.execute("CHECKPOINT")  # Force WAL flush before copy
        log.info("DuckDB CHECKPOINT complete")
    except Exception as e:
        log.warning(f"CHECKPOINT failed: {e}")
        return False

    if not DB_PATH.exists():
        log.warning("No DuckDB file to backup")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    gz_name = f"gad-{timestamp}.duckdb.gz"
    gz_path = BACKUP_DIR / gz_name

    try:
        with open(DB_PATH, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        log.info(f"Backup created: {gz_path} ({gz_path.stat().st_size} bytes)")
    except Exception as e:
        log.error(f"Backup gzip failed: {e}")
        return False

    # Upload to R2
    try:
        from gad.engine.r2_upload import _init, _client, _bucket, _enabled
        _init()
        if _enabled and _client:
            _client.put_object(
                Bucket=_bucket,
                Key=f"backups/{gz_name}",
                Body=gz_path.read_bytes(),
                ContentType="application/gzip",
            )
            log.info(f"Backup uploaded to R2: backups/{gz_name}")
        else:
            log.info("R2 not configured — backup saved locally only")
    except Exception as e:
        log.warning(f"R2 upload failed: {e}")

    return True


def prune_old_backups(keep_days=30):
    """Delete local backup files older than keep_days."""
    from gad.config import BACKUP_DIR

    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    pruned = 0

    try:
        for gz_file in BACKUP_DIR.glob("gad-*.duckdb.gz"):
            # Parse timestamp from filename: gad-YYYYMMDD-HHMMSS.duckdb.gz
            try:
                name_part = gz_file.stem.replace(".duckdb", "")  # gad-YYYYMMDD-HHMMSS
                ts_str = name_part[4:]  # YYYYMMDD-HHMMSS
                file_ts = datetime.strptime(ts_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
                if file_ts < cutoff:
                    gz_file.unlink()
                    pruned += 1
                    log.info(f"Pruned old backup: {gz_file.name}")
            except (ValueError, IndexError):
                continue  # Skip files with unexpected names

        log.info(f"Backup prune complete: {pruned} files removed (keep_days={keep_days})")
    except Exception as e:
        log.warning(f"Backup prune failed: {e}")

    return pruned
