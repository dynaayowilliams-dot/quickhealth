"""Question selection and note helpers for fictional clerking sessions."""

import json
import os

import neatlogs
from quickhealth.pathways import collect_pathway_question

SYSTEM_PROMPT = """You are a history-taking assistant for a fictional training case in Nigeria.
Never diagnose or decide urgency. Ask exactly one concise next history question at a time.
Cover biodata (made-up age, sex, pregnancy/postpartum status when relevant), presenting
complaint and onset, character, severity, timing, aggravating/relieving factors and
associated symptoms; past medical and surgical history; prescription, over-the-counter
and herbal medicines; allergies; family and social history; and systems review.
Adapt follow-ups to the answers. Avoid asking identifying details. If enough history has
been gathered, reply with exactly COMPLETE. Do not give medical advice, diagnoses, or
urgency classifications. Never calculate EDD or gestational age; Python handles estimates."""


@neatlogs.span(kind="TOOL", name="adaptive_clerking_loop", capture_input=False, capture_output=False)
def ask_next_question(client, history, patient_type="unknown"):
    def request_question(pathway_guidance):
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", ""),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + pathway_guidance},
                *history,
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    return collect_pathway_question(patient_type, request_question)


@neatlogs.span(kind="TOOL", name="note_generator", capture_input=False, capture_output=False)
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
