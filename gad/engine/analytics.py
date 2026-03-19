"""
Activity event logging. Fire-and-forget writes to Supabase gad_events.
Use SUPABASE_SERVICE_KEY so inserts bypass RLS.
"""

from __future__ import annotations

import logging
import os
import uuid
from uuid import UUID

from gad.engine.models import GadEvent

# EVENT TYPES (exhaustive — add new ones here only)
# trigger_viewed, trigger_created, trigger_modified, trigger_made_public,
# report_computed, report_downloaded_pdf, lloyds_checklist_viewed,
# yaml_toggled, comparison_started, api_key_created, notification_subscribed,
# determination_viewed

_sb = None


def _supabase():
    global _sb
    if _sb is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            return None
        try:
            from supabase import create_client
            _sb = create_client(url, key)
        except Exception as e:
            logging.getLogger(__name__).warning("Supabase client init failed: %s", e)
            return None
    return _sb


def track(
    event_type: str,
    session_id: str,
    user_id: UUID | None = None,
    trigger_id: UUID | None = None,
    report_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Fire-and-forget event write. Failures are logged, never raised.
    Call on every meaningful user action. Uses SUPABASE_SERVICE_KEY to bypass RLS.
    """
    try:
        client = _supabase()
        if not client:
            return
        event = GadEvent(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            trigger_id=trigger_id,
            report_id=report_id,
            metadata=metadata or {},
        )
        client.table("gad_events").insert(event.model_dump(mode="json")).execute()
    except Exception as e:
        logging.getLogger("gad.analytics").warning("Event tracking failed: %s", e)


def get_or_create_session_id() -> str:
    """
    Anonymous session token — persisted in Streamlit session state.
    Survives page reloads within a browser session. Not a user ID.
    """
    try:
        import streamlit as st
        if "gad_session_id" not in st.session_state:
            st.session_state["gad_session_id"] = str(uuid.uuid4())
        return st.session_state["gad_session_id"]
    except Exception:
        return str(uuid.uuid4())
