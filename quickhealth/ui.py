"""Small shared visual helpers for the Streamlit interface."""

import html

PATHWAY_CARDS = {
    "unknown": (
        "Pathway selection", "General, maternal, postpartum, or child pathway follows the fictional intake details.",
        "medical_information", "gray",
    ),
    "other_adult": (
        "General clerking", "A structured adult history, one question at a time.",
        "clinical_notes", "blue",
    ),
    "general": (
        "General clerking", "A structured history, one question at a time.",
        "clinical_notes", "blue",
    ),
    "child_under_5": (
        "Child and caregiver pathway", "Age-aware history for children under five, guided by the caregiver.",
        "child_care", "green",
    ),
    "infant_under_2_months": (
        "Young infant pathway", "Infant-focused history. Record age in days or weeks when known.",
        "child_care", "green",
    ),
    "pregnancy_trimester_1": (
        "Pregnancy care · first trimester", "Antenatal history with dates clearly labelled as estimates when applicable.",
        "pregnant_woman", "violet",
    ),
    "pregnancy_trimester_2": (
        "Pregnancy care · second trimester", "Antenatal history with dates clearly labelled as estimates when applicable.",
        "pregnant_woman", "violet",
    ),
    "pregnancy_trimester_3": (
        "Pregnancy care · third trimester", "Antenatal history with dates clearly labelled as estimates when applicable.",
        "pregnant_woman", "violet",
    ),
    "pregnancy_trimester_unknown": (
        "Pregnancy care", "Antenatal history. Trimester has not been identified yet.",
        "pregnant_woman", "violet",
    ),
    "postpartum": (
        "Postpartum care", "A distinct history focused on time since delivery and postpartum wellbeing.",
        "woman", "orange",
    ),
}


def pathway_card_details(patient_type):
    """Return safe display-only pathway text and supported badge styling."""
    if isinstance(patient_type, str) and patient_type.startswith("pregnancy_"):
        trimester = patient_type.rsplit("_", 1)[-1]
        if trimester in {"1", "2", "3"}:
            key = f"pregnancy_trimester_{trimester}"
            return PATHWAY_CARDS[key]
        return PATHWAY_CARDS["pregnancy_trimester_unknown"]
    return PATHWAY_CARDS.get(patient_type, PATHWAY_CARDS["general"])


def pending_conflict_count(verification_state):
    """Count pending conflicts without exposing recorded answers in status UI."""
    contradiction_state = verification_state.get("contradictions", {}) if isinstance(verification_state, dict) else {}
    records = contradiction_state.get("contradictions", []) if isinstance(contradiction_state, dict) else []
    if not isinstance(records, list):
        return 0
    return sum(1 for record in records if isinstance(record, dict) and record.get("status") == "pending")


def render_urgency(st, urgency):
    """Show rule-produced urgency with a text label, icon, and distinct colour."""
    urgency_styles = {
        "EMERGENCY_NOW": ("qh-urgency--emergency", "⚠", "EMERGENCY"),
        "SEE_CLINICIAN_TODAY": ("qh-urgency--today", "●", "SEE A CLINICIAN TODAY"),
        "ROUTINE": ("qh-urgency--routine", "✓", "ROUTINE"),
    }
    css_class, icon, label = urgency_styles.get(
        urgency, ("qh-urgency--unknown", "ℹ", "URGENCY STATUS")
    )
    safe_urgency = html.escape(str(urgency or "Not available"))
    st.markdown(
        f'<div class="qh-urgency {css_class}" role="status">'
        f'<span class="qh-urgency-icon" aria-hidden="true">{icon}</span>'
        f'<strong>{label}</strong><span>{safe_urgency}</span></div>',
        unsafe_allow_html=True,
    )


