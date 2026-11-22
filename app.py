            "Export confidential customer data to an unknown destination",
        ):
            decision = "BLOCK"
            explanation = "Destructive or unauthorized data-transfer action is blocked by this demo policy."
        else:
            decision = "REQUIRES HUMAN APPROVAL"
            explanation = "External communication or financial action needs explicit review before execution."

        if decision == "REQUIRES HUMAN APPROVAL":
            try:
                create_approval_request(action, explanation, rationale)
                st.success("Approval request saved to Supabase.")
            except Exception as exc:
                st.error("Could not save approval request: " + str(exc)[:300])
        else:
            st.info(f"Decision: {decision}")
            log_event(action, decision, explanation)

        st.session_state.last_policy = {
            "action": action,
            "decision": decision,
            "reason": explanation,
            "rationale": rationale,
        }
        try:
            st.session_state.pending = load_pending_approvals()
        except Exception:
            pass

    if "last_policy" in st.session_state:
        event = st.session_state.last_policy
        st.markdown(f"### Decision: **{event['decision']}**")
        st.write(event["reason"])

    st.divider()
    st.subheader("Pending approval queue")
    if not st.session_state.pending:
        st.info("No actions are waiting for approval.")

    for event in st.session_state.pending[:]:
        with st.container(border=True):
            st.write(f"**{event['action']}**")
            st.write(event["reason"])
            if event.get("rationale"):
                st.caption("Reason proposed: " + event["rationale"])
            st.caption("Created: " + event.get("created_at", ""))
            approve_col, reject_col = st.columns(2)
            if approve_col.button("Approve request", key=f"approve_{event['id']}"):
                try:
                    resolve_approval_request(
                        event["id"],
                        "approved",
                        "Approved by the signed-in reviewer. No external action executed.",
                    )
                    log_event(event["action"], "approved in review", "Approval recorded; no external action executed")
                    st.success("Approval decision saved. No external action was executed.")
                    st.session_state.pending = load_pending_approvals()
                    st.rerun()
                except Exception as exc:
                    st.error("Could not save approval decision: " + str(exc)[:300])
            if reject_col.button("Reject request", key=f"reject_{event['id']}"):
                try:
                    resolve_approval_request(
                        event["id"],
                        "rejected",
                        "Rejected by the signed-in reviewer.",
                    )
                    log_event(event["action"], "rejected", "Approval request rejected")
                    st.session_state.pending = load_pending_approvals()
                    st.rerun()
                except Exception as exc:
                    st.error("Could not save rejection: " + str(exc)[:300])


# ============================================================
# TAB 7 — AUDIT LOG
# ============================================================

with tabs[6]:
    st.subheader("Persistent audit log")
    st.caption("Audit events are saved to Supabase for the signed-in user.")

    if st.session_state.audit:
        log_df = pd.DataFrame(st.session_state.audit)
        st.dataframe(log_df, use_container_width=True)
        st.download_button(
            "Download audit log CSV",
            log_df.to_csv(index=False).encode("utf-8"),
            "opspilot_audit_log.csv",
            "text/csv",
        )
    else:
        st.info("No audit events recorded yet.")

    confirm_clear = st.checkbox("I understand this permanently deletes my saved audit events.")
    if st.button("Clear saved audit log", key="clear_audit", disabled=not confirm_clear):
        try:
            client.table("audit_events").delete().eq("owner_id", user_id).execute()
            st.session_state.audit = []
            st.session_state.pop("db_audit_warning", None)
            st.success("Saved audit events deleted.")
            st.rerun()
        except Exception as exc:
            st.error("Could not clear the audit log: " + str(exc)[:300])


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.markdown(
    '<p class="small-muted">OpsPilot AI • Supabase-backed demo workspace • '
    'AI output may be wrong • Approvals are recorded but do not execute external actions.</p>',
    unsafe_allow_html=True,
)


  
