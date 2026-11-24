import unittest

from config import MAX_RESUMES
from ui.helpers import candidate_matches_search


class CandidateSearchTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {
            "name": "Alex Morgan",
            "best_role": "Data Engineer",
            "text": "Experienced with distributed data platforms.",
            "resume_data": {
                "skills": ["Python"],
                "keywords": ["Spark", "ETL"],
            },
        }

    def test_search_matches_candidate_name_and_case_insensitively(self):
        self.assertTrue(candidate_matches_search(self.candidate, "alex"))
        self.assertTrue(candidate_matches_search(self.candidate, "MORGAN"))

    def test_search_matches_keywords_and_resume_text(self):
        self.assertTrue(candidate_matches_search(self.candidate, "spark"))
        self.assertTrue(candidate_matches_search(self.candidate, "distributed data"))

    def test_search_does_not_match_separate_skill_or_role_fields(self):
        self.assertFalse(candidate_matches_search(self.candidate, "python"))
        self.assertFalse(candidate_matches_search(self.candidate, "engineer"))

    def test_empty_search_matches_every_candidate(self):
        self.assertTrue(candidate_matches_search(self.candidate, "  "))

    def test_resume_cap_is_fixed_at_four(self):
        self.assertEqual(MAX_RESUMES, 4)


if __name__ == "__main__":
    unittest.main()
