"""Question selection and note helpers for fictional clerking sessions."""

import json
import os

import neatlogs

SYSTEM_PROMPT = """You are a history-taking assistant for a fictional training case in Nigeria.
Never diagnose or decide urgency. Ask exactly one concise next history question at a time.
Cover biodata (made-up age, sex, pregnancy/postpartum status when relevant), presenting
complaint and onset, character, severity, timing, aggravating/relieving factors and
associated symptoms; past medical and surgical history; prescription, over-the-counter
and herbal medicines; allergies; family and social history; and systems review.
Adapt follow-ups to the answers. For children under five (including infants), ask age in
months when useful, feeding, birth history when relevant, immunisations, wet nappies,
breathing and caregiver concerns. For pregnancy/postpartum, ask gestational or postpartum
timing, antenatal care, bleeding, fluid loss, severe headache/vision changes, fetal
movement when relevant, and delivery details when postpartum. Avoid asking identifying
details. If enough history has been gathered, reply with exactly COMPLETE. Do not give
medical advice, diagnoses, or urgency classifications."""


@neatlogs.span(kind="TOOL", name="adaptive_clerking_loop")
def ask_next_question(client, history):
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", ""),
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


@neatlogs.span(kind="TOOL", name="intake_and_patient_type_detection")
def detect_patient_type(history):
    text = " ".join(item["content"] for item in history if item["role"] == "user").lower()
    if any(word in text for word in ("pregnant", "pregnancy", "postpartum", "gave birth", "weeks gestation")):
        return "pregnant_or_postpartum"
    import re

    match = re.search(r"\b(\d{1,2})\s*(?:months?|mos?)\b", text)
    years = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?)\b", text)
    if (match and int(match.group(1)) < 60) or (years and int(years.group(1)) < 5):
        return "child_under_5"
    return "general"


@neatlogs.span(kind="TOOL", name="completeness_verifier")
def get_missing_sections(history):
    text = " ".join(item["content"] for item in history if item["role"] == "user").lower()
    sections = {
        "presenting complaint and symptom details": ("pain", "symptom", "complaint", "cough", "fever", "vomit"),
        "past medical history": ("medical history", "condition", "illness", "asthma", "diabetes"),
        "past surgical history": ("surgery", "operation", "surgical"),
        "medicines (including herbal and over-the-counter)": ("medicine", "medication", "drug", "herbal", "over-the-counter", "otc"),
        "allergies": ("allergy", "allergic", "no known allergies"),
        "family history": ("family", "relative", "mother", "father"),
        "social history": ("social", "smoke", "alcohol", "home", "work"),
        "systems review": ("systems review", "review of systems", "other symptoms"),
    }
    return [label for label, hints in sections.items() if not any(hint in text for hint in hints)]


@neatlogs.span(kind="TOOL", name="contradiction_checker")
def find_contradictions(client, history):
    prompt = "Find only clear internal inconsistencies in this fictional history. Return a short JSON array of questions to clarify; return [] if none. Do not diagnose or classify urgency. History: " + json.dumps(history)
    response = client.chat.completions.create(
        model=__import__("os").environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    try:
        value = json.loads(response.choices[0].message.content)
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


@neatlogs.span(kind="TOOL", name="note_generator")
def build_clerking_note(client, history, patient_type):
    prompt = f"""Create a concise structured clerking note for a fictional patient, patient pathway: {patient_type}.
Use headings for Biodata, Presenting complaint, History of presenting complaint (onset,
character, severity, timing, aggravating/relieving factors, associated symptoms), Past
medical history, Past surgical history, Medicines (prescribed, over-the-counter, herbal),
Allergies, Family history, Social history, and Systems review. Mark missing information
as 'Not provided'. Then add a separate plain-language summary. Never diagnose, infer a
disease, give treatment advice, or classify urgency. If differentials are requested or
included, label them exactly 'for clinician consideration'. The history is: {json.dumps(history)}"""
    response = client.chat.completions.create(
        model=__import__("os").environ["OPENAI_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    content = response.choices[0].message.content.strip()
    marker = "Plain-language summary"
    if marker.lower() in content.lower():
        index = content.lower().index(marker.lower())
        return content[:index].strip(), content[index + len(marker):].lstrip(" :\n")
    return content, "This summary could not be separated from the note. Please review the note with a clinician."
