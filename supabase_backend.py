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

    If the user isn't signed in, return (None, None, None); the caller should
    then call st.stop() so protected app modules aren't shown anonymously.
    """
    url, key = _read_config()
    if not url or not key:
        st.error(
            "Supabase settings are missing. In this test app, open Settings → Secrets "
            "and define SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
        )
        st.stop()

    client = st.session_state.get("supabase_client")
    user_id = st.session_state.get("supabase_user_id")

    # Revalidate an existing per-user client session on each Streamlit rerun.
    if client is not None and user_id:
        try:
            active_session = client.auth.get_session()
            if active_session is not None:
                current_user = client.auth.get_user()
                user_obj = getattr(current_user, "user", None)
                if user_obj and str(getattr(user_obj, "id", "")) == str(user_id):
                    try:
                        workspace_id = ensure_workspace(client, str(user_id))
                    except Exception as exc:
                        st.error(str(exc))
                        return None, None, None

                    st.session_state["supabase_workspace_id"] = workspace_id
                    with st.sidebar:
                        st.caption(
                            "Signed in as "
                            + (st.session_state.get("supabase_user_email") or "user")
                        )
                        if st.button("Sign out", key="supabase_signout"):
                            try:
                                client.auth.sign_out()
                            finally:
                                _clear_auth_state()
                                st.session_state.pop("docs", None)
                                st.session_state.pop("audit", None)
                                st.rerun()
                    return client, str(user_id), workspace_id
        except Exception:
            # Expired or invalid auth session: return to the sign-in form.
            _clear_auth_state()

    st.subheader("Sign in to OpsPilot AI")
    st.caption("Use a dedicated demo account. Do not upload confidential company data yet.")

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("supabase_signin_form", clear_on_submit=False):
            email = st.text_input("Email", key="supabase_login_email")
            password = st.text_input("Password", type="password", key="supabase_login_password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

        if submitted:
            if not email.strip() or not password:
                st.error("Enter both email and password.")
            else:
                try:
                    client = _create_client(url, key)
                    result = client.auth.sign_in_with_password({
                        "email": email.strip(),
                        "password": password,
                    })
                    _activate_session(client, result.user, result.session)
                    st.rerun()
                except Exception:
                    st.error(
                        "Sign-in failed. Check your email/password and whether email verification "
                        "is complete. No password or key was logged."
                    )

    with signup_tab:
        with st.form("supabase_signup_form", clear_on_submit=True):
            new_email = st.text_input("Email address", key="supabase_signup_email")
            new_password = st.text_input("Create password (at least 8 characters)", type="password", key="supabase_signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="supabase_signup_confirm")
            signed_up = st.form_submit_button("Create account", use_container_width=True)

        if signed_up:
            if not new_email.strip():
                st.error("Enter an email address.")
            elif len(new_password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif new_password != confirm_password:
                st.error("The passwords do not match.")
            else:
                try:
                    client = _create_client(url, key)
                    result = client.auth.sign_up({
                        "email": new_email.strip(),
                        "password": new_password,
                    })
                    if getattr(result, "session", None) and getattr(result, "user", None):
                        _activate_session(client, result.user, result.session)
                        st.success("Account created. Opening your workspace…")
                        st.rerun()
                    else:
                        st.success(
                            "Account request received. If email confirmation is enabled, verify "
                            "your email, then return to the Sign in tab."
                        )
                except Exception:
                    st.error(
                        "Account creation failed. Check the email, password requirements, "
                        "and Supabase Auth settings."
                    )

    return None, None, None


def load_documents(client: Any, user_id: str, workspace_id: str) -> list[dict[str, str]]:
    """Load the user's documents and reconstruct content from ordered chunks."""
    result = (
        client.table("documents")
        .select("id,filename,created_at")
        .eq("owner_id", user_id)
        .eq("workspace_id", workspace_id)
        .order("created_at")
        .execute()
    )
    docs: list[dict[str, str]] = []
    for row in result.data or []:
        chunk_result = (
            client.table("document_chunks")
            .select("chunk_index,content")
            .eq("owner_id", user_id)
            .eq("document_id", row["id"])
            .order("chunk_index")
            .execute()
        )
        text = "".join(item.get("content", "") for item in (chunk_result.data or []))
        docs.append({"name": row["filename"], "text": text})
    return docs


def save_document(client: Any, user_id: str, workspace_id: str, filename: str, content: str) -> None:
    """Upsert document metadata and replace its searchable text chunks."""
    clean_name = str(filename).strip()[:250]
    clean_content = str(content)[:20000]
    if not clean_name or not clean_content.strip():
        raise ValueError("A document filename and readable content are required.")

    digest = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()

    client.table("documents").upsert(
        {
            "owner_id": user_id,
            "workspace_id": workspace_id,
            "filename": clean_name,
            "content_sha256": digest,
        },
        on_conflict="workspace_id,filename",
    ).execute()

    doc_result = (
        client.table("documents")
        .select("id")
        .eq("owner_id", user_id)
        .eq("workspace_id", workspace_id)
        .eq("filename", clean_name)
        .limit(1)
        .execute()
    )
    if not doc_result.data:
        raise RuntimeError("Document metadata saved, but its ID could not be retrieved.")

    document_id = str(doc_result.data[0]["id"])
    client.table("document_chunks").delete().eq("document_id", document_id).execute()

    # Small, ordered chunks are the foundation for later source-aware RAG.
    chunk_size = 3500
    chunks = [clean_content[i:i + chunk_size] for i in range(0, len(clean_content), chunk_size)]
    records = [
        {
            "owner_id": user_id,
            "workspace_id": workspace_id,
            "document_id": document_id,
            "chunk_index": index,
            "content": chunk,
        }
        for index, chunk in enumerate(chunks)
    ]
    if records:
        client.table("document_chunks").insert(records).execute()


def delete_documents(client: Any, user_id: str, workspace_id: str) -> None:
    """Delete document metadata; the database cascade removes its chunks."""
    client.table("documents").delete().eq("owner_id", user_id).eq("workspace_id", workspace_id).execute()


def load_audit_events(client: Any, user_id: str, limit: int = 200) -> list[dict[str, str]]:
    """Load recent persisted audit events in the shape used by the current UI."""
    result = (
        client.table("audit_events")
        .select("created_at,action,status,details")
        .eq("owner_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    events: list[dict[str, str]] = []
    for row in result.data or []:
        details = row.get("details") or {}
        summary = details.get("summary", "") if isinstance(details, dict) else str(details)
        events.append({
            "time": str(row.get("created_at", "")),
            "action": str(row.get("action", "")),
            "status": str(row.get("status", "")),
            "details": str(summary)[:500],
        })
    return events


def save_audit_event(client: Any, user_id: str, action: str, status: str, details: Any) -> None:
    """Persist one audit event without storing credentials."""
    summary = str(details or "")[:500]
    client.table("audit_events").insert({
        "owner_id": user_id,
        "action": str(action)[:150],
        "status": str(status)[:80],
        "details": {"summary": summary},
    }).execute()
