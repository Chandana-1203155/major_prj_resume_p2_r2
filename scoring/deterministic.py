"""Deterministic scoring (reproducible; never asks the LLM for a number)."""

import re


# -------------------------------------------------
# DETERMINISTIC SCORING — skills, experience, education, keywords,
# certifications, projects are all computed here
# in plain Python from the LLM-extracted structured data, NOT by asking the
# LLM to invent a number. This makes scores reproducible (same input always
# gives the same output) and immune to resume text trying to talk the model
# into a higher score.
# -------------------------------------------------

# Each entry names a canonical display-independent key and only aliases that
# are equivalent to that exact skill. Related technologies intentionally stay
# separate (for example SQL/MySQL, Java/JavaScript, Git/GitHub, and
# React/React Native).
SKILL_ALIAS_GROUPS = (
    ("javascript", "javascript", "js"),
    ("typescript", "typescript", "ts"),
    ("postgresql", "postgresql", "postgres"),
    ("node.js", "nodejs", "node", "node.js"),
    ("golang", "golang", "go"),
    ("kubernetes", "kubernetes", "k8s"),
    ("amazon web services", "amazonwebservices", "aws"),
    ("google cloud platform", "googlecloudplatform", "gcp"),
    ("artificial intelligence", "artificialintelligence", "ai"),
    ("machine learning", "machinelearning", "ml"),
    ("deep learning", "deeplearning", "dl"),
    ("natural language processing", "naturallanguageprocessing", "nlp"),
    ("c#", "csharp", "c#"),
    ("objective-c", "objectivec", "objc"),
    ("continuous integration and continuous deployment",
     "continuousintegrationandcontinuousdeployment",
     "continuousintegrationcontinuousdeployment", "cicd"),
    ("user interface", "userinterface", "ui"),
    ("user experience", "userexperience", "ux"),
    ("object oriented programming", "objectorientedprogramming", "oop", "oops",
     "objectorientedprogrammingoop", "objectorientedprogrammingoops"),
    ("object oriented design", "objectorienteddesign", "ood"),
    ("data structures and algorithms", "datastructuresandalgorithms", "datastructuresalgorithms",
     "datastructureandalgorithm", "dsa"),
    ("application programming interface", "applicationprogramminginterface", "api"),
    ("rest apis", "rest", "restapi", "restapis", "restful", "restfulapi", "restfulapis"),
    ("structured query language", "structuredquerylanguage", "sql"),
    ("object relational mapping", "objectrelationalmapping", "orm"),
    ("extract transform load", "extracttransformload", "etl"),
    ("software development lifecycle", "softwaredevelopmentlifecycle", "sdlc"),
    ("quality assurance", "qualityassurance", "qa"),
    ("user acceptance testing", "useracceptancetesting", "uat"),
    ("test driven development", "testdrivendevelopment", "tdd"),
    ("behavior driven development", "behaviordrivendevelopment", "bdd"),
    ("proof of concept", "proofofconcept", "poc"),
    ("software development kit", "softwaredevelopmentkit", "sdk"),
    ("integrated development environment", "integrateddevelopmentenvironment", "ide"),
    ("customer relationship management", "customerrelationshipmanagement", "crm"),
    ("enterprise resource planning", "enterpriseresourceplanning", "erp"),
    ("search engine optimization", "searchengineoptimization", "seo"),
    ("infrastructure as code", "infrastructureascode", "iac"),
    ("identity access management", "identityaccessmanagement", "iam"),
    (".net", "net", "dotnet"),
    ("computer vision", "computervision", "cv"),
    ("react", "react", "reactjs"),
    ("vue", "vue", "vuejs"),
    ("git", "git", "gitversioncontrol"),
    ("github", "github"),
    ("mysql", "mysql"),
    ("python", "python", "python3"),
    ("java", "java", "javase", "javastandardedition"),
    ("c++", "c++", "cpp", "cplusplus"),
    ("dbms", "dbms", "databasemanagementsystem", "databasemanagementsystems"),
)


def _normalize_skill_text(skill):
    """Legacy normalizer: lowercase and drop everything except a-z, 0-9, # and +."""
    return re.sub(r"[^a-z0-9#+]", "", str(skill).lower())


# -------------------------------------------------
# GENERAL (NOT PER-SKILL) NORMALIZATION
# Skill names reach this module in whatever wording the LLM copied from the
# resume or the job description. Instead of listing every spelling, each skill
# is reduced to a set of canonical keys by rules that apply to ALL skills:
#   * "&" / "and" / "of" / "the" are ignored   (Data Structures & Algorithms)
#   * a simple plural is ignored               (Algorithm / Algorithms)
#   * an acronym in brackets is its own key    (Machine Learning (ML))
#   * known aliases collapse to one canonical  (DSA, AWS, OOPs ...)
# Two skills match when their key sets overlap. Anything these rules cannot
# settle is passed to the LLM skill mapper (ai/skill_mapper.py), whose answer
# is verified against the resume before it is trusted.
# -------------------------------------------------
_STOP_TOKENS = frozenset({"and", "of", "the"})
_TOKEN_RE = re.compile(r"[a-z0-9#+]+")
_PAREN_RE = re.compile(r"\(([^()]*)\)")
_PAREN_SPLIT_RE = re.compile(r"[,/;|]")


