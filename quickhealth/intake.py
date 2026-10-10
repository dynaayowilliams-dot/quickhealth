"""Rule-based patient pathway detection from fictional case answers."""

import re

import neatlogs


AGE_UNIT = r"(?:days?|weeks?|months?|years?|d|wks?|mos?|yrs?)"


def _age_mentions(text):
    """Return explicit patient ages without treating symptom durations as ages."""
    patterns = (
        rf"\b(\d{{1,3}})\s*[- ]?({AGE_UNIT})\s*[- ]old\b",
        rf"\b(?:age(?:d)?(?:\s+(?:is|of))?\s*|(?:child|baby|infant|newborn)\s+(?:is\s+)?)"
        rf"(\d{{1,3}})\s*({AGE_UNIT})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)), match.group(2).lower()
    return None


@neatlogs.span(kind="TOOL", name="intake_and_patient_type_detection", capture_input=False, capture_output=False)
def detect_patient_type(history):
    text = " ".join(item["content"] for item in history if item.get("role") == "user").lower()

    if re.search(r"\b(postpartum|after (?:giving birth|delivery)|since (?:giving birth|delivery)|gave birth)\b", text):
        return "postpartum"

    pregnant = re.search(r"\b(pregnant|pregnancy|gestation|weeks pregnant)\b", text)
    if pregnant:
        if re.search(r"\b(first|1st) trimester\b", text):
            return "pregnancy_trimester_1"
        if re.search(r"\b(second|2nd) trimester\b", text):
            return "pregnancy_trimester_2"
        if re.search(r"\b(third|3rd) trimester\b", text):
            return "pregnancy_trimester_3"
        weeks = re.search(r"\b(\d{1,2})\s*(?:weeks?|wks?)\s*(?:pregnant|gestation)?\b", text)
        if weeks:
            gestational_weeks = int(weeks.group(1))
            if gestational_weeks < 14:
                return "pregnancy_trimester_1"
            if gestational_weeks < 28:
                return "pregnancy_trimester_2"
            return "pregnancy_trimester_3"
        return "pregnancy_trimester_unknown"

    age = _age_mentions(text)
    if age:
        value, unit = age
        if unit in {"day", "days", "d"} and value < 60:
            return "infant_under_2_months"
        if unit in {"week", "weeks", "wk", "wks"} and value < 9:
            return "infant_under_2_months"
        if unit in {"month", "months", "mo", "mos"}:
            if value < 2:
                return "infant_under_2_months"
            if value < 60:
                return "child_under_5"
        if unit in {"year", "years", "yr", "yrs"}:
            if value < 5:
                return "child_under_5"
            if value < 18:
                # The rules file only defines a paediatric pathway under five;
                # unknown keeps the conservative, broader danger-rule coverage.
                return "unknown"
            return "other_adult"

    if re.search(r"\b(infant|newborn|baby)\b", text):
        return "infant_under_2_months"
    if re.search(r"\b(child|toddler)\b", text):
        return "child_under_5"
    if re.search(r"\b(adult|man|woman|male|female)\b", text):
        return "other_adult"
    return "unknown"
