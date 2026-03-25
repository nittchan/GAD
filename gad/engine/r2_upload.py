"""
Upload oracle determinations to Cloudflare R2.

Optional — requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.
If credentials are missing, uploads are silently skipped.
Failures never block the fetcher.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("gad.engine.r2_upload")

_client = None
_bucket: str = ""
_enabled: bool = False
_initialized: bool = False


def _init() -> None:
    """Lazy-init the S3 client for R2. Called once on first upload attempt."""
    global _client, _bucket, _enabled, _initialized
    _initialized = True

    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        log.info("R2 upload DISABLED (missing R2_ACCOUNT_ID/R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY)")
        _enabled = False
        return

    try:
        import boto3
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        _bucket = os.environ.get("R2_BUCKET_NAME", "gad-oracle-determinations")
        _enabled = True
        log.info(f"R2 upload ENABLED (bucket={_bucket})")
    except ImportError:
        log.info("R2 upload DISABLED (boto3 not installed)")
        _enabled = False
    except Exception as e:
        log.warning(f"R2 upload init failed: {e}")
        _enabled = False


def upload_determination(determination_id: str, json_body: str) -> bool:
    """
    Upload a determination JSON to R2.
    Returns True on success, False on failure or skip.
    Never raises — failures are logged and swallowed.
    """
    if not _initialized:
        _init()
    if not _enabled:
        return False

    try:
        key = f"determinations/{determination_id}.json"
        _client.put_object(
            Bucket=_bucket,
            Key=key,
            Body=json_body.encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except Exception as e:
        log.warning(f"R2 upload failed for {determination_id}: {e}")
        return False


def upload_to_r2_key(key: str, json_body: str) -> bool:
    """
    Upload arbitrary JSON to an R2 key (e.g. trigger-status/{id}.json).
    Returns True on success, False on failure or skip.
    Never raises — failures are logged and swallowed.
    """
    if not _initialized:
        _init()
    if not _enabled:
        return False

    try:
        _client.put_object(
            Bucket=_bucket,
            Key=key,
            Body=json_body.encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except Exception as e:
        log.warning(f"R2 upload failed for {key}: {e}")
        return False
