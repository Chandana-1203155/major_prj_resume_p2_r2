import unittest

from scoring.deterministic import (
    candidate_skill_gaps,
    normalize_skill,
    score_skills,
)


class SkillNormalizationTests(unittest.TestCase):
    def assert_matches(self, resume_skill, required_skill):
        result = score_skills([resume_skill], [required_skill], [])
        self.assertEqual(result["matched_skills"], [required_skill])
        self.assertEqual(result["missing_skills"], [])

    def assert_not_matches(self, resume_skill, required_skill):
        result = score_skills([resume_skill], [required_skill], [])
        self.assertEqual(result["matched_skills"], [])
        self.assertEqual(result["missing_skills"], [required_skill])

    def test_object_oriented_programming_aliases_and_punctuation(self):
        for resume_skill in ("OOP", "OOPS", "Object Oriented Programming"):
            with self.subTest(resume_skill=resume_skill):
                self.assert_matches(resume_skill, "Object-Oriented Programming (OOP)")

        values = (
            normalize_skill("OOP"),
            normalize_skill("OOPS"),
            normalize_skill("Object-Oriented Programming (OOP)"),
        )
        self.assertEqual(len(set(values)), 1)
        self.assertEqual(values[0], "object oriented programming")

    def test_common_controlled_aliases(self):
        examples = (
            ("DSA", "Data Structures and Algorithms"),
            ("ML", "Machine Learning"),
            ("RESTful APIs", "REST APIs"),
            ("React.js", "React"),
            ("NodeJS", "Node.js"),
            ("DBMS", "Database Management Systems"),
            ("AI", "Artificial Intelligence"),
            ("JS", "JavaScript"),
            ("TS", "TypeScript"),
            ("CV", "Computer Vision"),
            ("CI/CD", "Continuous Integration and Continuous Deployment"),
            ("Node JS", "Node.js"),
            ("VueJS", "Vue"),
            ("Git Version Control", "Git"),
            ("Git Hub", "GitHub"),
            ("My SQL", "MySQL"),
            ("Python3", "Python"),
            ("Java Standard Edition", "Java"),
            ("CPP", "C++"),
            ("C Sharp", "C#"),
        )
        for resume_skill, required_skill in examples:
            with self.subTest(resume_skill=resume_skill, required_skill=required_skill):
                self.assert_matches(resume_skill, required_skill)

    def test_aliases_are_used_for_preferred_skills(self):
        result = score_skills(["OOPS"], [], ["Object-Oriented Programming (OOP)"])
        self.assertEqual(result["preferred_matched_skills"], ["Object-Oriented Programming (OOP)"])
        self.assertEqual(result["preferred_missing_skills"], [])

    def test_related_but_distinct_skills_do_not_match(self):
        for resume_skill, required_skill in (
            ("JavaScript", "Java"),
            ("Java", "JavaScript"),
            ("MySQL", "SQL"),
            ("MongoDB", "SQL"),
            ("GitHub", "Git"),
            ("Git", "GitHub"),
            ("React", "React Native"),
            ("Node.js", "JavaScript"),
            ("AWS", "Cloud Computing"),
            ("Docker", "Kubernetes"),
            ("Machine Learning", "Deep Learning"),
            ("Artificial Intelligence", "Machine Learning"),
        ):
            with self.subTest(resume_skill=resume_skill, required_skill=required_skill):
                self.assert_not_matches(resume_skill, required_skill)

    def test_matched_and_missing_lists_cannot_contain_same_canonical_skill(self):
        result = score_skills(
            ["OOPS"],
            ["Object-Oriented Programming (OOP)", "Object Oriented Programming"],
            [],
        )
        self.assertEqual(
            result["matched_skills"],
            ["Object-Oriented Programming (OOP)", "Object Oriented Programming"],
        )
        self.assertEqual(result["missing_skills"], [])

    def test_existing_candidate_gap_is_suppressed_when_resume_has_alias(self):
        candidate = {
            "match_result": {
                "matched_skills": [],
                "missing_skills": ["Object-Oriented Programming (OOP)"],
            },
            "resume_data": {"skills": ["OOPS"]},
        }
        self.assertEqual(candidate_skill_gaps(candidate), [])


if __name__ == "__main__":
    unittest.main()
