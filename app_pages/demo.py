"""QuickHealth: fictional-case clerking assistant demo."""

import json
import secrets

import streamlit as st

from quickhealth.runtime_config import CONFIG, neatlogs

# app.py initializes neatlogs once before this page is imported.
from openai import OpenAI

from quickhealth.obstetric_dates import LMP_ESTIMATE_NOTICE, find_lmp_estimate
from quickhealth.limits import MAX_ANSWER_LENGTH
from quickhealth.pathways import select_pathway
from quickhealth.storage import (
    create_session,
    clear_fictional_sessions,
    get_session,
    get_verification_state,
    list_sessions,
)
from quickhealth.ui import apply_app_style, pending_conflict_count, render_pathway_card, render_progress, render_urgency
from quickhealth.verification import completeness_check
from quickhealth.workflow import DemoLimitReached, process_answer


def render_credit():
    st.markdown(
        '<div style="line-height:1.35">Built for neatHack 2026 with neatlogs, Entire and cfo.ai<br>'
        '<span style="font-size:.85em;color:#52635E">Code written with Codex</span></div>',
        unsafe_allow_html=True,
    )


apply_app_style(st)
with st.container(border=True):
    st.error(
        "Fictional cases only. Not medical advice. Call emergency services for danger signs. "
        "This tool does not diagnose.",
        icon=":material/emergency:",
    )
    st.info(
        "Do not enter real patient data: sessions are traced. Do not enter real names or contact details.",
        icon=":material/lock:",
    )

access_code_required = CONFIG.get("QUICKHEALTH_ACCESS_CODE")
if access_code_required and not st.session_state.get("quickhealth_access_granted", False):
    st.subheader("Access code required")
    with st.form("quickhealth_access_gate"):
        supplied_access_code = st.text_input("Access code", type="password")
        access_code_submitted = st.form_submit_button("Continue")
    if access_code_submitted:
        if secrets.compare_digest(supplied_access_code, access_code_required):
            st.session_state["quickhealth_access_granted"] = True
            st.rerun()
        else:
            st.error("That access code did not match.")
    render_credit()
    st.stop()

st.title("QuickHealth", icon=":material/health_and_safety:")
st.caption("A calm, structured clerking workspace for fictional cases")
with st.container(border=True):
    st.subheader("Before you begin", icon=":material/verified_user:")
    st.caption("Use fictional cases only. Do not enter real patient information.")
    fictional_confirmed = st.checkbox("I confirm this case is entirely fictional", key="fictional_case_confirmed")


def model_client():
    """Create the OpenAI client only when the owner has configured a key."""
    if not CONFIG.get("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing. Add it to your local .env file, then restart Streamlit.")
        render_credit()
        st.stop()
    if not CONFIG.get("OPENAI_MODEL"):
        st.error("OPENAI_MODEL is missing. Add it to your local .env file, then restart Streamlit.")
        render_credit()
        st.stop()
    return OpenAI(api_key=CONFIG["OPENAI_API_KEY"])


sessions = list_sessions()
with st.sidebar:
    st.subheader("Fictional sessions", icon=":material/folder_open:")
    with st.container(border=True):
        if st.button("Start a new fictional case", type="primary", disabled=not fictional_confirmed, icon=":material/add:"):
            st.session_state.session_id = create_session()
            st.session_state.history = []
            st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
            st.session_state.result = None
            st.session_state.verification_state = {}
            st.session_state.pop("demo_limit_reached_for", None)
    if sessions:
        with st.container(border=True):
            st.caption(f"Saved fictional cases · {len(sessions)}")
            saved_ids = [row[0] for row in sessions]
            session_labels = {row[0]: row[1] for row in sessions}
            selected_id = st.selectbox(
                "Choose a saved case",
                [""] + saved_ids,
                format_func=lambda value: session_labels.get(value, ""),
            )
            if selected_id and st.button("Open saved case", icon=":material/folder_open:"):
                row = get_session(selected_id)
                st.session_state.session_id = selected_id
                st.session_state.history = json.loads(row[1])
                st.session_state.verification_state = get_verification_state(selected_id)
                st.session_state.next_question = "Continue the fictional history with one question at a time."
                st.session_state.result = (
                    {"note": row[2], "summary": row[3], "urgency": row[4], "missing": [], "contradictions": []}
                    if row[2]
                    else None
                )
    st.divider()
    if st.button("Clear saved fictional sessions", key="clear_saved_fictional_sessions"):
        st.session_state.confirm_clear_fictional_sessions = True
    if st.session_state.get("confirm_clear_fictional_sessions"):
        st.warning("This will permanently delete all saved fictional sessions from this app database.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Confirm clear", type="primary", key="confirm_clear_sessions"):
                deleted_count = clear_fictional_sessions()
                st.session_state.session_id = None
                st.session_state.history = []
                st.session_state.result = None
                st.session_state.verification_state = {}
                st.session_state.confirm_clear_fictional_sessions = False
                st.session_state.clear_sessions_message = f"Deleted {deleted_count} saved fictional sessions."
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="cancel_clear_sessions"):
                st.session_state.confirm_clear_fictional_sessions = False
                st.rerun()
    if st.session_state.get("clear_sessions_message"):
        st.success(st.session_state.pop("clear_sessions_message"))

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if st.session_state.session_id is None:
    st.write("Start a fictional case to begin. QuickHealth asks one question at a time and adapts follow-up questions to earlier answers.")
    render_credit()
    st.stop()

