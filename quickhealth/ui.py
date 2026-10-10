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
        .block-container {max-width: 1120px; padding-top: 1.6rem; padding-bottom: 3rem;}
        [data-testid="stAppViewContainer"] {background: #F7F6F2;}
        [data-testid="stSidebar"] {border-right: 1px solid #D9E3DE;}
        [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px;}
        [data-testid="stChatMessage"] {
            border: 1px solid #D9E3DE; border-radius: 18px;
            padding: 0.85rem 1rem; background: rgba(255,255,255,0.72);
        }
        [data-testid="stChatInput"] {border-radius: 16px;}
        [data-testid="stChatInput"] textarea {line-height: 1.55;}
        button[kind="primary"] {border-radius: 12px; font-weight: 650;}
        .qh-pathway-card {
            border: 1px solid #D9E3DE; border-left: 5px solid #6C9690;
            border-radius: 18px; padding: 1rem 1.2rem; margin: 0.35rem 0 1rem;
            color: #153B3A; background: #FFFFFF;
        }
        .qh-pathway-card p {margin: 0; line-height: 1.55; color: #315654;}
        .qh-pathway-card--pregnancy {background: #FBF1F3; border-color: #E5CBD2; border-left-color: #A76F82;}
        .qh-pathway-card--postpartum {background: #FBF2E9; border-color: #E8D6C2; border-left-color: #A56C48;}
        .qh-pathway-card--child {background: linear-gradient(110deg, #EFF7F0, #EFF7F0 72%, #EEF5FA); border-color: #D2E3D8; border-left-color: #56836A;}
        .qh-pathway-card--general {background: #F0F5F7; border-color: #D4E1E5; border-left-color: #477A88;}
        .qh-pathway-card--unknown {background: #FBF8EF; border-color: #E9E1C8; border-left-color: #9A8751;}
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
