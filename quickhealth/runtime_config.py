"""Runtime settings and one-time tracing setup for the Streamlit app."""

import os
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values


DOTENV_CONFIG = dotenv_values(Path(__file__).resolve().parent.parent / ".env")


def configured_value(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    if value:
        return str(value)
    return DOTENV_CONFIG.get(name)


CONFIG = {
    name: configured_value(name)
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "NEATLOGS_API_KEY", "QUICKHEALTH_ACCESS_CODE")
}
os.environ["OPENAI_MODEL"] = CONFIG.get("OPENAI_MODEL") or ""

# Import and initialize tracing before any page imports OpenAI.
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

