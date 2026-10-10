"""Completeness and contradiction checks for fictional clerking sessions."""

from datetime import date
import hashlib
import json
import re

import neatlogs
from opentelemetry import trace as otel_trace

from quickhealth.obstetric_dates import calculate_obstetric_dates

CHECKER_VERSION = "1"
GA_TOLERANCE_DAYS = 7
UNKNOWN_RE = re.compile(
    r"\b(?:unknown|unsure|uncertain|not sure|don't know|do not know|cannot remember|can't remember|not available)\b",
    re.IGNORECASE,
)

GENERAL_SECTIONS = (
    "biodata", "presenting_complaint", "presenting_complaint_details",
    "past_medical_history", "past_surgical_history", "prescribed_medicines",
    "herbal_traditional_medicines", "otc_medicines", "allergies",
    "family_history", "social_history", "systems_review",
)
PATHWAY_SECTIONS = {
    "paediatric": GENERAL_SECTIONS + (
        "caregiver_history", "child_age", "birth_neonatal_history",
        "feeding_hydration", "immunisation_status", "development_milestones",
        "growth_history", "sick_contacts_exposures", "paediatric_danger_signs",
    ),
    "antenatal": GENERAL_SECTIONS + (
        "pregnancy_status", "lmp_and_certainty", "edd_and_gestational_age",
        "gravidity_parity", "antenatal_care", "previous_pregnancies_deliveries",
        "pregnancy_danger_signs",
    ),
    "postpartum": GENERAL_SECTIONS + (
        "postpartum_status", "time_since_delivery", "delivery_details",
        "postpartum_bleeding", "postpartum_fever", "postpartum_headache_vision",
        "postpartum_breathing", "postpartum_seizures", "postpartum_danger_signs",
    ),
    "general": GENERAL_SECTIONS,
}
SECTION_LABELS = {
    "biodata": "Biodata",
    "presenting_complaint": "Presenting complaint",
    "presenting_complaint_details": "Presenting complaint details",
    "past_medical_history": "Past medical history",
    "past_surgical_history": "Past surgical history",
    "prescribed_medicines": "Prescribed medicines",
    "herbal_traditional_medicines": "Herbal and traditional medicines",
    "otc_medicines": "Over-the-counter medicines",
    "allergies": "Allergies",
    "family_history": "Family history",
    "social_history": "Social history",
    "systems_review": "Systems review",
    "caregiver_history": "Caregiver history",
    "child_age": "Child's age",
    "birth_neonatal_history": "Birth and neonatal history",
    "feeding_hydration": "Feeding and hydration",
    "immunisation_status": "Immunisation status",
    "development_milestones": "Development and milestones",
    "growth_history": "Growth and recent changes",
    "sick_contacts_exposures": "Sick contacts and exposures",
    "paediatric_danger_signs": "Paediatric danger signs",
    "pregnancy_status": "Pregnancy status",
    "lmp_and_certainty": "Last menstrual period and date certainty",
    "edd_and_gestational_age": "EDD and gestational age",
    "gravidity_parity": "Gravidity and parity",
    "antenatal_care": "Antenatal care and booking",
    "previous_pregnancies_deliveries": "Previous pregnancies, deliveries, and complications",
    "pregnancy_danger_signs": "Current pregnancy danger signs",
    "postpartum_status": "Postpartum status",
    "time_since_delivery": "Time since delivery",
    "delivery_details": "Delivery details",
    "postpartum_bleeding": "Postpartum bleeding",
    "postpartum_fever": "Postpartum fever",
    "postpartum_headache_vision": "Postpartum headache and vision changes",
    "postpartum_breathing": "Postpartum breathing difficulty",
    "postpartum_seizures": "Postpartum seizures",
    "postpartum_danger_signs": "Other postpartum danger signs",
}
FOLLOW_UP_QUESTIONS = {
    "biodata": "What made-up age and basic, non-identifying biodata should be recorded?",
    "presenting_complaint": "What is the main concern for this fictional case?",
    "presenting_complaint_details": "When did the concern start, and how has it changed?",
    "past_medical_history": "What past medical conditions or illnesses should be recorded? If not known, say so.",
    "past_surgical_history": "What past surgeries or procedures should be recorded? If none or unknown, say so.",
    "prescribed_medicines": "What prescribed medicines are currently used, if any? Include the name as known, or say unknown.",
    "herbal_traditional_medicines": "Are any herbal or traditional remedies used? If none or unknown, say so.",
    "otc_medicines": "What over-the-counter medicines are used, if any? If none or unknown, say so.",
    "allergies": "What allergies are known, or is this information unknown?",
    "family_history": "What relevant family history should be recorded, or is it unknown?",
    "social_history": "What relevant social history should be recorded without identifying details?",
    "systems_review": "Are there other symptoms in the systems review, or is this information unknown?",
    "caregiver_history": "Who is providing this fictional child's history (for example, parent or caregiver)?",
    "child_age": "What is the child's age? For an infant, give age in days, weeks, or months if known.",
    "birth_neonatal_history": "Was the child born prematurely, or were there birth or neonatal complications? If unknown, say so.",
    "feeding_hydration": "How is the child feeding and staying hydrated, including breastfeeding if relevant?",
    "immunisation_status": "What is known about the child's immunisation status?",
    "development_milestones": "What developmental milestones has the child reached, and has any acquired skill been lost?",
    "growth_history": "Are there known growth measurements or recent growth changes? If unknown, say so.",
    "sick_contacts_exposures": "Have there been sick contacts or relevant exposures? If unknown, say so.",
    "paediatric_danger_signs": "Have any age-appropriate danger signs from the on-screen safety rules been reported?",
    "pregnancy_status": "Is this a current pregnancy, or is the pregnancy status unknown?",
    "lmp_and_certainty": "What was the first day of the last menstrual period (YYYY-MM-DD), and is that date certain?",
    "edd_and_gestational_age": "What EDD or gestational age has a clinician or the patient previously recorded, if known? Do not calculate it here.",
    "gravidity_parity": "How many times has the patient been pregnant including now (gravidity), and how many pregnancies have ended in birth (parity)?",
    "antenatal_care": "Has antenatal care been booked and attended? If unknown, say so.",
    "previous_pregnancies_deliveries": "What previous pregnancies, delivery modes, and complications should be recorded?",
    "pregnancy_danger_signs": "Have any current pregnancy danger signs from the on-screen safety rules been reported?",
    "postpartum_status": "When did delivery occur, and is the time since delivery known?",
    "time_since_delivery": "How long has it been since delivery?",
    "delivery_details": "What are the known details of the delivery, including delivery mode and any complications?",
    "postpartum_bleeding": "Has there been increased or heavy bleeding after delivery?",
    "postpartum_fever": "Has there been a fever after delivery?",
    "postpartum_headache_vision": "Has there been a severe headache or a change in vision after delivery?",
    "postpartum_breathing": "Has there been fast or difficult breathing after delivery?",
    "postpartum_seizures": "Have there been convulsions or seizures after delivery?",
    "postpartum_danger_signs": "Have any other postpartum danger signs from the on-screen safety rules been reported?",
}