def _token_key(text):
    """Word-level key: drop stop words, strip a plural 's', join the words."""
    tokens = []
    for token in _TOKEN_RE.findall(str(text).lower()):
        if token in _STOP_TOKENS:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return "".join(tokens)


def _build_canonical_map():
    mapping = {}
    for canonical, *aliases in SKILL_ALIAS_GROUPS:
        for name in (canonical, *aliases):
            for key in (_normalize_skill_text(name), _token_key(name)):
                if key:
                    mapping.setdefault(key, canonical)
    return mapping


_CANONICAL_SKILL_MAP = _build_canonical_map()
_CANONICAL_VALUES = frozenset(_CANONICAL_SKILL_MAP.values())


def skill_keys(skill):
    """Every canonical key a skill string can be known by (empty if blank).

    "Data Structures & Algorithms (DSA)" -> one key for the full name and one
    for the bracketed acronym; both resolve to the same canonical skill.
    """
    if not isinstance(skill, str) or not skill.strip():
        return []
    text = skill.lower()
    parts = [_PAREN_RE.sub(" ", text)]
    for inner in _PAREN_RE.findall(text):
        parts.extend(_PAREN_SPLIT_RE.split(inner))
    keys = []
    for part in parts:
        legacy = _normalize_skill_text(part)
        token = _token_key(part)
        if not legacy and not token:
            continue
        key = (
            _CANONICAL_SKILL_MAP.get(legacy)
            or _CANONICAL_SKILL_MAP.get(token)
            or token
            or legacy
        )
        if key not in keys:
            keys.append(key)
    return keys


def normalize_skill(skill):
    """Return one canonical key for a skill (used for counting/deduplication)."""
    keys = skill_keys(skill)
    if not keys:
        return ""
    for key in keys:
        if key in _CANONICAL_VALUES:
            return key
    return keys[0]


def canonical_skill(skill):
    """Backward-compatible name for the shared skill normalizer."""
    return normalize_skill(skill)


def _clean_skill_list(skills):
    return [s for s in (skills or []) if isinstance(s, str) and s.strip()]


def _evidence_key_set(skills):
    keys = set()
    for skill in _clean_skill_list(skills):
        keys.update(skill_keys(skill))
    return keys


def unresolved_skill_gaps(matched_skills, missing_skills):
    """Filter contradictory/duplicate gaps by canonical skill identity."""
    matched_keys = _evidence_key_set(matched_skills)
    unresolved = []
    seen = set()
    for skill in _clean_skill_list(missing_skills):
        keys = skill_keys(skill)
        primary = normalize_skill(skill)
        if matched_keys.isdisjoint(keys) and primary not in seen:
            unresolved.append(skill)
            seen.add(primary)
    return unresolved


def _candidate_evidence(candidate):
    match = candidate.get("match_result") or {}
    resume_skills = (candidate.get("resume_data") or {}).get("skills", [])
    return list(match.get("matched_skills") or []) + list(resume_skills or [])


def candidate_skill_gaps(candidate):
    """Return required-skill gaps not contradicted by resume evidence."""
    match = candidate.get("match_result") or {}
    return unresolved_skill_gaps(_candidate_evidence(candidate), match.get("missing_skills", []))


def candidate_related_skills(candidate):
    """Required skills where the resume only shows a related (not equivalent) skill."""
    match = candidate.get("match_result") or {}
    return unresolved_skill_gaps(_candidate_evidence(candidate), match.get("related_skills", []))


def candidate_unverified_skills(candidate):
    """Required skills that could not be verified (e.g. the LLM check failed)."""
    match = candidate.get("match_result") or {}
    return unresolved_skill_gaps(_candidate_evidence(candidate), match.get("unverified_skills", []))


def required_skill_total(match):
    """Number of required skills the job asked for (matched + every non-matched state)."""
    match = match or {}
    return sum(
        len(match.get(key) or [])
        for key in ("matched_skills", "missing_skills", "related_skills", "unverified_skills")
    )


def preferred_skill_total(match):
    match = match or {}
    return sum(
        len(match.get(key) or [])
        for key in (
            "preferred_matched_skills",
            "preferred_missing_skills",
            "preferred_related_skills",
            "preferred_unverified_skills",
        )
    )


