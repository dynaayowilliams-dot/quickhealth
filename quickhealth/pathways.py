"""Pathway selection and focused question guidance for fictional cases."""

import neatlogs

from quickhealth.intake import detect_patient_type


@neatlogs.span(kind="TOOL", name="pathway_selection", capture_input=False, capture_output=False)
def select_pathway(history):
    """Select the rules pathway from the fictional answers gathered so far."""
    return detect_patient_type(history)


@neatlogs.span(kind="TOOL", name="paediatric_history_guidance", capture_input=False, capture_output=False)
def _paediatric_guidance():
    return """Obtain the history from the caregiver, one concise question at a time. Adapt to earlier answers and cover the child's exact age (months for children under one year, and days/weeks for a young infant); birth and neonatal history, including prematurity and complications; feeding and hydration, including breastfeeding when relevant and urine/wet nappies; immunisation status; developmental milestones and any developmental regression or loss of acquired skills; growth and recent changes if known; sick contacts and relevant exposures; and age-appropriate danger signs from the safety rules: inability to drink or feed, convulsions, lethargy or being hard to wake, fast or difficult breathing, bluish lips, vomiting everything, severe dehydration signs, and fever in an infant under two months. Do not diagnose or classify urgency."""


@neatlogs.span(kind="TOOL", name="obstetric_history_guidance", capture_input=False, capture_output=False)
def _obstetric_guidance():
    return """For pregnancy, ask one concise question at a time. Ask for the first day of the LMP in YYYY-MM-DD format when known, then separately whether that date is certain. If not certain, do not imply certainty. Ask about EDD and gestational age as known to the patient. Do not calculate either: Python may show an explicitly labelled LMP-based estimate when a certain, valid date is provided. Explain that estimates can be inaccurate, especially with irregular cycles or uncertain dates. Ask gravidity (number of times pregnant, including the current pregnancy) and parity (number of pregnancies that have ended in birth; recording conventions can vary), antenatal booking and attendance, previous pregnancies, delivery modes and complications, and current danger signs: severe headache with visual changes, vaginal bleeding, convulsions, reduced fetal movement, leaking fluid, severe abdominal pain, and fever with chills. Adapt to earlier answers and do not diagnose or classify urgency."""


@neatlogs.span(kind="TOOL", name="postpartum_history_guidance", capture_input=False, capture_output=False)
def _postpartum_guidance():
    return """For a postpartum patient, obtain time since delivery and delivery details, then ask one concise question at a time about postpartum bleeding, fever, severe headache or vision changes, breathing difficulty (including fast or difficult breathing), seizures, and other danger signs listed in the safety rules. Also continue the general clerking history, adapting to earlier answers. Do not diagnose or classify urgency."""


@neatlogs.span(kind="TOOL", name="general_history_guidance", capture_input=False, capture_output=False)
def _general_guidance():
    return "Continue the general fictional clerking history, one concise adaptive question at a time. Do not diagnose or classify urgency."


def history_guidance(patient_type):
    """Return pathway-specific collection guidance inside its own trace span."""
    if patient_type in {"infant_under_2_months", "child_under_5"}:
        return _paediatric_guidance()
    if patient_type == "postpartum":
        return _postpartum_guidance()
    if patient_type.startswith("pregnancy_"):
        return _obstetric_guidance()
    return _general_guidance()


@neatlogs.span(kind="TOOL", name="paediatric_history_collection", capture_input=False, capture_output=False)
def _collect_paediatric_question(request_question):
    return request_question(_paediatric_guidance())


@neatlogs.span(kind="TOOL", name="obstetric_history_collection", capture_input=False, capture_output=False)
def _collect_obstetric_question(request_question):
    return request_question(_obstetric_guidance())


@neatlogs.span(kind="TOOL", name="postpartum_history_collection", capture_input=False, capture_output=False)
def _collect_postpartum_question(request_question):
    return request_question(_postpartum_guidance())


@neatlogs.span(kind="TOOL", name="general_history_collection", capture_input=False, capture_output=False)
def _collect_general_question(request_question):
    return request_question(_general_guidance())


def collect_pathway_question(patient_type, request_question):
    """Trace collection of the next adaptive question in the selected pathway."""
    if patient_type in {"infant_under_2_months", "child_under_5"}:
        return _collect_paediatric_question(request_question)
    if patient_type == "postpartum":
        return _collect_postpartum_question(request_question)
    if patient_type.startswith("pregnancy_"):
        return _collect_obstetric_question(request_question)
    return _collect_general_question(request_question)