def pathway_group(pathway_type):
    if pathway_type in {"child_under_5", "infant_under_2_months", "paediatric"}:
        return "paediatric"
    if pathway_type == "postpartum":
        return "postpartum"
    if isinstance(pathway_type, str) and pathway_type.startswith("pregnancy_"):
        return "antenatal"
    return "general"


def _span_attributes(name, pathway, fired, missing_count=0, suspected_count=0, resolution="none"):
    span = otel_trace.get_current_span()
    if not span or not span.is_recording():
        return
    span.set_attribute("quickhealth.checker.name", name)
    span.set_attribute("quickhealth.checker.version", CHECKER_VERSION)
    span.set_attribute("quickhealth.pathway", pathway_group(pathway))
    span.set_attribute("quickhealth.check.fired", bool(fired))
    span.set_attribute("quickhealth.missing_section_count", int(missing_count))
    span.set_attribute("quickhealth.suspected_contradiction_count", int(suspected_count))
    span.set_attribute("quickhealth.resolution_status", resolution)


@neatlogs.span(
    kind="TOOL", name="completeness_check", version=CHECKER_VERSION,
    capture_input=False, capture_output=False,
)
def completeness_check(pathway_type, state, question=None, answer=None):
    """Update section status without treating unknown information as complete."""
    group = pathway_group(pathway_type)
    required = PATHWAY_SECTIONS[group]
    incoming = state if isinstance(state, dict) else {}
    sections = incoming.get("sections", {}) if isinstance(incoming.get("sections"), dict) else {}
    clean_sections = {}
    for section in required:
        previous = sections.get(section, {})
        if not isinstance(previous, dict):
            previous = {}
        clean_sections[section] = {
            "status": previous.get("status") if previous.get("status") in {"answered", "unknown"} else "unanswered",
            "followups": int(previous.get("followups", 0)) if str(previous.get("followups", 0)).isdigit() else 0,
        }

    active_section = incoming.get("active_section")
    targets = [active_section] if active_section in clean_sections else _sections_for_question(question or "", required)
    if answer is not None:
        for section in targets:
            clean_sections[section]["status"] = "unknown" if UNKNOWN_RE.search(answer) else "answered"

    updated = {
        "version": 1,
        "pathway": group,
        "sections": clean_sections,
        "active_section": None,
    }
    missing = [section for section in required if clean_sections[section]["status"] != "answered"]
    statuses = {
        "answered": [section for section in required if clean_sections[section]["status"] == "answered"],
        "unanswered": [section for section in required if clean_sections[section]["status"] == "unanswered"],
        "unknown": [section for section in required if clean_sections[section]["status"] == "unknown"],
    }
    _span_attributes("completeness_check", group, bool(missing), len(missing))
    return {"state": updated, "required": list(required), "missing": missing, "statuses": statuses}