def _classify_skills(skills, resume_keys, resolutions):
    """Sort job skills into matched / missing / related / unverified.

    Order of evidence: (1) deterministic key overlap with the resume skills,
    (2) the verified LLM resolution, (3) otherwise missing.
    """
    resolutions = resolutions or {}
    llm_matched = resolutions.get("matched") or {}
    llm_related = resolutions.get("related") or {}
    llm_unverified = set(resolutions.get("unverified") or [])
    out = {"matched": [], "missing": [], "related": [], "unverified": [], "evidence": {}}
    for skill in skills:
        if resume_keys.intersection(skill_keys(skill)):
            out["matched"].append(skill)
        elif skill in llm_matched:
            out["matched"].append(skill)
            out["evidence"][skill] = {"verdict": "match", **llm_matched[skill]}
        elif skill in llm_related:
            out["related"].append(skill)
            out["evidence"][skill] = {"verdict": "related", **llm_related[skill]}
        elif skill in llm_unverified:
            out["unverified"].append(skill)
        else:
            out["missing"].append(skill)
    return out


def find_unresolved_skills(resume_skills, required_skills, preferred_skills):
    """Job skills that plain deterministic matching could not match.

    These are the only skills the LLM skill mapper is asked about.
    """
    resume_keys = _evidence_key_set(resume_skills)
    pending = []
    for skill in _clean_skill_list(required_skills) + _clean_skill_list(preferred_skills):
        if skill not in pending and not resume_keys.intersection(skill_keys(skill)):
            pending.append(skill)
    return pending


def score_skills(resume_skills, required_skills, preferred_skills, resolutions=None):
    """Alias-aware matching. Required skills carry full credit, preferred
    skills carry partial credit. No substring/fuzzy matching, so keyword
    stuffing cannot inflate a match, and related-but-different skills
    (Java vs JavaScript, React vs React Native) never match.

    `resolutions` (optional) is the VERIFIED output of the LLM skill mapper for
    skills plain matching could not settle:
        {"matched": {job_skill: {"resume_skill", "evidence"}},
         "related": {job_skill: {...}}, "unverified": [job_skill, ...]}
    Only "matched" earns credit. "related" (adjacent skill) and "unverified"
    (the check could not be completed) earn none, but are reported separately
    instead of being labelled "missing". The score stays deterministic: the
    LLM only resolves wording, and code decides what counts.
    """
    required_skills = _clean_skill_list(required_skills)
    preferred_skills = _clean_skill_list(preferred_skills)
    resume_keys = _evidence_key_set(resume_skills)

    req = _classify_skills(required_skills, resume_keys, resolutions)
    pref = _classify_skills(preferred_skills, resume_keys, resolutions)

    if required_skills:
        required_score = 100.0 * len(req["matched"]) / len(required_skills)
    else:
        required_score = 100.0  # nothing explicitly required — don't penalize
    if preferred_skills:
        preferred_score = 100.0 * len(pref["matched"]) / len(preferred_skills)
        # required skills dominate; preferred skills nudge the score
        skill_score = round(0.85 * required_score + 0.15 * preferred_score, 1)
    else:
        skill_score = round(required_score, 1)

    evidence = dict(pref["evidence"])
    evidence.update(req["evidence"])
    return {
        "skill_score": max(0.0, min(100.0, skill_score)),
        "matched_skills": req["matched"],
        "missing_skills": unresolved_skill_gaps(req["matched"], req["missing"]),
        "related_skills": req["related"],
        "unverified_skills": req["unverified"],
        "preferred_matched_skills": pref["matched"],
        "preferred_missing_skills": unresolved_skill_gaps(pref["matched"], pref["missing"]),
        "preferred_related_skills": pref["related"],
        "preferred_unverified_skills": pref["unverified"],
        "skill_match_evidence": evidence,
    }


def score_experience(candidate_years, required_years):
    if required_years <= 0:
        return 100.0  # JD stated no minimum — full credit, nothing to fall short of
    if candidate_years <= 0:
        return 0.0
    if candidate_years >= required_years:
        return 100.0
    return round(min(100.0, 100.0 * candidate_years / required_years), 1)


_EDUCATION_LEVELS = {"high school": 0, "other": 0, "bachelor": 1, "master": 2, "doctorate": 3}


def score_education(candidate_level, requirement_text):
    candidate_rank = _EDUCATION_LEVELS.get((candidate_level or "").strip().lower(), 0)
    req_text = (requirement_text or "").lower()
    required_rank = None
    for name, rank in [("doctorate", 3), ("phd", 3), ("master", 2), ("bachelor", 1), ("high school", 0)]:
        if name in req_text:
            required_rank = rank
            break
    if required_rank is None:
        # JD doesn't specify a clear education requirement — don't penalize
        return 100.0 if candidate_level and candidate_level.lower() != "not specified" else 60.0
    if candidate_rank >= required_rank:
        return 100.0
    gap = required_rank - candidate_rank
    return max(0.0, 100.0 - gap * 35.0)


