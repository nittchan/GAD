"""Webhook delivery with retry and dead-letter queue."""
import hashlib
import hmac
import json
import logging
import time
import httpx
from datetime import datetime, timezone

log = logging.getLogger("gad.engine.webhook")


def deliver_webhook(url, payload, secret, max_retries=3):
    """POST signed payload to webhook URL with exponential backoff retry."""
    body = json.dumps(payload, default=str)
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Signature-SHA256": signature,
        "X-Timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for attempt in range(max_retries):
        try:
            resp = httpx.post(url, content=body, headers=headers, timeout=10)
            if resp.status_code < 400:
                return {"status": "delivered", "status_code": resp.status_code, "attempt": attempt + 1}
            if resp.status_code < 500:  # Client error, don't retry
                return {"status": "rejected", "status_code": resp.status_code, "attempt": attempt + 1}
        except Exception as e:
            log.debug(f"Webhook attempt {attempt+1} failed: {e}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s

    # Dead letter — write to Supabase webhook_failures table
    _write_dead_letter(url, payload, "max_retries_exceeded")
    return {"status": "dead_letter", "attempt": max_retries}


def _write_dead_letter(url, payload, reason):
    """Write failed webhook to dead-letter queue (Supabase)."""
    try:
        import os
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL", "")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not supabase_url or not service_key:
            log.warning(f"Dead letter: {url} — {reason} (no Supabase)")
            return
        client = create_client(supabase_url, service_key)
        client.table("webhook_failures").insert({
            "webhook_url": url,
            "payload": json.dumps(payload, default=str),
            "reason": reason,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        log.warning(f"Dead letter write failed: {e}")
