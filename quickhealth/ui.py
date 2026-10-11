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


def apply_app_style(st):
    """Add restrained responsive polish on top of Streamlit's theme tokens."""
    st.html("""<style>
        :root {
            color-scheme: light;
            --qh-bg: #FFFBF7;
            --qh-surface: #E4EDE2;
            --qh-primary: #0F4C3A;
            --qh-text: #1F2D2A;
            --qh-border: #71827B;
        }
        html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
            color: var(--qh-text) !important;
            background: var(--qh-bg) !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
            color: var(--qh-text) !important;
            background: var(--qh-bg) !important;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
            color: var(--qh-text) !important;
            background: var(--qh-surface) !important;
            border-right: 1px solid var(--qh-border);
        }
        [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li, label, small {
            color: var(--qh-text) !important;
        }
        .block-container {max-width: 1120px; padding-top: 1.6rem; padding-bottom: 3rem;}
        [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px;}
        [data-testid="stChatMessage"] {
            color: var(--qh-text) !important;
            border: 1px solid var(--qh-border); border-radius: 18px;
            padding: 0.85rem 1rem; background: var(--qh-surface) !important;
        }
        [data-testid="stChatInput"], [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] textarea,
        [data-testid="stTextInput"] input, [data-testid="stSelectbox"] [role="combobox"] {
            color: var(--qh-text) !important;
            background: var(--qh-bg) !important;
            border-color: var(--qh-border) !important;
        }
        [data-testid="stChatInput"] {border-radius: 16px;}
        [data-testid="stChatInput"] textarea {line-height: 1.55;}
        [data-testid="stChatInput"] textarea::placeholder,
        input::placeholder, textarea::placeholder {color: #485852 !important; opacity: 1;}
        button[kind="primary"] {
            color: #FFFFFF !important; background: var(--qh-primary) !important;
            border-color: var(--qh-primary) !important; border-radius: 12px; font-weight: 650;
        }
        [data-testid="stAlert"] {
            color: var(--qh-text) !important;
            background: var(--qh-surface) !important;
            border: 1px solid var(--qh-border) !important;
        }
        [data-testid="stAlert"] * {color: var(--qh-text) !important;}
        [data-testid="stProgress"] [role="progressbar"] {background: #71827B !important;}
        [data-testid="stProgress"] [role="progressbar"] > div {
            background: var(--qh-primary) !important;
        }
        [data-testid="stProgress"] p {color: var(--qh-text) !important;}
        .qh-pathway-card {
            border: 1px solid var(--qh-border); border-left: 5px solid var(--qh-primary);
            border-radius: 18px; padding: 1rem 1.2rem; margin: 0.35rem 0 1rem;
            color: var(--qh-text); background: var(--qh-surface);
        }
        .qh-pathway-card p {margin: 0; line-height: 1.55; color: var(--qh-text);}
        .qh-pathway-card--pregnancy, .qh-pathway-card--postpartum,
        .qh-pathway-card--child, .qh-pathway-card--general,
        .qh-pathway-card--unknown {background: var(--qh-surface); border-color: var(--qh-border);}
        @media (max-width: 640px) {
            .block-container {padding: 1rem 0.85rem 2rem;}
            [data-testid="stChatMessage"] {padding: 0.7rem 0.8rem;}
            .qh-pathway-card {padding: 0.9rem 1rem;}
        }
    </style>""")


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
