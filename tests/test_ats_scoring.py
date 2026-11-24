import unittest

from config import BREAKDOWN_LABELS, DEFAULT_ATS_WEIGHTS
from scoring.ats import classify_candidate_status, compute_ats_score, rebalance_weights
from scoring.deterministic import compute_deterministic_breakdown


class ATSScoringTests(unittest.TestCase):
    def test_default_weights_cover_six_components_and_total_100(self):
        self.assertEqual(
            DEFAULT_ATS_WEIGHTS,
            {
                "skills": 40,
                "experience": 20,
                "education": 20,
                "projects": 8,
                "certifications": 6,
                "keywords": 6,
            },
        )
        self.assertEqual(sum(DEFAULT_ATS_WEIGHTS.values()), 100)
        self.assertEqual(set(BREAKDOWN_LABELS), set(DEFAULT_ATS_WEIGHTS))

    def test_ats_score_ignores_profile_completeness(self):
        breakdown = {key: 100 for key in DEFAULT_ATS_WEIGHTS}
        breakdown["skills"] = 50
        breakdown["resume_quality"] = 0
        weights = dict(DEFAULT_ATS_WEIGHTS, resume_quality=100)

        self.assertEqual(compute_ats_score(breakdown, weights), 80)

    def test_rebalance_keeps_six_weights_in_range_and_total_100(self):
        old_weights = dict(DEFAULT_ATS_WEIGHTS, resume_quality=5)
        for key in DEFAULT_ATS_WEIGHTS:
            for value in (0, 1, 17.7, 40, 42.3, 99, 100):
                with self.subTest(key=key, value=value):
                    weights = rebalance_weights(key, value, old_weights)
                    self.assertEqual(set(weights), set(DEFAULT_ATS_WEIGHTS))
                    self.assertEqual(weights[key], value)
                    self.assertAlmostEqual(sum(weights.values()), 100)
                    self.assertTrue(all(0 <= weight <= 100 for weight in weights.values()))

    def test_rebalance_distributes_when_other_weights_are_zero(self):
        weights = {key: 0 for key in DEFAULT_ATS_WEIGHTS}
        rebalanced = rebalance_weights("skills", 50, weights)

        self.assertEqual(sum(rebalanced.values()), 100)
        self.assertEqual(rebalanced["skills"], 50)
        self.assertEqual(
            [rebalanced[key] for key in DEFAULT_ATS_WEIGHTS if key != "skills"],
            [10, 10, 10, 10, 10],
        )

    def test_breakdown_retains_skill_matching_but_has_no_completeness_score(self):
        breakdown, match = compute_deterministic_breakdown(
            {
                "skills": ["Python"],
                "experience_years": 2,
                "education_level": "",
                "projects": [],
                "certifications": [],
                "keywords": [],
            },
            {
                "required_skills": ["Python"],
                "preferred_skills": ["SQL"],
                "min_experience": 2,
                "education_requirement": "",
                "keywords": [],
            },
            "",
        )

        self.assertEqual(set(breakdown), set(DEFAULT_ATS_WEIGHTS))
        self.assertIn("skill_match_score", match)
        self.assertEqual(match["matched_skills"], ["Python"])
        self.assertEqual(match["preferred_missing_skills"], ["SQL"])

    def test_scored_candidate_status_remains_usable(self):
        score = compute_ats_score(
            {key: 100 for key in DEFAULT_ATS_WEIGHTS},
            DEFAULT_ATS_WEIGHTS,
        )

        self.assertEqual(score, 100)
        self.assertEqual(classify_candidate_status(5, 5, score, 70, 40, 30), "Shortlisted")


if __name__ == "__main__":
    unittest.main()