def _sections_for_question(question, required):
    text = (question or "").lower()
    cues = {
        "biodata": ("biodata", "age and sex", "age, sex", "basic details"),
        "presenting_complaint": ("main concern", "presenting complaint", "chief complaint"),
        "presenting_complaint_details": ("when did", "how long", "onset", "severity", "aggravating", "relieving", "associated symptom", "character"),
        "past_medical_history": ("medical history", "past illness", "past condition"),
        "past_surgical_history": ("surgical history", "surgery", "operation"),
        "prescribed_medicines": ("prescribed medicine", "prescription", "prescribed medication"),
        "herbal_traditional_medicines": ("herbal", "traditional medicine", "traditional remedy"),
        "otc_medicines": ("over-the-counter", "over the counter", "otc medicine"),
        "allergies": ("allerg",), "family_history": ("family history", "family medical"),
        "social_history": ("social history", "smoking", "alcohol", "living situation"),
        "systems_review": ("systems review", "review of systems", "other symptoms"),
        "caregiver_history": ("caregiver", "who is providing the history"),
        "child_age": ("child's age", "child age", "how old", "months old", "weeks old"),
        "birth_neonatal_history": ("birth history", "born prematurely", "neonatal", "prematurity"),
        "feeding_hydration": ("feeding", "breastfeeding", "hydration", "wet nappies", "wet diapers"),
        "immunisation_status": ("immunisation", "immunization", "vaccination"),
        "development_milestones": ("development", "milestone", "lost any skill", "regression"),
        "growth_history": ("growth", "weight change", "growth measurement"),
        "sick_contacts_exposures": ("sick contact", "exposure"),
        "paediatric_danger_signs": ("danger sign", "red flag"),
        "pregnancy_status": ("pregnancy status", "are you pregnant", "currently pregnant"),
        "lmp_and_certainty": ("last menstrual period", "\blmp\b"),
        "edd_and_gestational_age": ("edd", "gestational age", "how many weeks pregnant"),
        "gravidity_parity": ("gravidity", "parity", "times pregnant"),
        "antenatal_care": ("antenatal", "anc booking", "prenatal care"),
        "previous_pregnancies_deliveries": ("previous pregnanc", "previous deliver", "delivery mode", "mode of delivery"),
        "pregnancy_danger_signs": ("pregnancy danger sign", "fetal movement", "vaginal bleeding"),
        "postpartum_status": ("postpartum status", "after delivery", "since delivery"),
        "time_since_delivery": ("time since delivery", "how long since delivery", "days after delivery"),
        "delivery_details": ("delivery detail", "delivery mode", "mode of delivery", "how was the delivery"),
        "postpartum_bleeding": ("postpartum bleeding", "bleeding after delivery", "bleeding after birth"),
        "postpartum_fever": ("fever after delivery", "postpartum fever"),
        "postpartum_headache_vision": ("headache", "vision change", "blurred vision"),
        "postpartum_breathing": ("breathing difficulty", "difficulty breathing", "shortness of breath"),
        "postpartum_seizures": ("seizure", "convulsion", "fits"),
        "postpartum_danger_signs": ("postpartum danger sign", "other danger sign"),
    }
    return [section for section in required if any(cue in text for cue in cues.get(section, ()))]


