"""UI presentation labels for fictional QuickHealth pathways."""

import unittest

from quickhealth.ui import pathway_card_details, pending_conflict_count


class PathwayCardTests(unittest.TestCase):
    def test_maternal_pathway_cards_are_distinct(self):
        pregnancy = pathway_card_details("pregnancy_trimester_2")
        postpartum = pathway_card_details("postpartum")
        self.assertIn("Pregnancy care", pregnancy[0])
        self.assertIn("Postpartum care", postpartum[0])
        self.assertNotEqual(pregnancy[3], postpartum[3])

    def test_child_and_infant_cards_explain_age_friendly_path(self):
        child = pathway_card_details("child_under_5")
        infant = pathway_card_details("infant_under_2_months")
        self.assertIn("caregiver", child[1].lower())
        self.assertIn("days or weeks", infant[1].lower())

    def test_unknown_trimester_is_not_presented_as_a_known_trimester(self):
        pathway = pathway_card_details("pregnancy_trimester_unknown")
        self.assertEqual(pathway[0], "Pregnancy care")
        self.assertIn("not been identified", pathway[1])

    def test_pending_conflict_count_does_not_depend_on_raw_answer_text(self):
        state = {"contradictions": {"contradictions": [
            {"status": "pending", "question": "fictional answer text"},
            {"status": "clarified"},
            {"status": "unresolved"},
        ]}}
        self.assertEqual(pending_conflict_count(state), 1)


if __name__ == "__main__":
    unittest.main()
