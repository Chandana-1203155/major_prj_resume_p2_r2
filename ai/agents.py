"""LLM agents: structured extraction and explanation only (no LLM node decides a score)."""

from ai.llm import get_llm, safe_llm_invoke
from ai.security import wrap_untrusted
from models.schemas import AIEvaluation, AIRecommendation, JDData, ResumeData
from models.state import HiringState


# -------------------------------------------------
# LLM AGENTS — used ONLY for structured evidence extraction (resume_parser,
# jd_analyzer) and for turning already-computed deterministic results into
# human-readable explanations ( ai_evaluation_agent,
# ai_recommendation_agent). No LLM node decides a numeric score — that is
# handled by the deterministic functions further down, so results are
# reproducible and cannot be swayed by resume content trying to talk the
# model into a higher score.
#
# IMPORTANT: these functions RAISE on failure rather than silently returning
# a zero-value default. A caught API/parsing failure must never look
# identical to a genuinely empty/low-quality resume — the caller
# (evaluate_candidate) is responsible for turning a raised exception into a
# visible "evaluation failed" error rather than a fabricated score.
def resume_parser(state: HiringState):
    structured_llm = get_llm().with_structured_output(ResumeData)
    prompt = f"""Extract structured resume data. Only report information that is
explicitly present in the text below — never guess, estimate, or infer
missing values.

IMPORTANT — experience_years (professional work experience ONLY):
- experience_years must count ONLY paid, professional employment: full-time
  jobs, part-time jobs, contract/freelance work, and consulting roles with
  a real employer and job title. Compute it only from explicit
  dates/durations stated for those roles.
- experience_years must NOT include, and must NOT be inflated by:
  * Internships or co-ops (put their duration in internship_experience_years
    instead, never in experience_years)
  * Academic/college/personal/course projects, capstones, or class
    assignments — these are not employment, regardless of how long they
    took or how professional they sound
  * Time spent in education itself (years of a degree program, semesters,
    bootcamps, training programs)
  * Certification validity/study periods (e.g. "6-month certification
    program" is not work experience)
  * Volunteer work, unless the resume explicitly frames it as professional
    employment
- If the resume has NO professional employment section at all (e.g. it
  only shows education, academic projects, internships, and/or
  certifications — typical of a student or recent graduate with no job
  history), experience_years MUST be 0. Do not approximate it from
  internship length, project duration, or years spent studying.
- If experience is stated as a range across multiple employers, sum only
  the professional roles; do not double count overlapping dates.

IMPORTANT — internship_experience_years (kept separate, never merged in):
- Sum the duration of internships/co-ops only, computed the same way
  (explicit dates/durations only). 0 if none are present.

OTHER FIELDS:
- skills must be a list of individual technical/professional skills actually
  named in the text
- education_level: one of High School, Bachelor, Master, Doctorate, Other
- projects: list of project titles or brief descriptions (academic or
  personal projects belong here, not in experience_years)
- certifications: list of certifications
- keywords: important industry keywords and technologies mentioned

{wrap_untrusted("resume", state['resume_text'])}

Return valid JSON matching the schema.
"""
    result = safe_llm_invoke(structured_llm, prompt)
    return {"resume_data": result.model_dump()}


def jd_analyzer(state: HiringState):
    structured_llm = get_llm().with_structured_output(JDData)
    prompt = f"""Extract structured job requirements from the job description below.

IMPORTANT:
- min_experience must be a number
- required_skills: individual skills explicitly required by the employer,
  using clear terms such as required, must-have, essential, or mandatory.
- preferred_skills: individual skills explicitly presented as preferred,
  nice-to-have, a bonus, or advantageous but not mandatory.
- Classify each skill in only one list. If a skill appears in both required
  and preferred wording, use the strongest explicit requirement context and
  do not duplicate it.
- Do not infer that a skill is required or preferred merely because it
  appears in responsibilities, qualifications without requirement context,
  or general description. Put those terms in keywords instead.
- Keep required_skills and preferred_skills as separate lists even when a
  skill's wording is an alias or abbreviation; do not merge distinct skills.
- keywords: important technologies, tools, or domain keywords that are not
  otherwise explicitly classified as required or preferred
- responsibilities: list of key responsibilities

{wrap_untrusted("job_description", state['jd_text'])}

Return valid JSON matching the schema.
"""
    result = safe_llm_invoke(structured_llm, prompt)
    return {"jd_data": result.model_dump()}



def ai_evaluation_agent(state: HiringState):
    structured_llm = get_llm().with_structured_output(AIEvaluation)
    prompt = f"""Write a qualitative evaluation of this candidate for the role,
grounded strictly in the extracted data and deterministic scores below. Do
NOT invent skills, experience, or facts not present in the data. Do not
contradict the deterministic matched/missing skill lists. Skills under
related_skills are only partially covered (the resume shows an adjacent skill)
and skills under unverified_skills could not be checked - never describe either
of those as simply "missing".

Resume data: {state['resume_data']}
Job data: {state['jd_data']}
Deterministic match result: {state['match_result']}
Deterministic score breakdown: {state['ats_breakdown']}

Generate:
- summary: professional 3-4 sentence summary
- matched_skills: copy exactly from the deterministic matched_skills list above
- missing_skills: copy exactly from the deterministic missing_skills list above
- strengths: 3-5 candidate strengths, based only on the data given
- weaknesses: 3-5 candidate weaknesses, based only on the data given
- skill_gap_analysis: paragraph explaining the skill gaps above and how to address them
- projects_analysis: 1-2 sentences on project relevance
- certifications_analysis: 1-2 sentences on certification relevance

Return valid JSON matching the schema.
"""
    result = safe_llm_invoke(structured_llm, prompt)
    return {"ai_evaluation": result.model_dump()}


def ai_recommendation_agent(state: HiringState):
    structured_llm = get_llm().with_structured_output(AIRecommendation)
    prompt = f"""Based ONLY on the deterministic score breakdown and match data
below, suggest a next action for this candidate. This is advisory input for a
human recruiter, not a final decision.

Resume data: {state['resume_data']}
Job data: {state['jd_data']}
Deterministic match result: {state['match_result']}
Deterministic score breakdown: {state['ats_breakdown']}
Deterministic overall score (0-100): {state.get('deterministic_overall_score', 'N/A')}

Decision must be one of: Shortlist, On Hold, Reject — pick the one most
consistent with the scores above.
Confidence: a 0-100 number reflecting how much of the job's required
information (skills, experience, education) was clearly and completely
present in the resume for you to judge confidently — NOT a claim about the
candidate's probability of being hired.
Reason: 3-5 sentences explaining the decision using specific factors from
the score breakdown above.

Return valid JSON matching the schema.
"""
    result = safe_llm_invoke(structured_llm, prompt)
    return {"ai_recommendation": result.model_dump()}