def completeness_follow_up(check):
    """Return one focused follow-up, or mark all unresolved sections exhausted."""
    state = check["state"]
    for section in check["missing"]:
        state["sections"].setdefault(section, {"status": "unanswered", "followups": 0})
        section_state = state["sections"][section]
        if section_state["followups"] < 1:
            section_state["followups"] += 1
            state["active_section"] = section
            return FOLLOW_UP_QUESTIONS[section]
    return None


def completeness_display(check):
    return [SECTION_LABELS[section] for section in check["missing"]]


class CandidateDetectionError(RuntimeError):
    """Free-text contradiction candidate detection could not be trusted."""


@neatlogs.span(
    kind="TOOL", name="contradiction_candidate_detection", version=CHECKER_VERSION,
    capture_input=False, capture_output=False,
)
def detect_free_text_candidates(client, history):
    """Ask for possible free-text conflicts only; results remain unconfirmed."""
    user_items = [(index, item.get("content", "")) for index, item in enumerate(history) if item.get("role") == "user"]
    if len(user_items) < 2:
        return []
    numbered = "\n".join(f"{position + 1}. {text}" for position, (_, text) in enumerate(user_items))
    prompt = (
        "Review this fictional history ONLY for statements that may contradict one another. "
        "Do not diagnose, infer urgency, or decide which statement is correct. Return JSON only as an object: "
        '{"candidates":[{"first_answer_number":1,"second_answer_number":2,"reason_code":"date_conflict",'
        '"clarification_question":"..."}]}. Return {"candidates":[]} if none. Use a short safe reason_code from '
        "date_conflict, medicine_conflict, pregnancy_status_conflict, delivery_history_conflict, other_conflict. "
        "Each answer number refers to the numbered user answer below. Treat every result as an unconfirmed candidate.\n"
        + numbered
    )
    try:
        import os
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", ""),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        value = json.loads(raw)
        if isinstance(value, dict):
            value = value.get("candidates")
        if not isinstance(value, list):
            raise ValueError("Expected a candidate list")
        result = []
        allowed = {"date_conflict", "medicine_conflict", "pregnancy_status_conflict", "delivery_history_conflict", "other_conflict"}
        for entry in value:
            if not isinstance(entry, dict):
                raise ValueError("Candidate must be an object")
            first = entry.get("first_answer_number")
            second = entry.get("second_answer_number")
            if not isinstance(first, int) or not isinstance(second, int) or first == second or not (1 <= first <= len(user_items) and 1 <= second <= len(user_items)):
                raise ValueError("Invalid answer references")
            kind = entry.get("reason_code")
            question = entry.get("clarification_question")
            if kind not in allowed or not isinstance(question, str) or not question.strip():
                raise ValueError("Invalid candidate description")
            result.append({
                "kind": "model_" + kind,
                "source_indices": [user_items[first - 1][0], user_items[second - 1][0]],
                # Never display model-generated clarification text as it could contain unsafe claims.
                "question": "Please clarify whether these two statements refer to the same time or event, and what each one means. Both original answers will be kept.",
            })
        return result
    except Exception as exc:
        _span_attributes("contradiction_check", "general", True, suspected_count=1, resolution="error")
        raise CandidateDetectionError("Free-text candidate detection failed") from exc


