"""Verification tests use invented training-case text only."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from quickhealth import verification
from quickhealth.privacy import redact_trace_content
from quickhealth.storage import get_verification_state, save_verification_state
from quickhealth.workflow import process_answer


class CompletenessTests(unittest.TestCase):
    def test_each_pathway_has_required_sections(self):
        pathways = {
            "general": ("general", ("biodata", "systems_review")),
            "child_under_5": ("paediatric", ("birth_neonatal_history", "feeding_hydration", "development_milestones")),
            "pregnancy_trimester_2": ("antenatal", ("lmp_and_certainty", "gravidity_parity", "pregnancy_danger_signs")),
            "postpartum": ("postpartum", ("time_since_delivery", "postpartum_bleeding", "postpartum_seizures")),
        }
        for pathway, (group, expected) in pathways.items():
            with self.subTest(pathway=pathway):
                result = verification.completeness_check(pathway, {})
                self.assertEqual(result["state"]["pathway"], group)
                self.assertTrue(set(expected).issubset(result["missing"]))

    def test_three_medication_categories_are_always_required(self):
        missing = verification.completeness_check("general", {})["missing"]
        for section in ("prescribed_medicines", "herbal_traditional_medicines", "otc_medicines"):
            self.assertIn(section, missing)

    def test_unknown_and_unanswered_are_not_complete(self):
        state = {"sections": {"biodata": {"status": "unknown", "followups": 0}}}
        result = verification.completeness_check("general", state)
        self.assertEqual(result["state"]["sections"]["biodata"]["status"], "unknown")
        self.assertIn("biodata", result["missing"])
        self.assertIn("biodata", result["statuses"]["unknown"])
        self.assertIn("presenting_complaint", result["statuses"]["unanswered"])

    def test_answer_of_unknown_to_targeted_follow_up_stays_incomplete(self):
        state = {"active_section": "prescribed_medicines", "sections": {}}
        result = verification.completeness_check(
            "general", state, "What prescribed medicines are used?", "Unknown."
        )
        self.assertEqual(result["state"]["sections"]["prescribed_medicines"]["status"], "unknown")
        self.assertIn("prescribed_medicines", result["missing"])

    def test_follow_up_is_focused_and_only_scheduled_once(self):
        check = verification.completeness_check("general", {})
        question = verification.completeness_follow_up(check)
        self.assertIn("made-up age", question)
        questions = [question]
        while True:
            question = verification.completeness_follow_up(check)
            if question is None:
                break
            questions.append(question)
        self.assertEqual(len(questions), len(check["missing"]))
        self.assertIsNone(verification.completeness_follow_up(check))


class ContradictionTests(unittest.TestCase):
    def test_lmp_and_gestational_age_conflict_is_candidate(self):
        history = [
            {"role": "assistant", "content": "What was the LMP date, and is it certain?"},
            {"role": "user", "content": "2026-01-01, certain"},
            {"role": "assistant", "content": "What gestational age is recorded?"},
            {"role": "user", "content": "30 weeks"},
        ]
        result = verification.contradiction_check(history, {})
        self.assertTrue(result["pending"])
        self.assertEqual(result["candidates"][0]["kind"], "lmp_gestational_age_difference_over_7_days")

    def test_three_month_old_family_food_and_walking_are_clarification_candidates(self):
        history = [
            {"role": "assistant", "content": "How old is the child?"},
            {"role": "user", "content": "Fictional child is 3 months old."},
            {"role": "assistant", "content": "Tell me about feeding and milestones."},
            {"role": "user", "content": "Eats ordinary family food and walks independently."},
        ]
        candidates = verification.contradiction_check(history, {})["candidates"]
        self.assertEqual({row["kind"] for row in candidates}, {
            "family_food_at_three_months", "independent_walking_at_three_months",
        })
        self.assertTrue(all("not a conclusion" in row["question"] for row in candidates))

    def test_three_month_old_pap_family_food_and_starting_to_walk_are_candidates(self):
        history = [
            {"role": "assistant", "content": "How old is the child?"},
            {"role": "user", "content": "A fictional child is 3 months old."},
            {"role": "assistant", "content": "What foods and movement milestones are reported?"},
            {"role": "user", "content": "The caregiver says the child is eating pap and family food and starting to walk."},
        ]
        candidates = verification.contradiction_check(history, {})["candidates"]
        self.assertEqual({row["kind"] for row in candidates}, {
            "family_food_at_three_months", "independent_walking_at_three_months",
        })

    def test_medication_conflict_preserves_answers_and_deduplicates(self):
        history = [
            {"role": "assistant", "content": "Any medicines?"},
            {"role": "user", "content": "Fictional patient takes paracetamol."},
            {"role": "assistant", "content": "Any other medicines?"},
            {"role": "user", "content": "Fictional patient takes no medicines."},
        ]
        first = verification.contradiction_check(history, {})
        second = verification.contradiction_check(history, first["state"])
        self.assertTrue(first["pending"])
        self.assertEqual(len(second["state"]["contradictions"]), 1)
        original = list(history)
        clarification = verification.contradiction_clarification_question(first["candidates"][0])
        self.assertIn("both be kept", clarification)
        self.assertEqual(history, original)

    def test_pregnancy_status_conflict(self):
        history = [
            {"role": "user", "content": "Fictional patient is currently pregnant."},
            {"role": "user", "content": "Fictional patient is not pregnant."},
        ]
        self.assertEqual(
            verification.contradiction_check(history, {})["candidates"][0]["kind"],
            "pregnancy_status_conflict",
        )

    def test_delivery_history_conflict_is_clarified(self):
        history = [
            {"role": "user", "content": "Fictional previous delivery was by caesarean section."},
            {"role": "user", "content": "Fictional previous delivery was vaginal."},
        ]
        self.assertEqual(
            verification.contradiction_check(history, {})["candidates"][0]["kind"],
            "delivery_mode_conflict",
        )

    def test_unusual_but_possible_or_explicitly_denied_development_is_not_flagged(self):
        history = [
            {"role": "user", "content": "Fictional child is 3-month-old."},
            {"role": "user", "content": "The child does not walk independently and is not eating ordinary family food."},
        ]
        self.assertEqual(verification.contradiction_check(history, {})["candidates"], [])

    def test_clarification_stored_separately_without_overwriting_original(self):
        history = [
            {"role": "assistant", "content": "Any medicines?"},
            {"role": "user", "content": "Fictional patient takes paracetamol."},
            {"role": "assistant", "content": "Any other medicines?"},
            {"role": "user", "content": "Fictional patient takes no medicines."},
        ]
        pending = verification.contradiction_check(history, {})
        clarification_history = history + [
            {"role": "assistant", "content": "Please clarify the two statements."},
            {"role": "user", "content": "Both refer to different dates."},
        ]
        resolved = verification.contradiction_check(clarification_history, pending["state"])
        self.assertEqual(resolved["state"]["contradictions"][0]["status"], "clarified")
        self.assertEqual(history[1]["content"], "Fictional patient takes paracetamol.")
        self.assertEqual(history[3]["content"], "Fictional patient takes no medicines.")


class WorkflowAndStorageTests(unittest.TestCase):
    def test_emergency_has_priority_over_both_verifiers_and_model(self):
        client = SimpleNamespace()
        with patch("quickhealth.workflow.save_answer"), patch("quickhealth.workflow.save_result"), \
                patch("quickhealth.workflow.completeness_check") as complete, \
                patch("quickhealth.workflow.contradiction_check") as contradict:
            history, question, result, _state = process_answer(
                client, "fictional-id", [], "Fictional child had convulsions.", "Main concern?"
            )
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")
        self.assertIsNone(question)
        complete.assert_not_called()
        contradict.assert_not_called()

    def test_model_complete_does_not_generate_note_with_missing_sections(self):
        fake_client = _Client("COMPLETE")
        check = {"state": {"sections": {}}, "required": ["biodata"], "missing": ["biodata"], "statuses": {}}
        with patch("quickhealth.workflow.save_answer"), patch("quickhealth.workflow.save_verification_state"), \
                patch("quickhealth.workflow.completeness_check", return_value=check), \
                patch("quickhealth.workflow.detect_free_text_candidates", return_value=[]), \
                patch("quickhealth.workflow.build_clerking_note") as note:
            _history, question, result, _state = process_answer(
                fake_client, "fictional-id", [], "Fictional case has an invented concern.", "Main concern?"
            )
        self.assertIsNone(result)
        self.assertEqual(question, verification.FOLLOW_UP_QUESTIONS["biodata"])
        note.assert_not_called()

    def test_model_complete_sends_back_for_herbal_and_otc_medicine_history(self):
        sections = verification.PATHWAY_SECTIONS["general"]
        for missing_section in ("herbal_traditional_medicines", "otc_medicines"):
            with self.subTest(section=missing_section):
                section_state = {
                    name: {"status": "unanswered" if name == missing_section else "answered", "followups": 0}
                    for name in sections
                }
                check = {
                    "state": {"sections": section_state, "pathway": "general", "active_section": None},
                    "required": list(sections), "missing": [missing_section],
                    "statuses": {"answered": [], "unanswered": [missing_section], "unknown": []},
                }
                client = _Client("COMPLETE")
                with patch("quickhealth.workflow.save_answer"), patch("quickhealth.workflow.save_verification_state"), \
                        patch("quickhealth.workflow.completeness_check", return_value=check), \
                        patch("quickhealth.workflow.detect_free_text_candidates", return_value=[]), \
                        patch("quickhealth.workflow.build_clerking_note") as note:
                    _history, follow_up, result, state = process_answer(
                        client, "fictional-id", [],
                        "Fictional adult, made-up age 30, mild cough.", "What is the main concern?",
                    )
                self.assertEqual(follow_up, verification.FOLLOW_UP_QUESTIONS[missing_section])
                self.assertEqual(state["completeness"]["active_section"], missing_section)
                self.assertIsNone(result)
                note.assert_not_called()

    def test_verification_state_round_trips_in_sqlite(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "temporary.sqlite3"
            from quickhealth import storage
            with patch.object(storage, "DB_PATH", db):
                session_id = storage.create_session()
                state = {"completeness": {"pathway": "general"}, "contradictions": {"contradictions": []}}
                save_verification_state(session_id, state)
                self.assertEqual(get_verification_state(session_id), state)


class CandidateDetectionTests(unittest.TestCase):
    def test_model_suspicions_are_candidates_and_bad_output_blocks(self):
        payload = json.dumps({"candidates": [{
            "first_answer_number": 1, "second_answer_number": 2,
            "reason_code": "date_conflict", "clarification_question": "Which date should be clarified?",
        }]})
        client = _Client(payload)
        history = [
            {"role": "user", "content": "Fictional date one."},
            {"role": "user", "content": "Fictional date two."},
        ]
        result = verification.detect_free_text_candidates(client, history)
        self.assertEqual(result[0]["kind"], "model_date_conflict")
        bad = _Client("not json")
        with self.assertRaises(verification.CandidateDetectionError):
            verification.detect_free_text_candidates(bad, history)
        with self.assertRaisesRegex(verification.CandidateDetectionError, "Free-text candidate detection failed") as raised:
            verification.detect_free_text_candidates(bad, history)
        self.assertNotIn("Fictional date one", str(raised.exception))


class TracePrivacyTests(unittest.TestCase):
    def test_named_check_spans_emit_only_safe_categories(self):
        class RecordingSpan:
            def __init__(self):
                self.attributes = {}

            def is_recording(self):
                return True

            def set_attribute(self, key, value):
                self.attributes[key] = value

        span = RecordingSpan()
        with patch("quickhealth.verification.otel_trace.get_current_span", return_value=span):
            verification._span_attributes(
                "completeness_check", "child_under_5", True,
                missing_count=4, suspected_count=0, resolution="none",
            )
        self.assertEqual(span.attributes["quickhealth.checker.name"], "completeness_check")
        self.assertEqual(span.attributes["quickhealth.pathway"], "paediatric")
        self.assertEqual(span.attributes["quickhealth.missing_section_count"], 4)
        self.assertNotIn("Fictional", repr(span.attributes))
        with patch("quickhealth.verification.otel_trace.get_current_span", return_value=span):
            verification._span_attributes(
                "contradiction_check", "pregnancy_trimester_2", True,
                suspected_count=1, resolution="pending",
            )
        self.assertEqual(span.attributes["quickhealth.checker.name"], "contradiction_check")

    def test_checker_exception_propagates_instead_of_becoming_complete(self):
        with patch("quickhealth.verification.pathway_group", return_value="invalid_pathway"):
            with self.assertRaises(KeyError):
                verification.completeness_check("fictional-only", {})

    def test_neatlogs_mask_redacts_prompt_answer_and_credential_fields(self):
        fake_span = {"attributes": {
            "neatlogs.llm.input_messages.0.content": "fictional history text",
            "neatlogs.llm.output_messages.0.content": "fictional note text",
            "neatlogs.openai.api_key": "not-a-real-key-placeholder",
            "quickhealth.checker.name": "completeness_check",
        }}
        masked = redact_trace_content(fake_span)
        self.assertEqual(masked["attributes"]["neatlogs.llm.input_messages.0.content"], "[redacted]")
        self.assertEqual(masked["attributes"]["neatlogs.llm.output_messages.0.content"], "[redacted]")
        self.assertEqual(masked["attributes"]["neatlogs.openai.api_key"], "[redacted]")
        self.assertEqual(masked["attributes"]["quickhealth.checker.name"], "completeness_check")


class _Client:
    def __init__(self, content):
        message = SimpleNamespace(content=content)
        self.chat = SimpleNamespace(completions=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(choices=[SimpleNamespace(message=message)])
        ))


if __name__ == "__main__":
    unittest.main()
