"""Pathway and date-estimate tests use fictional cases only."""

from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from quickhealth.obstetric_dates import calculate_obstetric_dates, find_lmp_estimate
from quickhealth.pathways import history_guidance, select_pathway
from quickhealth.workflow import process_answer


class PathwayAndDateTests(unittest.TestCase):
    def test_pathway_selection_for_child_pregnancy_and_postpartum(self):
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional 8 month old child"}]),
            "child_under_5",
        )
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional pregnant person, second trimester"}]),
            "pregnancy_trimester_2",
        )
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional postpartum person, 5 days after delivery"}]),
            "postpartum",
        )

    def test_hyphenated_age_is_detected_without_using_illness_duration_as_age(self):
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional 8-month-old child has fever for 2 days."}]),
            "child_under_5",
        )
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional 3-month-old baby has a cough for 2 days."}]),
            "child_under_5",
        )
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional 3-week-old baby has fever for 2 days."}]),
            "infant_under_2_months",
        )
        self.assertEqual(
            select_pathway([{"role": "user", "content": "Fictional 5-year-old child has a cough."}]),
            "unknown",
        )

    def test_pathway_guidance_covers_required_question_topics(self):
        paediatric = history_guidance("child_under_5").lower()
        for topic in ("caregiver", "age", "infant", "prematurity", "feeding", "breastfeeding", "immunisation", "developmental", "regression", "growth", "sick contacts", "danger signs"):
            self.assertIn(topic, paediatric)

        obstetric = history_guidance("pregnancy_trimester_2").lower()
        for topic in ("lmp", "edd", "gestational age", "gravidity", "parity", "antenatal", "previous pregnancies", "delivery modes", "danger signs"):
            self.assertIn(topic, obstetric)

        postpartum = history_guidance("postpartum").lower()
        for topic in ("time since delivery", "delivery details", "bleeding", "fever", "severe headache", "breathing difficulty", "seizures", "danger signs"):
            self.assertIn(topic, postpartum)

    def test_lmp_calculations_use_280_days_and_completed_weeks(self):
        result = calculate_obstetric_dates("2026-01-01", today=date(2026, 1, 29))
        self.assertEqual(result, {
            "status": "estimated", "edd": "2026-10-08", "weeks": 4, "days": 0,
        })

    def test_invalid_future_and_uncertain_lmp_do_not_produce_estimates(self):
        today = date(2026, 6, 1)
        self.assertEqual(calculate_obstetric_dates("2026-02-30", today=today)["status"], "invalid")
        self.assertEqual(calculate_obstetric_dates("2026-06-02", today=today)["status"], "future")
        self.assertEqual(calculate_obstetric_dates("2026-01-01", today=today, is_certain=False)["status"], "uncertain")

    def test_lmp_answer_requires_explicit_certainty(self):
        history = [
            {"role": "assistant", "content": "What was the LMP? Is that date certain?"},
            {"role": "user", "content": "2026-01-01, certain"},
        ]
        self.assertEqual(find_lmp_estimate(history, today=date(2026, 1, 29))["weeks"], 4)
        history[-1]["content"] = "2026-01-01, not sure"
        self.assertEqual(find_lmp_estimate(history, today=date(2026, 1, 29))["status"], "uncertain")

    def test_scripted_fictional_conversation_for_each_pathway(self):
        scripts = [
            (
                "Fictional 8 month old child has a mild cough.",
                ["How is the child feeding and drinking?", "What immunisations has the child received?", "COMPLETE"],
                "child_under_5",
                ("caregiver", "breastfeeding", "immunisation"),
            ),
            (
                "Fictional patient is pregnant, second trimester, LMP 2026-01-01 certain.",
                ["Was antenatal care booked?", "Any current pregnancy danger signs?", "COMPLETE"],
                "pregnancy_trimester_2",
                ("lmp", "gravidity", "parity", "antenatal", "danger signs"),
            ),
            (
                "Fictional patient is postpartum, 5 days after delivery.",
                ["How was the delivery?", "Any postpartum bleeding, fever, or breathing difficulty?", "COMPLETE"],
                "postpartum",
                ("time since delivery", "bleeding", "fever", "breathing difficulty", "seizures"),
            ),
        ]

        for first_answer, questions, expected_pathway, expected_guidance in scripts:
            with self.subTest(pathway=expected_pathway):
                fake_client = _ScriptedClient(questions)
                history = []
                current_question = "Describe this fictional case."
                with patch("quickhealth.workflow.save_answer"), patch("quickhealth.workflow.save_result"), \
                        patch("quickhealth.workflow.save_verification_state"), \
                        patch("quickhealth.workflow.build_clerking_note", return_value=("fictional note", "fictional summary")), \
                        patch("quickhealth.workflow.completeness_check", side_effect=lambda pathway, state, question, answer: {"state": {"sections": {}, "pathway": "general"}, "required": [], "missing": [], "statuses": {}}), \
                        patch("quickhealth.workflow.detect_free_text_candidates", return_value=[]):
                    answer = first_answer
                    for _ in questions:
                        history, current_question, result, _verification = process_answer(
                            fake_client, "fictional-session", history, answer, current_question
                        )
                        if result is not None:
                            self.assertFalse(result.get("emergency"))
                            break
                        answer = "Fictional caregiver/patient provides the requested history; no additional danger signs reported."
                self.assertEqual(select_pathway(history), expected_pathway)
                self.assertEqual(len(fake_client.system_prompts), len(questions))
                combined_prompt = " ".join(fake_client.system_prompts).lower()
                for topic in expected_guidance:
                    self.assertIn(topic, combined_prompt)

    def test_emergency_stops_before_the_next_model_question(self):
        fake_client = _ScriptedClient(["This should not be requested"])
        with patch("quickhealth.workflow.save_answer"), patch("quickhealth.workflow.save_result"), \
                patch("quickhealth.workflow.save_verification_state"), \
                patch("quickhealth.workflow.completeness_check", return_value={"state": {}, "required": [], "missing": [], "statuses": {}}):
            history, next_question, result, _verification = process_answer(
                fake_client,
                "fictional-session",
                [],
                "Fictional 8 month old child had convulsions.",
                "What is the fictional patient's main concern?",
            )
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")
        self.assertIsNone(next_question)
        self.assertEqual(fake_client.system_prompts, [])


class _ScriptedClient:
    """Minimal fake chat client returning predetermined fictional script steps."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.system_prompts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, *, messages, **kwargs):
        self.system_prompts.append(messages[0]["content"])
        content = self.responses.pop(0)
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


if __name__ == "__main__":
    unittest.main()
