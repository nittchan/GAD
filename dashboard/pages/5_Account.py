"""Account — saved triggers and notification subscriptions from Supabase."""

from __future__ import annotations

import streamlit as st

from dashboard.components.auth import current_user, render_auth_widget, handle_oauth_callback, get_supabase


def _client_with_session():
    """Supabase client with refreshed session so RLS applies. Refreshes token to avoid 401s from expired JWTs."""
    sb = get_supabase()
    if not sb:
        return None
    session = st.session_state.get("supabase_session")
    if not session:
        return sb
    inner = getattr(session, "session", session)
    refresh_token = getattr(inner, "refresh_token", None)
    if getattr(session, "get", None):
        refresh_token = refresh_token or session.get("refresh_token")
    try:
        if refresh_token:
            refreshed = sb.auth.refresh_session(refresh_token)
            st.session_state["supabase_session"] = refreshed
            sb.auth.set_session(
                refreshed.session.access_token,
                refreshed.session.refresh_token,
            )
        else:
            access_token = getattr(inner, "access_token", None)
            rt = getattr(inner, "refresh_token", None)
            if access_token and rt:
                sb.auth.set_session(access_token, rt)
    except Exception:
        # Use existing token; let the query fail naturally if expired
        access_token = getattr(inner, "access_token", None)
        rt = getattr(inner, "refresh_token", None)
        if access_token and rt:
            try:
                sb.auth.set_session(access_token, rt)
            except Exception:
                pass
    return sb


def main():
    st.set_page_config(page_title="Account | GAD", layout="wide")
    user = handle_oauth_callback() or current_user()
    if not user:
        render_auth_widget()
        return

    user_id = getattr(user, "id", None)
    if not user_id:
        st.warning("Could not read user id.")
        return

    st.markdown("## Your account")
    st.caption(f"Signed in as **{getattr(user, 'email', 'user')}**")
    st.divider()

    sb = _client_with_session()
    if not sb:
        st.info("Supabase is not configured. Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` to see saved triggers and notifications.")
        return

    # Saved triggers (join to trigger_defs)
    st.markdown("### Saved triggers")
    try:
        r = sb.table("saved_triggers").select("*, trigger_defs(name, description, peril, threshold, threshold_unit, created_at)").eq("user_id", str(user_id)).order("saved_at", desc=True).execute()
        rows = r.data if hasattr(r, "data") else []
        if not rows:
            st.caption("Triggers you save from the guided or expert flow appear here. Save a trigger to see it.")
        else:
            for row in rows:
                td = row.get("trigger_defs") or {}
                name = td.get("name") or "Unnamed trigger"
                peril = td.get("peril", "")
                st.markdown(f"- **{name}** — {peril.replace('_', ' ')}")
                st.caption(f"Saved {row.get('saved_at', '')[:10]}")
    except Exception as e:
        st.caption(f"Could not load saved triggers. (Tables may not exist yet.) {e}")

    st.divider()
    st.markdown("### Notification subscriptions")
    try:
        r = sb.table("trigger_notifications").select("*, trigger_defs(name, peril)").eq("user_id", str(user_id)).eq("active", True).execute()
        rows = r.data if hasattr(r, "data") else []
        if not rows:
            st.caption("Subscribe to data-update alerts for a trigger (v0.2). No active subscriptions.")
        else:
            for row in rows:
                td = row.get("trigger_defs") or {}
                name = td.get("name") or "Unnamed trigger"
                st.markdown(f"- **{name}** → {row.get('email', '')}")
    except Exception as e:
        st.caption(f"Could not load notifications. {e}")


if __name__ == "__main__":
    main()

# ── Footer ──
from dashboard.components.footer import render_footer
render_footer()