session_id = st.session_state.session_id
if st.session_state.get("demo_limit_reached_for") == session_id:
    st.warning(
        "Demo limit reached. This session or today's shared demo allowance has used its model calls. "
        "If only this session reached its limit, start a new fictional session; if the daily limit was reached, try again tomorrow."
    )
    render_credit()
    st.stop()
history = st.session_state.get("history", [])
st.session_state.setdefault("verification_state", {})
patient_type = select_pathway(history) if history else "unknown"
current_completeness = completeness_check(
    patient_type,
    st.session_state.get("verification_state", {}).get("completeness", {}),
)
lmp_estimate = find_lmp_estimate(history) if patient_type.startswith("pregnancy_") else None
render_pathway_card(st, patient_type)
render_progress(st, current_completeness)
pending_conflicts = pending_conflict_count(st.session_state.get("verification_state", {}))
if pending_conflicts and not st.session_state.get("result"):
    st.warning(
        f"Possible inconsistency detected ({pending_conflicts}). Please answer the clarification question below before continuing.",
        icon=":material/warning:",
    )
if lmp_estimate and lmp_estimate["status"] == "estimated":
    st.info(
        f"LMP-based estimate only — EDD {lmp_estimate['edd']}; "
        f"gestational age {lmp_estimate['weeks']} weeks and {lmp_estimate['days']} days. "
        + LMP_ESTIMATE_NOTICE
    )
elif lmp_estimate and lmp_estimate["status"] in {"uncertain", "invalid", "future"}:
    st.warning("LMP date is uncertain, invalid, or in the future; no date estimate is shown. " + LMP_ESTIMATE_NOTICE)

if st.session_state.get("result"):
    result = st.session_state.result
    if result.get("emergency"):
        render_urgency(st, result["urgency"])
        st.error("EMERGENCY — stop the questionnaire and seek emergency care now. Call emergency services or go to the nearest hospital.")
        st.write(result["message"])
        render_credit()
        st.stop()
    if result.get("incomplete") or result.get("blocked"):
        st.warning(result.get("message", "Required details remain unresolved; the session is not complete."))
        if result.get("urgency"):
            render_urgency(st, result["urgency"])
        if result.get("missing"):
            st.subheader("Still missing or unknown")
            st.write(", ".join(result["missing"]))
        if result.get("contradictions"):
            st.subheader("Possible conflicts still needing clarification")
            for pair in result["contradictions"]:
                st.write(" • ".join(pair))
        st.write("No final note was generated because verification is unresolved.")
        render_credit()
        st.stop()
    st.subheader("Structured clerking note", icon=":material/clinical_notes:")
    with st.container(border=True):
        st.markdown(result["note"])
    st.subheader("Plain-language summary", icon=":material/subject:")
    with st.container(border=True):
        st.write(result["summary"])
    render_urgency(st, result["urgency"])
    if result["missing"]:
        st.caption("Sections that may need more information: " + ", ".join(result["missing"]))
    if result["contradictions"]:
        st.warning("Please clarify these possible inconsistencies: " + "; ".join(result["contradictions"]))
    if st.button("Start another fictional case"):
        st.session_state.session_id = create_session()
        st.session_state.history = []
        st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
        st.session_state.result = None
        st.session_state.verification_state = {}
        st.rerun()
else:
    if not history:
        st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
    for item in history:
        with st.chat_message(item["role"], avatar=":material/health_and_safety:" if item["role"] == "assistant" else None):
            st.write(item["content"])
    with st.chat_message("assistant", avatar=":material/health_and_safety:"):
        st.write(st.session_state.next_question)
    answer = st.chat_input("Answer for this fictional case", max_chars=MAX_ANSWER_LENGTH)
    if answer:
        client = model_client()
        try:
            updated_history, next_question, result, verification_state = process_answer(
                client, session_id, history, answer, st.session_state.next_question,
                st.session_state.get("verification_state", {}),
            )
            st.session_state.history = updated_history
            st.session_state.verification_state = verification_state
            if result:
                st.session_state.result = result
            else:
                st.session_state.next_question = next_question
        except DemoLimitReached:
            saved_session = get_session(session_id)
            if saved_session:
                st.session_state.history = json.loads(saved_session[1])
            st.session_state.demo_limit_reached_for = session_id
        except Exception:
            # Never display exception text because provider errors can contain request details.
            st.error("QuickHealth could not complete that step. Check your local setup and try again.")
        finally:
            neatlogs.flush()
        st.rerun()

render_credit()