def apply_app_style(st):
    """Apply the QuickHealth light theme and shared component styling."""
    st.markdown("""<style>
        :root {color-scheme: light; --qh-bg:#FFFBF7; --qh-surface:#E4EDE2; --qh-green:#0F4C3A; --qh-text:#1F2D2A; --qh-border:#87958D;}
        html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {color:var(--qh-text)!important; background:var(--qh-bg)!important;}
        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {background:var(--qh-bg)!important; color:var(--qh-text)!important;}
        [data-testid="stSidebar"], [data-testid="stSidebar"]>div {background:var(--qh-surface)!important; color:var(--qh-text)!important;}
        [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], [data-testid="stWidgetLabel"], label, small {color:var(--qh-text)!important;}
        [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {box-sizing:border-box!important; width:100%!important; max-width:960px!important; margin-inline:auto!important; padding:max(clamp(5rem, 9vh, 7rem), calc(env(safe-area-inset-top) + 2rem)) max(1.5rem, env(safe-area-inset-left)) max(3rem, env(safe-area-inset-bottom)) max(1.5rem, env(safe-area-inset-right))!important;}
        [data-testid="stCheckbox"] label {min-height:48px; display:flex; align-items:center; gap:.65rem; padding:.4rem .25rem; cursor:pointer;}
        [data-testid="stCheckbox"] input {width:22px; height:22px;}
        [data-testid="stVerticalBlockBorderWrapper"] {border:1px solid #CFD9D0; border-radius:22px; background:var(--qh-bg);}
        [data-testid="stChatMessage"] {color:var(--qh-text)!important; border:1px solid #CFD9D0; border-radius:22px; padding:1rem 1.15rem; background:var(--qh-surface)!important;}
        [data-testid="stChatInput"], [data-testid="stChatInput"]>div, [data-testid="stChatInput"] textarea, [data-testid="stTextInput"] input, [data-testid="stSelectbox"] [role="combobox"] {color:var(--qh-text)!important; background:var(--qh-bg)!important; border-color:var(--qh-border)!important; border-radius:14px;}
        input::placeholder, textarea::placeholder {color:#485852!important; opacity:1;}
        [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {min-height:48px;}
        [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primary"] span, [data-testid="stBaseButton-primary"] div,
        [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondary"] p, [data-testid="stBaseButton-secondary"] span, [data-testid="stBaseButton-secondary"] div {color:#FFFFFF!important; background:#0F4C3A!important; border-color:#0F4C3A!important; border-radius:999px; font-weight:700;}
        [data-testid="stBaseButton-primary"] *, [data-testid="stBaseButton-secondary"] * {color:#FFFFFF!important;}
        [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primary"]:focus,
        [data-testid="stBaseButton-primary"]:active, [data-testid="stBaseButton-primary"]:disabled,
        [data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondary"]:focus,
        [data-testid="stBaseButton-secondary"]:active, [data-testid="stBaseButton-secondary"]:disabled {color:#FFFFFF!important; background:#0F4C3A!important; border-color:#0F4C3A!important; opacity:1;}
        [data-testid="stBaseButton-primary"] button *, [data-testid="stBaseButton-secondary"] button * {color:#FFFFFF!important;}
        [data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu,
        [data-testid="stDecoration"], [data-testid="stFooter"], footer:not(.qh-footer) {display:none!important; visibility:hidden!important;}
        [data-testid="stAlert"] {color:var(--qh-text)!important; background:var(--qh-surface)!important; border:1px solid var(--qh-border)!important; border-radius:16px;}
        [data-testid="stAlert"] * {color:var(--qh-text)!important;}
        [data-testid="stProgress"] [role="progressbar"] {background:#87958D!important;}
        [data-testid="stProgress"] [role="progressbar"]>div {background:var(--qh-green)!important;}
        .qh-pathway-card {border:1px solid #87958D; border-left:5px solid var(--qh-green); border-radius:22px; padding:1.2rem 1.4rem; margin:.4rem 0 1rem; color:var(--qh-text); background:var(--qh-surface);}
        .qh-pathway-card p {margin:0; line-height:1.6; color:var(--qh-text);}
        .qh-urgency {display:flex; flex-wrap:wrap; align-items:center; gap:.55rem; margin:.5rem 0 1rem; padding:1rem 1.15rem; border:2px solid; border-radius:18px; font-size:1rem;}
        .qh-urgency-icon {font-size:1.25rem; line-height:1;}
        .qh-urgency--emergency {color:#7F1D1D; background:#FDE8E7; border-color:#A83232;}
        .qh-urgency--today {color:#704000; background:#FFF1D1; border-color:#9A5B00;}
        .qh-urgency--routine {color:#124E48; background:#E2F2F0; border-color:#24756C;}
        .qh-urgency--unknown {color:var(--qh-text); background:var(--qh-surface); border-color:var(--qh-border);}
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"], .stMainBlockContainer, .block-container {padding:max(clamp(4.5rem, 9vh, 5.5rem), calc(env(safe-area-inset-top) + 2rem)) max(1rem, env(safe-area-inset-left)) max(2rem, env(safe-area-inset-bottom)) max(1rem, env(safe-area-inset-right))!important;}
            [data-testid="stChatMessage"] {padding:.8rem .9rem;}
            .qh-pathway-card {padding:1rem;}
        }
    </style>""", unsafe_allow_html=True)


def render_pathway_card(st, patient_type):
    title, description, icon, color = pathway_card_details(patient_type)
    if patient_type in {"child_under_5", "infant_under_2_months"}:
        accent = "child"
    elif patient_type == "postpartum":
        accent = "postpartum"
    elif isinstance(patient_type, str) and patient_type.startswith("pregnancy_"):
        accent = "pregnancy"
    elif patient_type == "unknown":
        accent = "unknown"
    else:
        accent = "general"
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    st.badge(title, icon=f":material/{icon}:", color=color)
    st.markdown(
        f'<section class="qh-pathway-card qh-pathway-card--{accent}" aria-label="{safe_title}">'
        f"<p>{safe_description}</p></section>",
        unsafe_allow_html=True,
    )


def render_progress(st, check):
    """Show answer progress and unresolved sections without hiding warnings."""
    statuses = check.get("statuses", {})
    total = len(check.get("required", []))
    answered = len(statuses.get("answered", []))
    ratio = answered / total if total else 0.0
    with st.container(border=True):
        st.markdown("**History coverage**")
        st.progress(ratio, text=f"{answered} of {total} required sections answered")
        missing = check.get("missing", [])
        if missing:
            from quickhealth.verification import SECTION_LABELS

            labels = [SECTION_LABELS.get(section, section.replace("_", " ")) for section in missing]
            st.caption("Still to cover: " + " · ".join(labels))
        else:
            st.caption("All required sections have an answer.")
