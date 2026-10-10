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


@st.cache_resource
def configure_tracing():
    neatlogs.init(
        api_key=CONFIG.get("NEATLOGS_API_KEY"),
        workflow_name="quickhealth-clerking",
        instrumentations=["openai"],
    )
    return True


configure_tracing()

from openai import OpenAI

from quickhealth.clerking import (
    ask_next_question,
    build_clerking_note,
    detect_patient_type,
    find_contradictions,
    get_missing_sections,
)
from quickhealth.safety_rules import assess_urgency
from quickhealth.storage import (
    create_session,
    get_session,
    list_sessions,
    save_answer,
    save_result,
)


st.set_page_config(page_title="QuickHealth", page_icon="🩺", layout="centered")
st.title("QuickHealth")
st.caption("AI-assisted history taking for nurses and health workers")
st.error(
    "Fictional cases only. Not medical advice. Call emergency services for danger signs. "
    "This tool does not diagnose."
)
st.info("Do not enter real patient names, contact details, or any real patient information.")


def model_client():
    """Create the OpenAI client only when the owner has configured a key."""
    if not CONFIG.get("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY is missing. Add it to your local .env file, then restart Streamlit.")
        st.stop()
    if not CONFIG.get("OPENAI_MODEL"):
        st.error("OPENAI_MODEL is missing. Add it to your local .env file, then restart Streamlit.")
        st.stop()
    return OpenAI(api_key=CONFIG["OPENAI_API_KEY"])


@neatlogs.span(kind="WORKFLOW", name="quickhealth_clerking_session")
def process_answer(client, session_id, history, answer):
    """Record one turn in a clerking session and select its next question."""
    question = st.session_state.next_question
    save_answer(session_id, question, answer)
    updated_history = history + [
        {"role": "assistant", "content": question},
        {"role": "user", "content": answer},
    ]
    next_question = ask_next_question(client, updated_history)
    result = None
    if next_question.strip().upper() == "COMPLETE":
        patient_type = detect_patient_type(updated_history)
        note, summary = build_clerking_note(client, updated_history, patient_type)
        urgency = assess_urgency(updated_history, patient_type)
        missing = get_missing_sections(updated_history)
        contradictions = find_contradictions(client, updated_history)
        save_result(session_id, note, summary, urgency, patient_type)
        result = {
            "note": note,
            "summary": summary,
            "urgency": urgency,
            "missing": missing,
            "contradictions": contradictions,
        }
    return updated_history, next_question, result


sessions = list_sessions()
with st.sidebar:
    st.subheader("Fictional sessions")
    fictional_confirmed = st.checkbox("I confirm this case is entirely fictional")
    if st.button("Start a new fictional case", type="primary", disabled=not fictional_confirmed):
        st.session_state.session_id = create_session()
        st.session_state.history = []
        st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
        st.session_state.result = None
    if sessions:
        st.caption(f"Saved fictional sessions: {len(sessions)}")
        saved_ids = [row[0] for row in sessions]
        selected_id = st.selectbox("Choose a saved case", [""] + saved_ids)
        if selected_id and st.button("Open saved case"):
            row = get_session(selected_id)
            st.session_state.session_id = selected_id
            st.session_state.history = json.loads(row[1])
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
st.caption(f"Fictional case ID: {session_id}")

if st.session_state.get("result"):
    result = st.session_state.result
    st.subheader("Structured clerking note")
    st.markdown(result["note"])
    st.subheader("Plain-language summary")
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
        st.rerun()
else:
    history = st.session_state.get("history", [])
    if not history:
        st.session_state.next_question = "Describe a fictional patient using a made-up age and no identifying details. What is the main concern today?"
    for item in history:
        with st.chat_message(item["role"]):
            st.write(item["content"])
    st.chat_message("assistant").write(st.session_state.next_question)
    answer = st.chat_input("Type an answer for this fictional case")
    if answer:
        client = model_client()
        try:
            updated_history, next_question, result = process_answer(
                client, session_id, history, answer
            )
            st.session_state.history = updated_history
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
