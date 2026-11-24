"""LLM-assisted skill equivalence, verified by code before it is trusted.

WHY THIS EXISTS
Resume and job-description skills are extracted by the LLM in whatever wording
the source documents use ("DSA" / "Data Structure and Algorithm", "Gen AI" /
"Generative AI", "MS Excel" / "Microsoft Excel" ...). Plain string matching can
never cover every wording, so wrongly-"missing" skills kept appearing.

HOW IT WORKS (general - there are no per-skill rules here)
1. scoring.deterministic matches everything it can by canonical keys.
2. Only the job skills left over are sent here, in ONE LLM call per
   resume/job pair, together with the candidate's skill list and resume text.
3. For each job skill the LLM answers: match / related / none, plus the
   resume skill and a short quote as evidence.
4. CODE verifies every answer: a "match" must point at a skill that really is
   in the extracted resume skills (or an evidence quote that really appears in
   the resume text). Anything the LLM claims that cannot be verified is never
   counted as a match.
5. If the call fails, the leftover skills are reported as "unverified" - they
   are NOT silently turned into "missing".

The LLM only resolves wording. Which skills count towards the score is still
decided by plain Python in scoring/deterministic.py, so scoring stays
reproducible. Results are cached per (resume skills, resume text, job skills,
model, version).
"""

import hashlib
import re
import threading

from ai.security import wrap_untrusted
from scoring.deterministic import find_unresolved_skills

_MAX_PROMPT_RESUME_CHARS = 12000
_cache = {}
_cache_lock = threading.Lock()


def _ws(text):
    """Lower-case and collapse whitespace so quotes compare reliably."""
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _empty_resolutions():
    return {"matched": {}, "related": {}, "unverified": []}


def build_skill_mapping_prompt(resume_skills, resume_text, jd_skills):
    skills_block = "\n".join(f"- {s}" for s in resume_skills) or "- (none listed)"
    jd_block = "\n".join(f"- {s}" for s in jd_skills)
    return f"""You are checking whether a candidate's resume shows the skills a job asks for.

For EACH job skill listed below, return one mapping with a verdict:
- "match": the resume shows the SAME skill under a different name. Examples of
  the same skill: an abbreviation or acronym and its full name, the full
  product name and its short name, singular/plural or spelling/punctuation
  variants, or a trade name with or without a generic word ("Microsoft Excel"
  and "MS Excel"). Also use "match" when the resume text clearly states the
  skill even though it is missing from the extracted skills list.
- "related": the resume shows only a NARROWER, BROADER or ADJACENT skill that
  is not the same thing (for example a framework instead of its language, or a
  neighbouring technology). Do not use "match" for these.
- "none": no evidence of the skill or anything close to it.

Rules:
- Be strict: if you are not sure the skill is the same, use "related" or "none".
- resume_skill: copy ONE entry exactly from the extracted skills list below.
  Only if the skill appears solely in the resume text, copy its exact wording
  from the text. Empty for "none".
- evidence: a short exact quote (at most 12 words) copied from the resume text
  that shows the skill. Empty for "none".
- jd_skill: copy the job skill exactly as written below.
- Return exactly one mapping for every job skill, in the same order.

Skills extracted from the resume:
{skills_block}

{wrap_untrusted("resume", (resume_text or "")[:_MAX_PROMPT_RESUME_CHARS])}

Job skills to check:
{jd_block}

Return valid JSON matching the schema.
"""


def _call_llm(prompt):
    """Real LLM call. Imported lazily so this module (and its tests) load
    without the LLM client being installed or configured."""
    from ai.llm import get_llm, safe_llm_invoke
    from models.schemas import SkillMappingResult

    structured_llm = get_llm().with_structured_output(SkillMappingResult)
    result = safe_llm_invoke(structured_llm, prompt)
    return [m.model_dump() for m in result.mappings]


def _verify_claim(resume_skill, evidence, resume_skill_norms, resume_text_norm):
    """True only if the LLM's pointer into the resume can be found there."""
    skill_norm = _ws(resume_skill)
    if not skill_norm:
        return False
    if skill_norm in resume_skill_norms:
        return True
    evidence_norm = _ws(evidence)
    return bool(
        evidence_norm
        and evidence_norm in resume_text_norm
        and skill_norm in resume_text_norm
    )


def verify_mappings(raw_mappings, pending, resume_skills, resume_text):
    """Turn raw LLM mappings into verified resolutions.

    Unknown job skills in the output are ignored; job skills the LLM did not
    answer, or whose "match" claim cannot be verified, become "unverified"
    (never "missing").
    """
    resume_skill_norms = {_ws(s) for s in resume_skills}
    resume_text_norm = _ws(resume_text)
    pending_by_norm = {_ws(s): s for s in pending}

    resolutions = _empty_resolutions()
    answered = set()
    for item in raw_mappings or []:
        if not isinstance(item, dict):
            continue
        jd_skill = pending_by_norm.get(_ws(item.get("jd_skill")))
        if jd_skill is None or jd_skill in answered:
            continue
        verdict = _ws(item.get("verdict"))
        resume_skill = str(item.get("resume_skill") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        info = {"resume_skill": resume_skill, "evidence": evidence}

        if verdict == "match":
            answered.add(jd_skill)
            if _verify_claim(resume_skill, evidence, resume_skill_norms, resume_text_norm):
                resolutions["matched"][jd_skill] = info
            else:
                resolutions["unverified"].append(jd_skill)
        elif verdict == "related":
            answered.add(jd_skill)
            if _verify_claim(resume_skill, evidence, resume_skill_norms, resume_text_norm):
                resolutions["related"][jd_skill] = info
            # an unverifiable "related" claim is just treated as no evidence
        elif verdict == "none":
            answered.add(jd_skill)  # genuinely missing: no entry needed

    for skill in pending:
        if skill not in answered:
            resolutions["unverified"].append(skill)
    return resolutions


def resolve_skills_for_job(resume_data, jd_data, resume_text, llm_call=None, model_tag=""):
    """Return verified skill resolutions for one resume against one job.

    Never raises: any failure marks the leftover skills "unverified".
    `llm_call(prompt) -> list[dict]` can be injected (used by tests).
    """
    resume_skills = [
        s for s in (resume_data.get("skills") or []) if isinstance(s, str) and s.strip()
    ]
    pending = find_unresolved_skills(
        resume_skills,
        jd_data.get("required_skills") or [],
        jd_data.get("preferred_skills") or [],
    )
    if not pending:
        return _empty_resolutions()

    cache_key = hashlib.sha256(
        "\n".join(
            [
                "|".join(sorted(_ws(s) for s in resume_skills)),
                "|".join(_ws(s) for s in pending),
                hashlib.sha256((resume_text or "").encode("utf-8")).hexdigest(),
                model_tag,
            ]
        ).encode("utf-8")
    ).hexdigest()
    with _cache_lock:
        cached = _cache.get(cache_key)
    if cached is not None:
        return {
            "matched": dict(cached["matched"]),
            "related": dict(cached["related"]),
            "unverified": list(cached["unverified"]),
        }

    try:
        prompt = build_skill_mapping_prompt(resume_skills, resume_text, pending)
        raw = (llm_call or _call_llm)(prompt)
        resolutions = verify_mappings(raw, pending, resume_skills, resume_text)
    except Exception:
        # Do not cache failures, and do not pretend the skills are missing.
        return {"matched": {}, "related": {}, "unverified": list(pending)}

    with _cache_lock:
        _cache[cache_key] = resolutions
    return resolutions
