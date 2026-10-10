"""Focused checks of rules using fictional training-case text only."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quickhealth import safety_rules


class SafetyRulesTests(unittest.TestCase):
    def assess(self, answer, pathway):
        return safety_rules.assess_urgency(
            [{"role": "user", "content": answer}], pathway
        )

    def test_child_convulsions_escalate_to_emergency(self):
        result = self.assess("The fictional child had convulsions today.", "child_under_5")
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")
        self.assertIn("child_convulsions", result["matches"])

    def test_infant_fever_escalates_to_emergency(self):
        result = self.assess("Fictional 3 week old baby has fever.", "infant_under_2_months")
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")

    def test_pregnancy_fever_with_chills_requires_same_day_care(self):
        result = self.assess("Fictional pregnant patient reports fever with chills.", "pregnancy_trimester_2")
        self.assertEqual(result["urgency"], "SEE_CLINICIAN_TODAY")

    def test_reduced_fetal_movement_worded_as_much_less_escalates(self):
        result = self.assess(
            "Fictional patient is 36 weeks pregnant; the baby has been moving much less since yesterday.",
            "pregnancy_trimester_3",
        )
        self.assertEqual(result["urgency"], "SEE_CLINICIAN_TODAY")
        self.assertIn("pregnancy_reduced_fetal_movement", result["matches"])

    def test_pregnancy_headache_with_visual_changes_escalates_even_if_headache_is_described_as_small(self):
        result = safety_rules.assess_urgency(
            [
                {"role": "user", "content": "Fictional patient is 28 weeks pregnant and has had a small headache for 2 days."},
                {"role": "assistant", "content": "Have you had blurred vision or any change in your vision?"},
                {"role": "user", "content": "Yes, blurred vision has occurred."},
            ],
            "pregnancy_trimester_2",
        )
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")
        self.assertIn("pregnancy_headache_with_visual_changes", result["matches"])

    def test_routine_requires_a_complete_rules_covered_negative_screen(self):
        question = (
            "Have there been severe headache with blurred vision, vaginal bleeding, convulsions, "
            "reduced fetal movement, leaking fluid, severe abdominal pain, or fever with chills?"
        )
        history = [
            {"role": "assistant", "content": question},
            {"role": "user", "content": "No, none of the listed pregnancy danger signs have been reported."},
        ]
        result = safety_rules.assess_urgency(history, "pregnancy_trimester_1")
        self.assertEqual(result["urgency"], "ROUTINE")

    def test_generic_or_partial_negative_screen_does_not_allow_routine(self):
        history = [
            {"role": "assistant", "content": "Have any pregnancy danger signs been reported?"},
            {"role": "user", "content": "No."},
        ]
        result = safety_rules.assess_urgency(history, "pregnancy_trimester_1")
        self.assertEqual(result["urgency"], "SEE_CLINICIAN_TODAY")

    def test_postpartum_increased_bleeding_escalates_to_emergency(self):
        result = self.assess("Fictional postpartum patient says vaginal bleeding has increased.", "postpartum")
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")

    def test_postpartum_breathing_difficulty_escalates_to_emergency(self):
        result = self.assess("Fictional postpartum patient reports difficulty breathing.", "postpartum")
        self.assertEqual(result["urgency"], "EMERGENCY_NOW")

    def test_routine_json_default_does_not_silently_mean_routine(self):
        result = self.assess("Fictional child has a mild cough.", "child_under_5")
        self.assertEqual(result["urgency"], "SEE_CLINICIAN_TODAY")

    def test_unrecognized_pathway_escalates(self):
        result = self.assess("Fictional person describes a concern.", "not_a_pathway")
        self.assertEqual(result["urgency"], "SEE_CLINICIAN_TODAY")

    def test_missing_or_invalid_rules_escalate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing-red-flags.json"
            with patch.object(safety_rules, "RULES_PATH", missing_path):
                missing = self.assess("Fictional child has a cough.", "child_under_5")
                with self.assertRaises(safety_rules.RulesError):
                    safety_rules.load_rules()
        self.assertEqual(missing["urgency"], "SEE_CLINICIAN_TODAY")

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "rules.json"
            invalid_path.write_text("not json", encoding="utf-8")
            with patch.object(safety_rules, "RULES_PATH", invalid_path):
                invalid = self.assess("Fictional child has a cough.", "child_under_5")
                with self.assertRaises(safety_rules.RulesError):
                    safety_rules.load_rules()
        self.assertEqual(invalid["urgency"], "SEE_CLINICIAN_TODAY")

    def test_rule_schema_requires_review_metadata(self):
        data = safety_rules.load_rules()
        data["rules"][0]["reviewed_by_clinician"] = True
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rules.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(safety_rules.RulesError):
                safety_rules.load_rules(path)


if __name__ == "__main__":
    unittest.main()
