"""One-answer clerking workflow with rules-first safety and verification."""

import neatlogs
import time

from quickhealth.clerking import ask_next_question, build_clerking_note
from quickhealth.pathways import select_pathway
from quickhealth.safety_rules import assess_urgency
from quickhealth.storage import record_model_usage, save_answer, save_result, save_verification_state
from quickhealth.verification import (
    CandidateDetectionError,
    completeness_check,
    completeness_follow_up,
    completeness_display,
    contradiction_check,
    contradiction_clarification_question,
    detect_free_text_candidates,
)


class _UsageRecordingClient:
    """Transparent model-client proxy; saves only token counts and elapsed time."""

    def __init__(self, client, session_id):
        self._client = client
        source_chat = getattr(client, "chat", None)
        self.chat = self._Chat(source_chat, session_id) if source_chat is not None else None

    class _Chat:
        def __init__(self, chat, session_id):
            self.completions = _UsageRecordingClient._Completions(chat.completions, session_id)

    class _Completions:
        def __init__(self, completions, session_id):
            self._completions = completions
            self._session_id = session_id

        def create(self, **kwargs):
            started = time.perf_counter()
            response = self._completions.create(**kwargs)
            elapsed_ms = (time.perf_counter() - started) * 1000
            usage = getattr(response, "usage", None)
            if usage is not None:
                record_model_usage(
                    self._session_id,
                    getattr(usage, "prompt_tokens", 0) or 0,
                    getattr(usage, "completion_tokens", 0) or 0,
                    elapsed_ms,
                )
            return response


@neatlogs.span(kind="WORKFLOW", name="quickhealth_clerking_session", capture_input=False, capture_output=False)
def process_answer(client, session_id, history, answer, current_question, verification_state=None):
    """Save one answer; emergency rules always run before other checks or questions."""
    client = _UsageRecordingClient(client, session_id)
    save_answer(session_id, current_question, answer)
    updated_history = history + [
        {"role": "assistant", "content": current_question},
        {"role": "user", "content": answer},
    ]
    patient_type = select_pathway(updated_history)
    safety = assess_urgency(updated_history, patient_type)
    state = verification_state if isinstance(verification_state, dict) else {}

    if safety["urgency"] == "EMERGENCY_NOW":
        save_result(
            session_id,
            "Questionnaire stopped because a rules-based emergency red flag was reported.",
            safety["message"], safety["urgency"], patient_type,
        )
        return updated_history, None, {
            "emergency": True, "urgency": safety["urgency"], "message": safety["message"],
        }, state

    completeness = completeness_check(patient_type, state.get("completeness", {}), current_question, answer)
    state["completeness"] = completeness["state"]
    contradiction_state = state.get("contradictions", {})
    contradiction_state["pathway"] = patient_type
    try:
        deterministic = contradiction_check(updated_history, contradiction_state)
        if deterministic["pending"]:
            state["contradictions"] = deterministic["state"]
            save_verification_state(session_id, state)
            active = next((item for item in deterministic["candidates"] if item["id"] == deterministic["state"].get("active_contradiction_id")), deterministic["candidates"][0])
            return updated_history, contradiction_clarification_question(active), None, state
        # Model-assisted detection is only a candidate finder; it cannot resolve facts or urgency.
        model_candidates = detect_free_text_candidates(client, updated_history)
        contradiction = contradiction_check(updated_history, deterministic["state"], model_candidates)
    except CandidateDetectionError:
        state["contradictions"] = contradiction_state
        save_verification_state(session_id, state)
        return updated_history, None, {
            "emergency": False, "blocked": True, "incomplete": True,
            "message": "Possible inconsistencies could not be checked safely. Review the history before continuing.",
            "urgency": safety["urgency"], "missing": completeness_display(completeness),
        }, state
    state["contradictions"] = contradiction["state"]
    save_verification_state(session_id, state)

    # A possible conflict pauses routine questions until the user clarifies it.
    if contradiction["unresolved"]:
        unresolved = [item for item in contradiction["candidates"] if item["status"] == "unresolved"]
        return updated_history, None, {
            "emergency": False, "incomplete": True, "urgency": safety["urgency"],
            "message": "A possible inconsistency could not be clarified. The original answers are preserved; do not treat this session as complete.",
            "missing": completeness_display(completeness),
            "contradictions": [item["facts"] for item in unresolved],
        }, state
    if contradiction["pending"]:
        active = next((item for item in contradiction["candidates"] if item["id"] == contradiction["state"].get("active_contradiction_id")), contradiction["candidates"][0])
        return updated_history, contradiction_clarification_question(active), None, state

    next_question = ask_next_question(client, updated_history, patient_type)
    if next_question.strip().upper() != "COMPLETE":
        return updated_history, next_question, None, state

    # A model's COMPLETE signal cannot overrule unresolved verification results.
    if contradiction["unresolved"]:
        unresolved = [item for item in contradiction["candidates"] if item["status"] == "unresolved"]
        return updated_history, None, {
            "emergency": False, "incomplete": True, "urgency": safety["urgency"],
            "message": "The possible inconsistency remains unresolved. The original answers are preserved; do not treat this session as complete.",
            "missing": completeness_display(completeness),
            "contradictions": [item["facts"] for item in unresolved],
        }, state

    missing = completeness["missing"]
    if missing:
        follow_up = completeness_follow_up(completeness)
        state["completeness"] = completeness["state"]
        save_verification_state(session_id, state)
        if follow_up:
            return updated_history, follow_up, None, state
        return updated_history, None, {
            "emergency": False, "incomplete": True, "urgency": safety["urgency"],
            "message": "Required sections remain unanswered or unknown after focused follow-ups. No final note was generated.",
            "missing": completeness_display(completeness),
        }, state

    note, summary = build_clerking_note(client, updated_history, patient_type)
    save_result(session_id, note, summary, safety["urgency"], patient_type)
    return updated_history, None, {
        "note": note, "summary": summary, "urgency": safety["urgency"],
        "missing": [], "contradictions": [], "emergency": False,
        "incomplete": False,
    }, state
