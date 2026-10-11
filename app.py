"""QuickHealth Streamlit entry point. Streamlit Cloud continues to run app.py."""

import streamlit as st

from quickhealth.runtime_config import configure_tracing


st.set_page_config(
    page_title="QuickHealth",
    page_icon=":material/health_and_safety:",
    layout="wide",
)
configure_tracing()

home_page = st.Page(
    "app_pages/home.py",
    title="Home",
    icon=":material/home:",
    default=True,
)
demo_page = st.Page(
    "app_pages/demo.py",
    title="Demo",
    icon=":material/health_and_safety:",
)

page = st.navigation([home_page, demo_page], position="top")
page.run()
