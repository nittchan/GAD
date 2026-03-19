"""
Supabase auth widgets for sign-in and session.
Requires SUPABASE_URL and SUPABASE_ANON_KEY. Google OAuth configured in Supabase dashboard.
"""

from __future__ import annotations

import os
from typing import Any

_sb: Any = None


def get_supabase():
    global _sb
    if _sb is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            return None
        try:
            from supabase import create_client
            return create_client(url, key)
        except Exception:
            return None
    return _sb


def render_auth_widget():
    """
    Renders sign-in UI if not authenticated.
    Returns the current user dict or None.
    """
    sb = get_supabase()
    if not sb:
        return None

    import streamlit as st
    session = st.session_state.get("supabase_session")
    if session:
        return getattr(session, "user", None)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Sign in to save triggers")
        st.caption("Free account. No credit card.")

        if st.button("Continue with Google", use_container_width=True):
            try:
                result = sb.auth.sign_in_with_oauth(
                    {"provider": "google"}
                )
                if getattr(result, "url", None):
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0; url={result.url}">',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(str(e))

        st.divider()
        email = st.text_input("Email", key="auth_email")
        if st.button("Send magic link", use_container_width=True, key="auth_magic"):
            try:
                sb.auth.sign_in_with_otp({"email": email})
                st.success("Check your email for a sign-in link.")
            except Exception as e:
                st.error(str(e))

    return None


def handle_oauth_callback():
    """Call on the account page to capture the OAuth return."""
    import streamlit as st
    sb = get_supabase()
    if not sb:
        return None
    params = st.query_params
    if "code" in params or "access_token" in params:
        try:
            session = sb.auth.get_session()
            if session:
                st.session_state["supabase_session"] = session
                st.query_params.clear()
                return getattr(session, "user", None)
        except Exception:
            pass
    return None


def current_user():
    import streamlit as st
    session = st.session_state.get("supabase_session")
    if session:
        return getattr(session, "user", None)
    return None


def require_auth():
    """Use in any page that requires a logged-in user."""
    user = current_user()
    if not user:
        render_auth_widget()
        st.stop()
    return user
