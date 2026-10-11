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
if page.title == "Home":
    st.markdown(
        '<div style="line-height:1.35">Built for neatHack 2026 with neatlogs, Entire and cfo.ai<br>'
        '<span style="font-size:.85em;color:#52635E">Code written with Codex</span></div>',
        unsafe_allow_html=True,
    )
page.run()