@neatlogs.span(
    kind="TOOL", name="contradiction_check", version=CHECKER_VERSION,
    capture_input=False, capture_output=False,
)
def contradiction_check(history, state, model_candidates=None):
    """Detect deterministic conflicts and accept free-text findings as candidates."""
    incoming = state if isinstance(state, dict) else {}
    records = incoming.get("contradictions", [])
    if not isinstance(records, list):
        records = []
    records = [record for record in records if isinstance(record, dict) and isinstance(record.get("id"), str)]
    active_id = incoming.get("active_contradiction_id")
    resolution_status = "pending" if active_id else "none"

    user_items = [(index, item) for index, item in enumerate(history) if item.get("role") == "user"]
    if active_id:
        active = next((record for record in records if record["id"] == active_id), None)
        if active and active.get("status") == "pending":
            if user_items:
                answer_index = user_items[-1][0]
                answer = user_items[-1][1].get("content", "")
                active["clarification_index"] = answer_index
                active["status"] = "unresolved" if UNKNOWN_RE.search(answer) else "clarified"
                active_id = None
                resolution_status = active["status"]

    new_candidates = list(_deterministic_candidates(history))
    if model_candidates:
        if not isinstance(model_candidates, list):
            _span_attributes("contradiction_check", incoming.get("pathway", "general"), True, suspected_count=1, resolution="error")
            raise CandidateDetectionError("Candidate detection returned an invalid format")
        new_candidates.extend(model_candidates)

    for candidate in new_candidates:
        candidate_id = _candidate_id(candidate)
        existing = next((record for record in records if record["id"] == candidate_id), None)
        if existing:
            if existing.get("status") == "pending":
                active_id = candidate_id
            continue
        record = {
            "id": candidate_id,
            "kind": candidate["kind"],
            "source_indices": candidate["source_indices"],
            "status": "pending",
            "clarification_index": None,
            "question": candidate["question"],
        }
        records.append(record)
        active_id = candidate_id
        resolution_status = "pending"

    updated = {
        "version": 1,
        "pathway": incoming.get("pathway", "general"),
        "contradictions": records,
        "active_contradiction_id": active_id,
    }
    pending = [record for record in records if record.get("status") == "pending"]
    unresolved = [record for record in records if record.get("status") == "unresolved"]
    if pending and active_id is None:
        active_id = pending[0]["id"]
        updated["active_contradiction_id"] = active_id
    candidates = [_candidate_for_display(record, history) for record in pending + unresolved]
    if pending:
        resolution_status = "pending"
    _span_attributes(
        "contradiction_check", updated["pathway"], bool(candidates),
        suspected_count=len(candidates), resolution=resolution_status,
    )
    return {"state": updated, "candidates": candidates, "pending": bool(pending), "unresolved": bool(unresolved)}


def contradiction_clarification_question(candidate):
    left, right = candidate["facts"]
    return (
        f"Please clarify these two recorded statements: '{left}' and '{right}'. "
        f"{candidate['question']} The earlier answers will both be kept."
    )


