import unittest

from ai import skill_mapper
from ai.skill_mapper import resolve_skills_for_job
from scoring.deterministic import (
    candidate_skill_gaps,
    compute_deterministic_breakdown,
    preferred_skill_total,
    required_skill_total,
    score_skills,
)
from ui.helpers import skill_gap_html


RESUME_TEXT = (
    "Skills: Python, Java, Gen AI, MS Excel, Docker. "
    "Built REST services. Strong communication in team projects. " * 3
)


def _resume(skills):
    return {
        "skills": skills, "keywords": [], "certifications": [], "projects": [],
        "experience_years": 1.0, "education_level": "Bachelor", "education": "B.Tech",
        "name": "A", "email": "a@x.com", "phone": "1",
    }


def _jd(required, preferred=()):
    return {
        "role": "SDE", "required_skills": list(required), "preferred_skills": list(preferred),
        "min_experience": 0.0, "education_requirement": "", "keywords": [],
    }


class GeneralNormalizationTests(unittest.TestCase):
    """Wording variants are handled by rules, not by per-skill entries."""

    def assert_match(self, resume_skill, jd_skill):
        r = score_skills([resume_skill], [jd_skill], [])
        self.assertEqual(r["matched_skills"], [jd_skill], (resume_skill, jd_skill))
        self.assertEqual(r["missing_skills"], [])

    def assert_not_match(self, resume_skill, jd_skill):
        r = score_skills([resume_skill], [jd_skill], [])
        self.assertEqual(r["matched_skills"], [], (resume_skill, jd_skill))

    def test_and_ampersand_plural_and_bracket_acronym_variants(self):
        jd = "Data Structure and Algorithm"
        for resume_skill in (
            "DSA", "Data Structures & Algorithms", "Data Structure and Algorithms",
            "Data Structures and Algorithm", "Data Structure & Algorithm",
            "Data Structures & Algorithms (DSA)", "Data Structures and Algorithms (DSA)",
        ):
            with self.subTest(resume_skill=resume_skill):
                self.assert_match(resume_skill, jd)

    def test_full_name_with_acronym_in_brackets_works_in_both_directions(self):
        for a, b in (
            ("Amazon Web Services (AWS)", "AWS"), ("AWS", "Amazon Web Services (AWS)"),
            ("Machine Learning (ML)", "ML"), ("ML", "Machine Learning (ML)"),
        ):
            with self.subTest(a=a, b=b):
                self.assert_match(a, b)

    def test_unknown_skills_also_get_general_rules(self):
        self.assert_match("Unit Tests", "Unit Test")
        self.assert_match("Design of Experiments", "Design Experiments")
        self.assert_match("Cloud (Terraform)", "Terraform")

    def test_distinct_skills_still_do_not_match(self):
        for r, j in (
            ("Java", "JavaScript"), ("JavaScript", "Java"), ("React", "React Native"),
            ("MySQL", "SQL"), ("Git", "GitHub"), ("C", "C++"), ("C++", "C#"),
            ("Machine Learning", "Deep Learning"), ("Docker", "Kubernetes"),
        ):
            with self.subTest(resume=r, jd=j):
                self.assert_not_match(r, j)


