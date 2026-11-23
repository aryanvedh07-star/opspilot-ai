








"""Supabase authentication and persistence helpers for OpsPilot AI.

This module is designed for a Streamlit app using Supabase Auth + RLS.
Only the publishable/anon key is used. Never put a Supabase secret/service-role
key in Streamlit client-facing code or in GitHub.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import streamlit as st


def _read_config() -> tuple[str, str]:
    """Read Supabase credentials from Streamlit Secrets or host environment."""
    try:
        url = str(st.secrets.get("SUPABASE_URL", "")).strip()
        key = str(st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "")).strip()
    except Exception:
        url, key = "", ""

    # Render and other hosts commonly configure these as environment variables.
    url = url or os.environ.get("SUPABASE_URL", "").strip()
    key = key or os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
    return url, key


def _clear_auth_state() -> None:
    """Remove authentication/session-specific state for the current browser session."""
    for name in (
        "supabase_client",
        "supabase_user_id",
        "supabase_user_email",
        "supabase_workspace_id",
        "db_loaded_for_user",
        "conversation_id",
        "conversation_owner_id",
    ):
        st.session_state.pop(name, None)


def _activate_session(client: Any, user: Any, session: Any) -> None:
    """Store the authenticated client in the current Streamlit user's session."""
    if not user or not getattr(user, "id", None) or not session:
        raise ValueError("Supabase did not return an active user session.")
    st.session_state["supabase_client"] = client
    st.session_state["supabase_user_id"] = str(user.id)
    st.session_state["supabase_user_email"] = str(getattr(user, "email", "") or "")


def _create_client(url: str, key: str):
    from supabase import create_client
    return create_client(url, key)


def ensure_workspace(client: Any, user_id: str) -> str:
    """Get or create the signed-in user's default workspace under RLS."""
    try:
        result = (
            client.table("workspaces")
            .select("id")
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return str(result.data[0]["id"])

        client.table("workspaces").insert({
            "owner_id": user_id,
            "name": "My workspace",
        }).execute()

        result = (
            client.table("workspaces")
            .select("id")
            .eq("owner_id", user_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return str(result.data[0]["id"])
        raise RuntimeError("Workspace was not returned after creation.")
    except Exception as exc:
        raise RuntimeError(
            "Supabase login succeeded, but the workspace could not be read or created. "
            "Verify that the seven tables and their RLS policies exist. "
            f"Details: {str(exc)[:300]}"
        ) from exc


def render_auth_gate():
    """Render sign-in/sign-up and return (client, user_id, workspace_id).
Unlock more with ChatGPT Business. Upgrade for higher limits, more advanced models, and more access to tools.




