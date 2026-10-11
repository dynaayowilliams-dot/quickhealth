"""QuickHealth Streamlit entry point. Streamlit Cloud continues to run app.py."""

import streamlit as st

from quickhealth.runtime_config import configure_tracing


st.set_page_config(
    page_title="QuickHealth",
    page_icon=":material/health_and_safety:",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)
configure_tracing()
st.markdown(
    """<style>
    [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {box-sizing:border-box!important; width:100%!important; max-width:960px!important; margin-inline:auto!important; padding:max(clamp(5rem, 9vh, 7rem), calc(env(safe-area-inset-top) + 2rem)) max(1.5rem, env(safe-area-inset-left)) max(3rem, env(safe-area-inset-bottom)) max(1.5rem, env(safe-area-inset-right))!important;}
    @media (max-width: 640px) {
      [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {padding:max(clamp(4.5rem, 9vh, 5.5rem), calc(env(safe-area-inset-top) + 2rem)) max(1rem, env(safe-area-inset-left)) max(2rem, env(safe-area-inset-bottom)) max(1rem, env(safe-area-inset-right))!important;}
    }
    [data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
    #MainMenu, [data-testid="stDecoration"], [data-testid="stFooter"], footer:not(.qh-footer) {display:none!important; visibility:hidden!important;}
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primary"] span, [data-testid="stBaseButton-primary"] div,
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondary"] p, [data-testid="stBaseButton-secondary"] span, [data-testid="stBaseButton-secondary"] div {color:#FFFFFF!important; background:#0F4C3A!important; border-color:#0F4C3A!important;}
    [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primary"]:focus, [data-testid="stBaseButton-primary"]:active, [data-testid="stBaseButton-primary"]:disabled,
    [data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondary"]:focus, [data-testid="stBaseButton-secondary"]:active, [data-testid="stBaseButton-secondary"]:disabled {color:#FFFFFF!important; background:#0F4C3A!important; border-color:#0F4C3A!important;}
    [data-testid="stBaseButton-primary"] *, [data-testid="stBaseButton-secondary"] * {color:#FFFFFF!important;}
    </style>""",
    unsafe_allow_html=True,
)

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
