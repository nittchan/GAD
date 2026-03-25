#!/usr/bin/env python3
"""
Restore a DuckDB backup from R2 or local .gz file.

Usage:
    python scripts/restore_duckdb.py                          # List available R2 backups
    python scripts/restore_duckdb.py --latest                 # Restore latest R2 backup
    python scripts/restore_duckdb.py --key backups/gad-20260325-120000.duckdb.gz
    python scripts/restore_duckdb.py --file /path/to/gad-20260325-120000.duckdb.gz
"""
import argparse
import gzip
import hashlib
import logging
import os
import shutil
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("restore_duckdb")


def compute_checksum(filepath: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def list_r2_backups():
    """List available backups in R2."""
    from gad.engine.r2_upload import _init, _client, _bucket, _enabled
    _init()
    if not _enabled or not _client:
        log.error("R2 not configured. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.")
        return []

    try:
        response = _client.list_objects_v2(Bucket=_bucket, Prefix="backups/")
        contents = response.get("Contents", [])
        backups = sorted(contents, key=lambda x: x["LastModified"], reverse=True)
        for b in backups:
            size_mb = b["Size"] / (1024 * 1024)
            log.info(f"  {b['Key']}  ({size_mb:.1f} MB, {b['LastModified']})")
        return backups
    except Exception as e:
        log.error(f"Failed to list R2 backups: {e}")
        return []


def download_from_r2(key: str, dest: Path) -> bool:
    """Download a backup file from R2."""
    from gad.engine.r2_upload import _init, _client, _bucket, _enabled
    _init()
    if not _enabled or not _client:
        log.error("R2 not configured.")
        return False

    try:
        log.info(f"Downloading {key} from R2...")
        response = _client.get_object(Bucket=_bucket, Key=key)
        with open(dest, "wb") as f:
            shutil.copyfileobj(response["Body"], f)
        log.info(f"Downloaded to {dest} ({dest.stat().st_size} bytes)")
        return True
    except Exception as e:
        log.error(f"R2 download failed: {e}")
        return False


def restore_from_gz(gz_path: Path, db_path: Path) -> bool:
    """Gunzip a backup file and place it as the active DuckDB database."""
    if not gz_path.exists():
        log.error(f"Backup file not found: {gz_path}")
        return False

    # Safety: back up existing DB if present
    if db_path.exists():
        safety_path = db_path.with_suffix(".duckdb.pre-restore")
        shutil.copy2(db_path, safety_path)
        log.info(f"Existing DB backed up to {safety_path}")

    try:
        with gzip.open(gz_path, "rb") as f_in, open(db_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        checksum = compute_checksum(db_path)
        log.info(f"Restored: {db_path} ({db_path.stat().st_size} bytes)")
        log.info(f"SHA-256:  {checksum}")

        # Quick validation: try opening with DuckDB
        try:
            import duckdb
            conn = duckdb.connect(str(db_path), read_only=True)
            tables = conn.execute("SHOW TABLES").fetchall()
            conn.close()
            log.info(f"Validation: {len(tables)} tables found — {[t[0] for t in tables]}")
        except Exception as e:
            log.warning(f"Validation warning (DB may still be usable): {e}")

        return True
    except Exception as e:
        log.error(f"Restore failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Restore DuckDB from R2 or local backup")
    parser.add_argument("--latest", action="store_true", help="Restore the latest R2 backup")
    parser.add_argument("--key", type=str, help="R2 object key to restore (e.g. backups/gad-20260325-120000.duckdb.gz)")
    parser.add_argument("--file", type=str, help="Local .gz file to restore from")
    args = parser.parse_args()

    from gad.config import DB_PATH, BACKUP_DIR

    if args.file:
        gz_path = Path(args.file)
        restore_from_gz(gz_path, DB_PATH)
        return

    if not args.latest and not args.key:
        log.info("Available R2 backups:")
        backups = list_r2_backups()
        if not backups:
            log.info("  (none found)")
        log.info("\nUse --latest or --key <key> to restore.")
        return

    if args.latest:
        backups = list_r2_backups()
        if not backups:
            log.error("No backups found in R2")
            return
        key = backups[0]["Key"]
    else:
        key = args.key

    gz_dest = BACKUP_DIR / Path(key).name
    if download_from_r2(key, gz_dest):
        restore_from_gz(gz_dest, DB_PATH)


if __name__ == "__main__":
    main()