def _candidate_id(candidate):
    signature = json.dumps(
        [candidate["kind"], sorted(candidate["source_indices"])],
        ensure_ascii=True, separators=(",", ":"),
    )
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def _candidate_for_display(record, history):
    facts = []
    for source_index in record.get("source_indices", []):
        if isinstance(source_index, int) and 0 <= source_index < len(history):
            item = history[source_index]
            content = item.get("content", "") if isinstance(item, dict) else ""
            facts.append(content if isinstance(content, str) else "Recorded statement")
    question = record.get("question") or "Can you clarify which information is correct, or explain how both statements fit together?"
    return {
        "id": record["id"], "kind": record.get("kind", "possible_inconsistency"),
        "status": record.get("status", "pending"), "facts": facts,
        "question": question,
    }


def _deterministic_candidates(history):
    yield from _lmp_gestational_age_candidate(history)
    yield from _child_age_stage_candidates(history)
    yield from _simple_status_conflicts(history)


def _lmp_gestational_age_candidate(history):
    lmp_entries = []
    stated_ga = []
    for index, item in enumerate(history):
        if item.get("role") != "user":
            continue
        answer = item.get("content", "")
        previous_question = history[index - 1].get("content", "") if index else ""
        if re.search(r"\b(?:LMP|last menstrual period)\b", previous_question, re.IGNORECASE):
            date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", answer)
            certain = re.search(r"\b(certain|sure|yes)\b", answer, re.IGNORECASE)
            uncertain = re.search(r"\b(?:uncertain|unsure|unknown|not sure|not certain|don't know)\b", answer, re.IGNORECASE)
            if date_match and certain and not uncertain:
                estimate = calculate_obstetric_dates(date_match.group(1), today=date.today())
                if estimate["status"] == "estimated":
                    lmp_entries.append((index, estimate))
        if re.search(r"\b(?:gestational age|weeks pregnant|pregnancy is|currently .* weeks)\b", previous_question, re.IGNORECASE):
            ga_match = re.search(r"\b(\d{1,2})\s*(?:weeks?|wks?)(?:\s*(\d)\s*days?)?\b", answer, re.IGNORECASE)
            if ga_match:
                stated_ga.append((index, int(ga_match.group(1)) * 7 + int(ga_match.group(2) or 0)))
    for lmp_index, estimate in lmp_entries:
        expected_days = estimate["weeks"] * 7 + estimate["days"]
        for ga_index, stated_days in stated_ga:
            if abs(expected_days - stated_days) > GA_TOLERANCE_DAYS:
                yield {
                    "kind": "lmp_gestational_age_difference_over_7_days",
                    "source_indices": [lmp_index, ga_index],
                    "question": f"The LMP-based estimate and the stated gestational age differ by more than the {GA_TOLERANCE_DAYS}-day clarification threshold. Which dates or recorded estimate should be checked?",
                }


def _child_age_stage_candidates(history):
    answer_items = [(index, item.get("content", "")) for index, item in enumerate(history) if item.get("role") == "user"]
    age_patterns = (
        r"\b(\d{1,2})[- ]?months?[- ]old\b",
        r"\b(three)\s*months?\s*old\b",
    )
    age_location = None
    for answer_index, text in answer_items:
        for pattern in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                months = 3 if match.group(1).lower() == "three" else int(match.group(1))
                if months == 3:
                    age_location = answer_index
                    break
        if age_location is not None:
            break
    if age_location is None:
        return
    checks = (
        ("family_food_at_three_months", r"\b(?:eating|eats|given)\b.{0,40}\bfamily food\b"),
        ("independent_walking_at_three_months", r"\b(?:starting\s+to\s+walk|walking|walks)\b"),
    )
    for kind, pattern in checks:
        for milestone_index, text in answer_items:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match or milestone_index == age_location:
                continue
            prefix = text[max(0, match.start() - 30):match.start()]
            if re.search(r"\b(?:no|not|never|denies|without|cannot|can't|hasn't|doesn't)\s+(?:\w+\s+){0,3}$", prefix, re.IGNORECASE):
                continue
            yield {
                "kind": kind,
                "source_indices": sorted({age_location, milestone_index}),
                "question": "Please confirm the child's age and what was meant by the developmental or feeding description. This is only a request to clarify the recorded history, not a conclusion about development.",
            }


