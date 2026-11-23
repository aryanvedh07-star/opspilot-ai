








import os
import streamlit as st
import pandas as pd
from datetime import datetime

from supabase_backend import (
    render_auth_gate,
    load_documents,
    save_document,
    delete_documents,
    load_audit_events,
    save_audit_event,
)


# ============================================================
# 1. APP CONFIGURATION AND DESIGN
# ============================================================

st.set_page_config(
    page_title="OpsPilot AI",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        max-width: 1250px;
    }
    .hero {
        padding: 1.3rem 1.5rem;
        border: 1px solid #303744;
        border-radius: 16px;
        background: linear-gradient(120deg, #111827, #172554);
    }
    .hero h1 {
        margin: 0;
        font-size: 2.1rem;
    }
    .hero p {
        margin: .4rem 0 0;
        color: #cbd5e1;
    }
    .small-muted {
        color: #94a3b8;
        font-size: .9rem;
    }
    div[data-testid="stMetric"] {
        border: 1px solid #303744;
        padding: 12px;
        border-radius: 12px;
    }
    </style>
    <div class="hero">
        <h1>🧭 OpsPilot AI</h1>
        <p>Your business operations copilot — company knowledge,
        research, financial checks, communication drafts, and controlled actions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. SESSION DATA
# ============================================================

DEFAULTS = {
    "audit": [],
    "pending": [],
    "approved": [],
    "chat": [],
    "docs": [],
    "drafts": [],
}

for name, default_value in DEFAULTS.items():
    if name not in st.session_state:
        st.session_state[name] = default_value


def log_event(action, status, details):
    """Add an audit event locally and persist it to Supabase."""
    event = {
        "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "action": str(action)[:150],
        "status": str(status)[:80],
        "details": str(details)[:500],
    }
    st.session_state.audit.insert(0, event)

    client = st.session_state.get("db_client")
    user_id = st.session_state.get("db_user_id")
Unlock more with ChatGPT Business. Upgrade for higher limits, more advanced models, and more access to tools.