class VerifiedResolutionTests(unittest.TestCase):
    def _run(self, resume_skills, required, llm, preferred=()):
        resume = _resume(resume_skills)
        jd = _jd(required, preferred)
        resolutions = resolve_skills_for_job(resume, jd, RESUME_TEXT, llm_call=llm,
                                             model_tag=str(id(llm)))
        breakdown, match = compute_deterministic_breakdown(
            resume, jd, RESUME_TEXT, skill_resolutions=resolutions)
        return resolutions, breakdown, match

    def test_llm_not_called_when_deterministic_matching_settles_everything(self):
        def llm(prompt):
            raise AssertionError("LLM must not be called")
        res, _, match = self._run(["DSA", "Python"], ["Data Structure and Algorithm", "Python"], llm)
        self.assertEqual(match["missing_skills"], [])
        self.assertEqual(res["unverified"], [])

    def test_only_leftover_skills_are_sent_and_verified_matches_get_credit(self):
        seen = {}

        def llm(prompt):
            seen["prompt"] = prompt
            return [
                {"jd_skill": "Generative AI", "verdict": "match",
                 "resume_skill": "Gen AI", "evidence": "Gen AI"},
                {"jd_skill": "Microsoft Excel", "verdict": "match",
                 "resume_skill": "MS Excel", "evidence": "MS Excel"},
                {"jd_skill": "Kubernetes", "verdict": "none", "resume_skill": "", "evidence": ""},
            ]

        _, breakdown, match = self._run(
            ["Python", "Gen AI", "MS Excel", "Docker"],
            ["Python", "Generative AI", "Microsoft Excel", "Kubernetes"], llm)
        self.assertNotIn("- Python\n\nJob", seen["prompt"])  # already matched, not re-asked
        self.assertEqual(match["matched_skills"], ["Python", "Generative AI", "Microsoft Excel"])
        self.assertEqual(match["missing_skills"], ["Kubernetes"])
        self.assertEqual(breakdown["skills"], 75.0)
        self.assertEqual(match["skill_match_evidence"]["Generative AI"]["resume_skill"], "Gen AI")

    def test_hallucinated_match_is_not_trusted(self):
        def llm(prompt):
            return [{"jd_skill": "Kubernetes", "verdict": "match",
                     "resume_skill": "Kubernetes Expert", "evidence": "led k8s migrations"}]
        res, breakdown, match = self._run(["Python", "Docker"], ["Kubernetes"], llm)
        self.assertEqual(match["matched_skills"], [])
        self.assertEqual(match["unverified_skills"], ["Kubernetes"])
        self.assertEqual(match["missing_skills"], [])
        self.assertEqual(breakdown["skills"], 0.0)

    def test_match_can_be_verified_from_resume_text_when_extraction_missed_it(self):
        def llm(prompt):
            return [{"jd_skill": "Team Communication", "verdict": "match",
                     "resume_skill": "communication", "evidence": "Strong communication in team projects"}]
        _, _, match = self._run(["Python"], ["Team Communication"], llm)
        self.assertEqual(match["matched_skills"], ["Team Communication"])

    def test_related_skill_is_reported_separately_and_earns_no_credit(self):
        def llm(prompt):
            return [{"jd_skill": "JavaScript", "verdict": "related",
                     "resume_skill": "Java", "evidence": "Java"}]
        _, breakdown, match = self._run(["Java"], ["JavaScript"], llm)
        self.assertEqual(match["related_skills"], ["JavaScript"])
        self.assertEqual(match["missing_skills"], [])
        self.assertEqual(match["matched_skills"], [])
        self.assertEqual(breakdown["skills"], 0.0)
        self.assertEqual(required_skill_total(match), 1)

    def test_llm_failure_marks_skills_unverified_not_missing_and_is_not_cached(self):
        calls = []

        def failing(prompt):
            calls.append(1)
            raise RuntimeError("503 service unavailable")

        _, _, match = self._run(["Python"], ["Generative AI"], failing)
        self.assertEqual(match["unverified_skills"], ["Generative AI"])
        self.assertEqual(match["missing_skills"], [])

        resolutions = resolve_skills_for_job(_resume(["Python"]), _jd(["Generative AI"]),
                                             RESUME_TEXT, llm_call=failing,
                                             model_tag=str(id(failing)))
        self.assertEqual(resolutions["unverified"], ["Generative AI"])
        self.assertEqual(len(calls), 2)  # failure was retried, not cached

    def test_skills_the_llm_forgot_are_unverified(self):
        def llm(prompt):
            return []
        _, _, match = self._run(["Python"], ["Generative AI"], llm)
        self.assertEqual(match["unverified_skills"], ["Generative AI"])

    def test_result_is_cached_per_resume_and_job(self):
        calls = []

        def llm(prompt):
            calls.append(1)
            return [{"jd_skill": "Generative AI", "verdict": "match",
                     "resume_skill": "Gen AI", "evidence": "Gen AI"}]

        for _ in range(3):
            self._run_cached(llm)
        self.assertEqual(len(calls), 1)

    def _run_cached(self, llm):
        return resolve_skills_for_job(_resume(["Gen AI"]), _jd(["Generative AI"]), RESUME_TEXT,
                                      llm_call=llm, model_tag="cache-test")

    def test_preferred_skills_are_resolved_too(self):
        def llm(prompt):
            return [{"jd_skill": "Microsoft Excel", "verdict": "match",
                     "resume_skill": "MS Excel", "evidence": "MS Excel"}]
        _, _, match = self._run(["MS Excel"], [], llm, preferred=["Microsoft Excel"])
        self.assertEqual(match["preferred_matched_skills"], ["Microsoft Excel"])
        self.assertEqual(preferred_skill_total(match), 1)


class DisplayTests(unittest.TestCase):
    def test_missing_skill_cell_excludes_related_and_unverified_details(self):
        candidate = {
            "resume_data": {"skills": ["Python"]},
            "match_result": {
                "matched_skills": ["Python"],
                "missing_skills": ["A1", "B2", "C3", "D4", "E5"],
                "related_skills": ["JavaScript"],
                "unverified_skills": ["Gen AI"],
            },
        }
        cell = skill_gap_html(candidate, limit=4)
        self.assertIn("A1, B2, C3, D4", cell)
        self.assertNotIn("E5", cell)
        self.assertIn("(+1 more)", cell)
        self.assertNotIn("JavaScript", cell)
        self.assertNotIn("Gen AI", cell)

    def test_old_candidate_records_without_new_fields_still_render(self):
        candidate = {
            "resume_data": {"skills": ["Data Structures & Algorithms (DSA)"]},
            "match_result": {"matched_skills": [], "missing_skills": ["Data Structure and Algorithm", "Docker"]},
        }
        self.assertEqual(candidate_skill_gaps(candidate), ["Docker"])
        self.assertEqual(skill_gap_html(candidate, limit=4), "Docker")
        self.assertEqual(skill_gap_html({"resume_data": {}, "match_result": {}}, limit=4), "None")


if __name__ == "__main__":
    unittest.main()
