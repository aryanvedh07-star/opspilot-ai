import streamlit as st
import pandas as pd
import json, re, io, os
from datetime import datetime, timezone
from difflib import SequenceMatcher

st.set_page_config(page_title="OpsPilot AI", page_icon="🧭", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; max-width: 1250px;}
.hero {padding: 1.3rem 1.5rem; border: 1px solid #303744; border-radius: 16px; background: linear-gradient(120deg,#111827,#172554);}
.hero h1 {margin:0; font-size:2.1rem;}
.hero p {margin:.4rem 0 0; color:#cbd5e1;}
.small-muted {color:#94a3b8; font-size:.9rem;}
div[data-testid="stMetric"] {border:1px solid #303744; padding:12px; border-radius:12px;}
</style>
<div class="hero">
<h1>🧭 OpsPilot AI</h1>
<p>Your business operations copilot — research, company knowledge, financial checks, communication drafts, and controlled actions.</p>
</div>
""", unsafe_allow_html=True)

if "audit" not in st.session_state:
    st.session_state.audit = []
if "pending" not in st.session_state:
    st.session_state.pending = []
if "approved" not in st.session_state:
    st.session_state.approved = []
if "chat" not in st.session_state:
    st.session_state.chat = []
if "docs" not in st.session_state:
    st.session_state.docs = []
if "drafts" not in st.session_state:
    st.session_state.drafts = []

def log_event(action, status, details):
    st.session_state.audit.insert(0, {
        "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "action": action, "status": status, "details": str(details)[:500]
    })

def get_api_key():
    key = st.session_state.get("gemini_key", "").strip()
    return key

def ask_model(prompt, context=""):
    key = get_api_key()
    if not key:
        return None, "Add a Gemini API key in the sidebar to enable AI-generated answers. The non-AI CSV checks and approval demo work without it."
    try:
        from google import genai
        client = genai.Client(api_key=key)
        full_prompt = (
            "You are OpsPilot AI, a careful business operations assistant. "
            "Use only supplied context for claims about the user's company. "
            "Separate verified facts from assumptions. Never claim an action was completed unless a tool confirms it. "
            "For risky actions, recommend human approval. Do not expose secrets.\n\n"
            f"CONTEXT:\n{context[:18000]}\n\nTASK:\n{prompt}"
        )
        response = client.models.generate_content(model="gemini-3.8-flash", contents=full_prompt)
        text = getattr(response, "text", None)
        if not text:
            return None, "The model returned an empty response. Try a shorter request."
        return text, None
    except Exception as e:
        return None, f"AI request failed: {e}"

def read_uploaded_text(uploaded):
    name = uploaded.name.lower()
    try:
        if name.endswith(".txt") or name.endswith(".md"):
            return uploaded.getvalue().decode("utf-8", errors="ignore")
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded)
            return "CSV file: " + uploaded.name + "\n" + df.head(80).to_string(index=False)
        if name.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(uploaded)
                return "\n".join(page.extract_text() or "" for page in reader.pages)[:20000]
            except Exception:
                return ""
        if name.endswith(".docx"):
            try:
                from docx import Document
                doc = Document(uploaded)
                return "\n".join(p.text for p in doc.paragraphs)[:20000]
            except Exception:
                return ""
    except Exception:
        return ""
    return ""

with st.sidebar:
    st.header("⚙️ Setup")
    st.caption("Prototype mode: use sample or non-sensitive data.")
    st.text_input("Gemini API key (optional)", type="password", key="gemini_key",
                  help="Used only for this running session. For a deployed public app, configure a server-side secret instead of sharing your key.")
    st.markdown("Get a key: [Google AI Studio](https://aistudio.google.com/apikey)")
    st.divider()
    st.subheader("Demo safety rules")
    st.write("✅ Read-only analysis is allowed")
    st.write("🟡 Sending messages / external changes need approval")
    st.write("⛔ Unauthorized destructive actions are blocked")
    st.caption("This is a portfolio prototype, not a production security boundary. Do not connect real company accounts yet.")

tabs = st.tabs([
    "🏠 Overview", "🧠 Company Brain", "🔎 Research & Chat",
    "💸 Financial Checks", "✉️ Email Drafts", "🛡️ AgentGate", "📜 Audit Log"
])

with tabs[0]:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Documents loaded", len(st.session_state.docs))
    c2.metric("Pending approvals", len(st.session_state.pending))
    c3.metric("Drafts created", len(st.session_state.drafts))
    c4.metric("Audit events", len(st.session_state.audit))
    st.subheader("What this prototype can do today")
    st.markdown("""
    - **Company Brain:** upload TXT, MD, CSV, PDF or DOCX files and ask questions about their content.
    - **Research & Chat:** ask the AI to analyze supplied notes, competitor facts or company context.
    - **Financial Checks:** upload invoice/payment CSVs and flag exact or likely duplicate payments for human review.
    - **Email Drafts:** generate draft replies; nothing is sent automatically.
    - **AgentGate:** demonstrate allow / approval required / blocked decisions and keep an audit trail.
    """)
    st.warning("AI research is not automatically live web research in this version. Provide source URLs or copied public facts and verify important claims. Real browsing integrations can be added later.")
    st.info("Start with synthetic/sample data. This demo does not connect to Gmail, a bank, a CRM or a phone provider.")

with tabs[1]:
    st.subheader("Company Brain — upload your knowledge")
    uploads = st.file_uploader("Upload files", type=["txt","md","csv","pdf","docx"], accept_multiple_files=True, key="docs_uploader")
    if st.button("Process uploaded files", type="primary"):
        count = 0
        for f in uploads or []:
            content = read_uploaded_text(f)
            if content.strip():
                existing = [d["name"] for d in st.session_state.docs]
                if f.name not in existing:
                    st.session_state.docs.append({"name":f.name, "text":content})
                else:
                    for d in st.session_state.docs:
                        if d["name"] == f.name:
                            d["text"] = content
                count += 1
            else:
                st.warning(f"Could not extract text from {f.name}. Try TXT/CSV or check PDF/DOCX support.")
        log_event("Process documents", "completed", f"Processed {count} file(s)")
        st.success(f"Processed {count} file(s).")
    if st.session_state.docs:
        st.write("Loaded files:")
        for d in st.session_state.docs:
            st.write(f"📄 **{d['name']}** — {len(d['text'])} characters")
        question = st.text_area("Ask a question about these files", placeholder="What are our refund rules? Summarize the risks in these records.")
        if st.button("Ask Company Brain"):
            context = "\n\n".join(f"FILE: {d['name']}\n{d['text'][:6000]}" for d in st.session_state.docs)
            answer, err = ask_model(question, context)
            if err:
                st.error(err)
            else:
                st.markdown(answer)
                log_event("Company Brain question", "completed", question)
    else:
        st.info("No files loaded yet. Upload a sample policy or a CSV to try this module.")
    if st.button("Clear uploaded document memory"):
        st.session_state.docs = []
        log_event("Clear documents", "completed", "User cleared session documents")
        st.rerun()

with tabs[2]:
    st.subheader("Research & general operations chat")
    st.caption("Use public facts, source URLs, or uploaded company documents. This version does not crawl the web automatically.")
    prompt = st.text_area("What should OpsPilot investigate?", height=110,
        placeholder="Compare these competitors using the notes below. Cite which claims came from the supplied notes and list unknowns.")
    research_context = st.text_area("Evidence / public notes / source URLs (optional)", height=130,
        placeholder="Paste public facts or notes and include source URLs. Do not paste confidential data.")
    doc_context = "\n\n".join(f"FILE: {d['name']}\n{d['text'][:4000]}" for d in st.session_state.docs)
    if st.button("Run analysis", type="primary"):
        context = (research_context + "\n\n" + doc_context)[:18000]
        answer, err = ask_model(prompt, context)
        if err:
            st.error(err)
        else:
            st.markdown(answer)
            log_event("Research/chat", "completed", prompt)
    st.divider()
    st.subheader("Example tasks")
    st.code("Compare competitor A and B based only on the supplied facts. Return a table, sources, unknowns, and three testable opportunities.")
    st.code("Review these support notes. Group complaints by theme and recommend which issue to investigate first.")

with tabs[3]:
    st.subheader("Financial checks — potential duplicate payments")
    st.write("Upload a CSV with columns such as supplier, invoice_number, amount, payment_date. You can also try sample data.")
    sample = pd.DataFrame([
        {"supplier":"ABC Supplies","invoice_number":"INV-1042","amount":25000,"payment_date":"2026-10-02"},
        {"supplier":"ABC Supplies","invoice_number":"INV-1042","amount":25000,"payment_date":"2026-10-08"},
        {"supplier":"Northstar Office","invoice_number":"NS-220","amount":4600,"payment_date":"2026-10-09"},
        {"supplier":"Delta Parts","invoice_number":"DP-51","amount":12500,"payment_date":"2026-10-10"},
    ])
    if st.button("Load sample financial data"):
        st.session_state.fin_df = sample
    fin_file = st.file_uploader("Upload payment CSV", type=["csv"], key="fin_uploader")
    if fin_file is not None:
        try:
            st.session_state.fin_df = pd.read_csv(fin_file)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
    if "fin_df" in st.session_state:
        df = st.session_state.fin_df.copy()
        st.dataframe(df, use_container_width=True)
        cols = list(df.columns)
        lower_map = {str(c).lower().strip():c for c in cols}
        def pick(candidates):
            for k,v in lower_map.items():
                if any(x in k for x in candidates):
                    return v
            return None
        supplier_col = pick(["supplier","vendor","payee","merchant"])
        invoice_col = pick(["invoice","bill","reference","ref_no"])
        amount_col = pick(["amount","total","paid","value"])
        if not supplier_col or not amount_col:
            st.warning("Could not automatically identify supplier and amount columns. Rename them to supplier and amount, then upload again.")
        else:
            df["_supplier_norm"] = df[supplier_col].astype(str).str.lower().str.strip()
            df["_amount_num"] = pd.to_numeric(df[amount_col].astype(str).str.replace(",",""), errors="coerce")
            if invoice_col:
                df["_invoice_norm"] = df[invoice_col].astype(str).str.lower().str.strip()
                dup_mask = df.duplicated(subset=["_supplier_norm","_invoice_norm","_amount_num"], keep=False)
                matches = df[dup_mask].copy()
            else:
                dup_mask = df.duplicated(subset=["_supplier_norm","_amount_num"], keep=False)
                matches = df[dup_mask].copy()
            potential = float(matches["_amount_num"].sum()) if not matches.empty else 0.0
            st.metric("Rows flagged for review", len(matches))
            st.metric("Sum of flagged row amounts (not confirmed loss)", f"{potential:,.2f}")
            if not matches.empty:
                st.warning("These are potential matches, not confirmed duplicate payments. Verify invoice IDs, credit notes, reversals and payment status.")
                st.dataframe(matches.drop(columns=[c for c in ["_supplier_norm","_invoice_norm","_amount_num"] if c in matches.columns]), use_container_width=True)
                csv = matches.drop(columns=[c for c in ["_supplier_norm","_invoice_norm","_amount_num"] if c in matches.columns]).to_csv(index=False).encode()
                st.download_button("Download flagged rows CSV", csv, "opspilot_flagged_rows.csv", "text/csv")
                log_event("Financial duplicate check", "review required", f"{len(matches)} rows flagged")
            else:
                st.success("No exact duplicates found by this basic rule. This does not prove the file is error-free.")
    else:
        st.info("Load the sample data or upload a CSV to run the checks.")

with tabs[4]:
    st.subheader("Email draft assistant")
    email_type = st.selectbox("Draft type", ["Customer support reply","Follow-up email","Meeting follow-up","Internal escalation"])
    incoming = st.text_area("Original message / situation", height=140, placeholder="Paste a message without confidential information.")
    extra = st.text_area("Approved facts the reply may use", height=100, placeholder="Order status, company policy, dates, next steps...")
    tone = st.selectbox("Tone", ["Professional and clear","Friendly","Concise","Empathetic"])
    if st.button("Generate draft"):
        task = f"Write a {email_type}. Tone: {tone}. Do not invent facts, promises, dates, refunds, or actions. If key facts are missing, use placeholders or state what needs confirmation.\n\nOriginal message:\n{incoming}"
        answer, err = ask_model(task, extra)
        if err:
            st.error(err)
        else:
            st.session_state.drafts.insert(0, {"time":datetime.now().astimezone().isoformat(timespec="seconds"),"type":email_type,"draft":answer})
            log_event("Email draft created", "draft only", email_type)
            st.markdown(answer)
            st.caption("Nothing was sent. Copy the draft only after reviewing it.")
    if st.session_state.drafts:
        st.divider()
        st.write("Recent drafts")
        for i,d in enumerate(st.session_state.drafts[:5],1):
            with st.expander(f"{i}. {d['type']} — {d['time']}"):
                st.write(d["draft"])

with tabs[5]:
    st.subheader("AgentGate — action policy demonstration")
    st.write("Select an action. This prototype demonstrates policy decisions; it does not execute external actions.")
    action = st.selectbox("Proposed agent action", [
        "Read an authorized company document",
        "Draft a customer email",
        "Send an email to a customer",
        "Issue a refund above the configured limit",
        "Delete customer records",
        "Export confidential customer data to an unknown destination"
    ])
    rationale = st.text_input("Why is the agent proposing this action?", "Requested during a workflow")
    if st.button("Evaluate action", type="primary"):
        if action == "Read an authorized company document":
            decision = "ALLOW"
            explanation = "Read-only action, assuming the current user has document access."
        elif action == "Delete customer records" or action == "Export confidential customer data to an unknown destination":
            decision = "BLOCK"
            explanation = "Destructive or unauthorized data-transfer action is blocked by this demo policy."
        else:
            decision = "REQUIRES HUMAN APPROVAL"
            explanation = "External communication or financial action needs explicit review before execution."
        event = {"id":len(st.session_state.audit)+len(st.session_state.pending)+1,"action":action,"decision":decision,"reason":explanation,"rationale":rationale}
        if decision == "REQUIRES HUMAN APPROVAL":
            st.session_state.pending.append(event)
        log_event(action, decision, explanation)
        st.session_state.last_policy = event
    if "last_policy" in st.session_state:
        e=st.session_state.last_policy
        st.markdown(f"### Decision: **{e['decision']}**")
        st.write(e["reason"])
    st.divider()
    st.subheader("Pending approval queue")
    if not st.session_state.pending:
        st.info("No actions are waiting for approval.")
    for e in st.session_state.pending[:]:
        with st.container(border=True):
            st.write(f"**{e['action']}**")
            st.write(e["reason"])
            col1,col2=st.columns(2)
            if col1.button("Approve demo action", key=f"approve_{e['id']}"):
                st.session_state.approved.append(e)
                st.session_state.pending.remove(e)
                log_event(e["action"], "approved in demo", "Approval recorded; no external action executed")
                st.rerun()
            if col2.button("Reject", key=f"reject_{e['id']}"):
                st.session_state.pending.remove(e)
                log_event(e["action"], "rejected", "Rejected by reviewer; no external action executed")
                st.rerun()
    if st.session_state.approved:
        st.caption(f"{len(st.session_state.approved)} demo action(s) approved. Approval is recorded only; no external action is executed.")

with tabs[6]:
    st.subheader("Audit log")
    st.caption("Events are stored in the current Streamlit session only. They reset when the session restarts.")
    if st.session_state.audit:
        log_df = pd.DataFrame(st.session_state.audit)
        st.dataframe(log_df, use_container_width=True)
        st.download_button("Download audit log CSV", log_df.to_csv(index=False).encode(), "opspilot_audit_log.csv", "text/csv")
    else:
        st.info("No events recorded yet.")
    if st.button("Clear session audit log"):
        st.session_state.audit = []
        st.rerun()

st.divider()
st.markdown('<p class="small-muted">OpsPilot AI prototype • Use synthetic data first • AI output may be wrong • No external actions are executed by this demo.</p>', unsafe_allow_html=True)