def score_keywords(resume_keywords, resume_skills, jd_keywords):
    if not jd_keywords:
        return 100.0
    pool = {_normalize_skill_text(k) for k in (resume_keywords + resume_skills) if k.strip()}
    hits = sum(1 for k in jd_keywords if _normalize_skill_text(k) in pool)
    return round(100.0 * hits / len(jd_keywords), 1)


def score_certifications(resume_certifications, jd_keywords, jd_required_skills):
    """No JD field currently captures 'required certifications' specifically,
    so this is a best-effort, clearly-documented heuristic rather than a
    precise requirement match: certifications that textually relate to the
    JD's keywords/skills count fully; unrelated certifications still count,
    at a reduced rate, as general evidence of professional development.
    This is a known limitation — see project README / audit notes."""
    if not resume_certifications:
        return 0.0
    relevant_terms = {_normalize_skill_text(k) for k in (jd_keywords + jd_required_skills)}
    relevant = 0
    for cert in resume_certifications:
        cert_norm = _normalize_skill_text(cert)
        if any(term and term in cert_norm for term in relevant_terms):
            relevant += 1
    other = len(resume_certifications) - relevant
    score = relevant * 30 + other * 10
    return float(max(0, min(100, score)))


def score_projects(resume_projects, jd_keywords, jd_required_skills):
    if not resume_projects:
        return 0.0
    relevant_terms = {_normalize_skill_text(k) for k in (jd_keywords + jd_required_skills) if k.strip()}
    relevant = 0
    for proj in resume_projects:
        proj_norm = _normalize_skill_text(proj)
        if any(term and term in proj_norm for term in relevant_terms):
            relevant += 1
    base = min(100.0, len(resume_projects) * 15.0)  # having projects at all is worth something
    relevance_bonus = min(40.0, relevant * 20.0)
    return round(min(100.0, base * 0.6 + relevance_bonus), 1)


def compute_deterministic_breakdown(resume_data, jd_data, resume_text, skill_resolutions=None):
    """Runs all deterministic component scores and returns an ATSBreakdown-
    shaped dict plus the raw match details (matched/missing skills etc.).

    skill_resolutions: optional verified output of ai.skill_mapper (see
    score_skills). Omit it for purely string-based matching."""
    skill_result = score_skills(
        resume_data.get("skills", []),
        jd_data.get("required_skills", []),
        jd_data.get("preferred_skills", []),
        resolutions=skill_resolutions,
    )
    experience_score = score_experience(
        resume_data.get("experience_years", 0.0),
        jd_data.get("min_experience", 0.0),
    )
    education_score = score_education(
        resume_data.get("education_level", ""),
        jd_data.get("education_requirement", ""),
    )
    keyword_score = score_keywords(
        resume_data.get("keywords", []),
        resume_data.get("skills", []),
        jd_data.get("keywords", []),
    )
    cert_score = score_certifications(
        resume_data.get("certifications", []),
        jd_data.get("keywords", []),
        jd_data.get("required_skills", []),
    )
    project_score = score_projects(
        resume_data.get("projects", []),
        jd_data.get("keywords", []),
        jd_data.get("required_skills", []),
    )
    breakdown = {
        "skills": skill_result["skill_score"],
        "experience": experience_score,
        "education": education_score,
        "projects": project_score,
        "certifications": cert_score,
        "keywords": keyword_score,
    }
    match_result = {
        "skill_match_score": skill_result["skill_score"],
        "experience_match_score": experience_score,
        "matched_skills": skill_result["matched_skills"],
        "missing_skills": skill_result["missing_skills"],
        # Previously computed by score_skills() but discarded here — now kept
        # so downstream views (Quick View, Why This Score?) can show
        # required vs. preferred skill match separately instead of only
        # ever seeing the required-skills numbers.
        "preferred_matched_skills": skill_result["preferred_matched_skills"],
        "preferred_missing_skills": skill_result["preferred_missing_skills"],
        # Skills that are neither matched nor genuinely missing: the resume
        # shows only a related skill, or the equivalence check could not be
        # completed. Kept separate so they are never shown as "missing".
        "related_skills": skill_result["related_skills"],
        "unverified_skills": skill_result["unverified_skills"],
        "preferred_related_skills": skill_result["preferred_related_skills"],
        "preferred_unverified_skills": skill_result["preferred_unverified_skills"],
        # job skill -> {verdict, resume_skill, evidence} for LLM-resolved skills
        "skill_match_evidence": skill_result["skill_match_evidence"],
    }
    return breakdown, match_result
