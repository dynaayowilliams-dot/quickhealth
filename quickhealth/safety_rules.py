"""Simple safety rule checks; the language model never determines urgency."""

import re

import neatlogs

EMERGENCY_PATTERNS = (
    r"cannot breathe|not breathing|severe difficulty breathing|blue lips|unconscious|not waking|seizure|fits|heavy bleeding|bleeding heavily|severe chest pain|suicid(al|e) intent|danger to self",
    r"pregnan\w*.{0,40}(heavy bleeding|severe headache|blurred vision|convulsion|seizure)|postpartum.{0,40}(heavy bleeding|seizure|convulsion)",
    r"baby.{0,40}(not breathing|blue lips|unconscious|not waking|unable to feed)",
)
TODAY_PATTERNS = (
    r"high fever|persistent vomiting|worsening pain|reduced fetal movement|baby.{0,30}(not feeding|very sleepy)|dehydration|blood in stool",
)
ROUTINE_PATTERNS = (
    r"\bno current symptoms\b|\bsymptoms? (?:have )?(?:resolved|settled)\b|\bwell and feeding normally\b",
)


@neatlogs.span(kind="GUARDRAIL", name="rules_based_red_flag_checker")
def assess_urgency(history, patient_type):
    """Return a cautious category based only on explicit rule matches."""
    text = " ".join(item["content"] for item in history if item["role"] == "user").lower()
    if any(_has_unnegated_match(pattern, text) for pattern in EMERGENCY_PATTERNS):
        return "EMERGENCY_NOW"
    if any(_has_unnegated_match(pattern, text) for pattern in TODAY_PATTERNS):
        return "SEE_CLINICIAN_TODAY"
    if any(_has_unnegated_match(pattern, text) for pattern in ROUTINE_PATTERNS):
        return "ROUTINE"
    # The limited prototype rules cannot rule out danger; direct review when uncertain.
    return "SEE_CLINICIAN_TODAY"


def _has_unnegated_match(pattern, text):
    for match in re.finditer(pattern, text):
        preceding_words = text[max(0, match.start() - 35):match.start()]
        if not re.search(r"\b(?:no|not|never|denies|without)\s+(?:\w+\s+){0,3}$", preceding_words):
            return True
    return False
