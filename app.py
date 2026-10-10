"""QuickHealth: fictional-case clerking assistant demo."""

import json
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values

# Initialize tracing before importing OpenAI so neatlogs can instrument it.
CONFIG = dotenv_values(Path(__file__).parent / ".env")
# The clerking helpers use the model name from this .env-derived value.
import os

os.environ["OPENAI_MODEL"] = CONFIG.get("OPENAI_MODEL") or ""
import neatlogs
from quickhealth.privacy import redact_trace_content


@st.cache_resource
def configure_tracing():
    neatlogs.init(
        api_key=CONFIG.get("NEATLOGS_API_KEY"),
        workflow_name="quickhealth-clerking",
        instrumentations=["openai"],
        mask=redact_trace_content,
    )
    return True


configure_tracing()

from openai import OpenAI

from quickhealth.obstetric_dates import LMP_ESTIMATE_NOTICE, find_lmp_estimate
from quickhealth.pathways import select_pathway
from quickhealth.storage import (
    create_session,
    get_session,
    get_verification_state,
    list_sessions,
)
from quickhealth.ui import apply_app_style, pending_conflict_count, render_pathway_card, render_progress
from quickhealth.verification import completeness_check
from quickhealth.workflow import process_answer


st.set_page_config(page_title="QuickHealth", page_icon=":material/health_and_safety:", layout="wide")
apply_app_style(st)
st.title("QuickHealth", icon=":material/health_and_safety:")
st.caption("A calm, structured clerking workspace for fictional cases")
with st.container(border=True):
    st.error(
        "Fictional cases only. Not medical advice. Call emergency services for danger signs. "
        "This tool does not diagnose.",
        icon=":material/emergency:",
    )
    st.info("Do not enter real patient names, contact details, or any real patient information.", icon=":material/lock:")


def model_client():
    """Create the OpenAI client only when the owner has configured a key."""
    if not CONFIG.get("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing. Add it to your local .env file, then restart Streamlit.")
        st.stop()
    if not CONFIG.get("OPENAI_MODEL"):
        st.error("OPENAI_MODEL is missing. Add it to your local .env file, then restart Streamlit.")
        st.stop()
    return OpenAI(api_key=CONFIG["OPENAI_API_KEY"])


sessions = list_sessions()
with st.sidebar:
    st.subheader("Fictional sessions", icon=":material/folder_open:")
    with st.container(border=True):
        fictional_confirmed = st.checkbox("I confirm this case is entirely fictional")
        if st.button("Start a new fictional case", type="primary", disabled=not fictional_confirmed, icon=":material/add:"):
            st.session_state.session_id = create_session()
            st.session_state.history = []
            st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
            st.session_state.result = None
            st.session_state.verification_state = {}
    if sessions:
        with st.container(border=True):
            st.caption(f"Saved fictional cases · {len(sessions)}")
            saved_ids = [row[0] for row in sessions]
            selected_id = st.selectbox("Choose a saved case", [""] + saved_ids)
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

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if st.session_state.session_id is None:
    st.write("Start a fictional case to begin. QuickHealth asks one question at a time and adapts follow-up questions to earlier answers.")
    st.stop()

session_id = st.session_state.session_id
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
        st.error("EMERGENCY — stop the questionnaire and seek emergency care now. Call emergency services or go to the nearest hospital.")
        st.write(result["message"])
        st.subheader("Urgency from safety rules")
        st.write(result["urgency"])
        st.stop()
    if result.get("incomplete") or result.get("blocked"):
        st.warning(result.get("message", "Required details remain unresolved; the session is not complete."))
        st.subheader("Urgency from safety rules")
        if result.get("urgency"):
            st.write(result["urgency"])
        if result.get("missing"):
            st.subheader("Still missing or unknown")
            st.write(", ".join(result["missing"]))
        if result.get("contradictions"):
            st.subheader("Possible conflicts still needing clarification")
            for pair in result["contradictions"]:
                st.write(" • ".join(pair))
        st.write("No final note was generated because verification is unresolved.")
        st.stop()
    st.subheader("Structured clerking note", icon=":material/clinical_notes:")
    with st.container(border=True):
        st.markdown(result["note"])
    st.subheader("Plain-language summary", icon=":material/subject:")
    with st.container(border=True):
        st.write(result["summary"])
    st.subheader("Urgency from safety rules")
    st.write(result["urgency"])
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
    answer = st.chat_input("Answer for this fictional case", max_chars=4000)
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
        except Exception:
            # Never display exception text because provider errors can contain request details.
            st.error("QuickHealth could not complete that step. Check your local setup and try again.")
        finally:
            neatlogs.flush()
        st.rerun()