def _simple_status_conflicts(history):
    user_items = [(index, item.get("content", "")) for index, item in enumerate(history) if item.get("role") == "user"]
    for first_pos, (first_index, first_text) in enumerate(user_items):
        for second_index, second_text in user_items[first_pos + 1:]:
            if _explicit_pregnancy_status(first_text) and _explicit_pregnancy_status(second_text):
                if _explicit_pregnancy_status(first_text) != _explicit_pregnancy_status(second_text):
                    yield _candidate("pregnancy_status_conflict", first_index, second_index,
                                     "Please confirm whether this fictional history describes a current pregnancy or not.")
            first_delivery = _delivery_mode(first_text)
            second_delivery = _delivery_mode(second_text)
            if first_delivery and second_delivery and first_delivery != second_delivery:
                yield _candidate("delivery_mode_conflict", first_index, second_index,
                                 "Please clarify whether the delivery mode statements refer to different deliveries or correct one of the details.")
            if _medication_conflict(first_text, second_text):
                yield _candidate("medication_status_conflict", first_index, second_index,
                                 "Please clarify the medicine history and whether the two statements refer to different times.")


def _candidate(kind, first_index, second_index, question):
    return {"kind": kind, "source_indices": [first_index, second_index], "question": question}


def _explicit_pregnancy_status(text):
    if re.search(r"\b(?:not pregnant|isn't pregnant|is not pregnant|no current pregnancy)\b", text, re.IGNORECASE):
        return "not_pregnant"
    if re.search(r"\b(?:currently pregnant|is pregnant|am pregnant|pregnant now)\b", text, re.IGNORECASE):
        return "pregnant"
    return None


def _delivery_mode(text):
    if re.search(r"\b(?:caesarean|cesarean|c-section)\b", text, re.IGNORECASE):
        return "caesarean"
    if re.search(r"\b(?:vaginal delivery|delivered vaginally|delivery was vaginal)\b", text, re.IGNORECASE):
        return "vaginal"
    return None


def _medication_polarities(text):
    found = {}
    no_medicines = re.search(r"\b(?:no medicines|no medications|not taking any medicines|takes no medicine)\b", text, re.IGNORECASE)
    if no_medicines:
        found["__all_medicines__"] = False
    for match in re.finditer(r"\b(?:taking|takes|using|uses|prescribed)\s+([a-z][a-z0-9-]{2,})\b", text, re.IGNORECASE):
        medicine = match.group(1).lower()
        if medicine in {"any", "no", "the", "her", "his", "medicine", "medicines", "medication"}:
            continue
        polarity = not _negated_fact(match.group(0), text)
        found[medicine] = polarity
    if found.get("__all_medicines__") is False:
        for medicine in list(found):
            if medicine != "__all_medicines__":
                found[medicine] = True
    return found


def _medication_conflict(first_text, second_text):
    first = _medication_polarities(first_text)
    second = _medication_polarities(second_text)
    first_none = first.get("__all_medicines__") is False
    second_none = second.get("__all_medicines__") is False
    first_named = {name for name, present in first.items() if name != "__all_medicines__" and present}
    second_named = {name for name, present in second.items() if name != "__all_medicines__" and present}
    if (first_none and second_named) or (second_none and first_named):
        return True
    return any(first[name] != second[name] for name in first.keys() & second.keys())


def _negated_fact(fact, text):
    for match in re.finditer(re.escape(fact), text, re.IGNORECASE):
        prefix = text[max(0, match.start() - 30):match.start()]
        if re.search(r"\b(?:no|not|never|denies|without)\s+(?:\w+\s+){0,3}$", prefix):
            return True
    return False
