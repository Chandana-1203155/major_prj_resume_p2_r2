"""Candidate evaluation pipeline (cache, extraction, scoring, AI explanation)."""

import hashlib
from datetime import datetime

import streamlit as st

from ai.execution_tracking import run_with_node_tracking
from ai.graphs import explanation_graph, resume_extraction_graph
from ai.security import detect_prompt_injection
from ai.skill_mapper import resolve_skills_for_job
from config import GEMINI_MODEL, SCORING_LOGIC_VERSION
from parsing.ocr import OCR_AVAILABLE
from scoring.ats import classify_candidate_status, compute_ats_score
from scoring.deterministic import compute_deterministic_breakdown


# -------------------------------------------------
# PIPELINE
# -------------------------------------------------
def compute_cache_key(resume_text, jobs, model_name, version):
    """
    Cache key covers everything that can change the RESULT of the LLM
    extraction / deterministic scoring: the resume content, the full set of
    job descriptions being evaluated against (not just their names — two
    JDs can share a name with different text), the model in use, and a
    scoring-logic version string. Weights are deliberately excluded: they
    only affect the final weighted sum (compute_ats_score), which is cheap
    to redo from the cached breakdown on every weight change, so adjusting
    weights doesn't require a cache miss / new LLM calls.
    """
    jd_fingerprint = "||".join(sorted(j.get("text", "") for j in jobs))
    raw = f"{resume_text}\n---JOBS---\n{jd_fingerprint}\n---MODEL---\n{model_name}\n---VER---\n{version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def evaluate_candidate(file_entry, jobs, weights, progress_callback=None, thresholds=None,
                        resume_cache=None, existing_candidates=None):
    """
    thresholds: optional dict with keys min_skill_match, shortlist_score_threshold,
    hold_score_threshold, reject_score_threshold.

    resume_cache / existing_candidates: optional explicit snapshots of
    st.session_state.resume_cache and st.session_state.candidates.

    All three of the above exist for the same reason: when this function
    runs inside a background thread (see the parallel-processing block in
    render_evaluation), reading OR writing st.session_state from that
    thread raises "st.session_state has no attribute ..." — Streamlit's
    session state is only reliably accessible on the main script thread.
    The threaded caller MUST pass all of these explicitly (captured in the
    main thread before submitting to the executor) instead of letting this
    function touch st.session_state itself. When called from the main
    thread, omitting them falls back to reading/writing st.session_state
    directly as before. This function never mutates the caller's cache
    dict directly (even when one is passed in) — the caller is responsible
    for storing the returned candidate into st.session_state.resume_cache
    itself, in the main thread, once the call returns.
    """
    cache = resume_cache if resume_cache is not None else st.session_state.resume_cache
    candidate_pool = existing_candidates if existing_candidates is not None else st.session_state.candidates

    if not jobs:
        st.warning("No job descriptions available.")
        return None

    if not file_entry["text"].strip():
        if OCR_AVAILABLE:
            reason = (
                "the file appears to be empty, unreadable, or a scanned image "
                "with no recognizable text even after OCR was attempted."
            )
        else:
            reason = (
                "this may be a scanned/image-only PDF. OCR fallback is not active in "
                "this environment (install pytesseract, pdf2image, and the tesseract-ocr "
                "and poppler-utils system packages to enable it)."
            )
        return {
            "error": f"Resume parsing failed — {reason}"
        }

    # Cache key covers resume text + every job's text + model + scoring version
    cache_key = compute_cache_key(
        file_entry["text"],
        jobs,
        GEMINI_MODEL,
        SCORING_LOGIC_VERSION
    )

    # -------------------------------------------------
    # CACHE HIT — reuse the previously computed candidate result.
    # This branch now owns its own `return`, so it can never fall through
    # into the "cached" variable being referenced when nothing was cached
    # (which used to raise NameError on every first-time / cache-miss run),
    # and it no longer short-circuits the real pipeline below unconditionally.
    # -------------------------------------------------
    if cache_key in cache:
        cached = dict(cache[cache_key])

        cached["ats_score"] = compute_ats_score(
            cached["ats_breakdown"],
            weights
        )

        # Preserve recruiter workflow data from an existing candidate.
        existing = next(
            (
                c for c in candidate_pool
                if c.get("file_name") == file_entry["name"]
            ),
            None
        )

        if existing:
            cached["recruiter_decision"] = existing.get(
                "recruiter_decision",
                "Not Decided"
            )
            cached["recruiter_notes"] = existing.get(
                "recruiter_notes",
                ""
            )
            cached["recruiter_reason"] = existing.get(
                "recruiter_reason",
                ""
            )
            cached["selected_for_comparison"] = existing.get(
                "selected_for_comparison",
                False
            )
        else:
            cached["recruiter_decision"] = "Not Decided"
            cached["recruiter_notes"] = ""
            cached["recruiter_reason"] = ""
            cached["selected_for_comparison"] = False

        if progress_callback:
            progress_callback("✅ Loaded cached analysis.")

        if resume_cache is None:
            # Only touch st.session_state directly when we're on the main
            # thread (i.e. the caller didn't hand us an explicit cache).
            st.session_state.resume_cache[cache_key] = cached
        return cached

    # -------------------------------------------------
    # CACHE MISS — run the real pipeline. This code used to be unreachable
    # dead code because of the unconditional `return cached` above; it now
    # only runs when there is nothing usable in the cache.
    # -------------------------------------------------
    injection_flag = detect_prompt_injection(file_entry["text"])

    # -------------------------------------------------
    # 1) EXTRACT RESUME INFORMATION
    # -------------------------------------------------
    try:
        if progress_callback:
            progress_callback("📄 Extracting resume information...")

        resume_state = run_with_node_tracking(resume_extraction_graph, {
            "resume_text": file_entry["text"],
            "jd_text": "",
            "resume_data": {},
            "jd_data": {},
            "match_result": {},
            "ats_breakdown": {},
            "ai_evaluation": {},
            "ai_recommendation": {}
        }, label=file_entry["name"])

    except Exception as e:
        error_str = str(e).lower()

        if any(
            k in error_str
            for k in [
                "rate",
                "429",
                "timeout",
                "timed out",
                "connection",
                "503",
                "502"
            ]
        ):
            return {
                "error": (
                    f"Evaluation service unavailable "
                    f"(rate limit/timeout) while parsing "
                    f"{file_entry['name']}: {e}"
                )
            }

        return {
            "error": (
                f"Resume parsing failed for "
                f"{file_entry['name']}: {e}"
            )
        }

    resume_data = resume_state["resume_data"]

    # -------------------------------------------------
    # 2) DETERMINISTIC ATS SCORING
    # -------------------------------------------------
    if progress_callback:
        progress_callback("🧮 Calculating Candidate Match score...")

    best_job = None
    best_score = -1.0
    best_breakdown = None
    best_match_result = None

    for job in jobs:
        # Skills plain matching could not settle (different wording of the
        # same skill) are resolved by one verified LLM check per job. It
        # never raises: on failure those skills are reported as "unverified",
        # not "missing".
        skill_resolutions = resolve_skills_for_job(
            resume_data,
            job,
            file_entry["text"],
            model_tag=f"{GEMINI_MODEL}|{SCORING_LOGIC_VERSION}",
        )

        breakdown, match_result = compute_deterministic_breakdown(
            resume_data,
            job,
            file_entry["text"],
            skill_resolutions=skill_resolutions,
        )

        score = compute_ats_score(
            breakdown,
            weights
        )

        if score > best_score:
            best_job = job
            best_score = score
            best_breakdown = breakdown
            best_match_result = match_result

    if best_job is None:
        return None

    if progress_callback:
        progress_callback(
            f"✅ ATS Match Score calculated: {best_score:.1f}%"
        )

    # -------------------------------------------------
    # 3) AI EVALUATION + RECOMMENDATION
    # -------------------------------------------------
    try:
        if progress_callback:
            progress_callback(
                "🤖 Generating AI evaluation and recommendation..."
            )

        explanation_state = run_with_node_tracking(explanation_graph, {
            "resume_text": file_entry["text"],
            "jd_text": best_job.get("text", ""),
            "resume_data": resume_data,
            "jd_data": best_job,
            "match_result": best_match_result,
            "ats_breakdown": best_breakdown,
            "ai_evaluation": {},
            "ai_recommendation": {},
            "deterministic_overall_score": best_score
        }, label=file_entry["name"])

    except Exception as e:
        error_str = str(e).lower()

        if any(
            k in error_str
            for k in [
                "rate",
                "429",
                "timeout",
                "timed out",
                "connection",
                "503",
                "502"
            ]
        ):
            return {
                "error": (
                    f"Evaluation service unavailable "
                    f"(rate limit/timeout) while evaluating "
                    f"{file_entry['name']}: {e}"
                )
            }

        return {
            "error": (
                f"Evaluation failed for "
                f"{file_entry['name']}: {e}"
            )
        }

    if progress_callback:
        progress_callback("✅ AI evaluation completed.")

    # -------------------------------------------------
    # 4) FORCE MATCHED/MISSING SKILLS TO MATCH
    #    DETERMINISTIC RESULT
    # -------------------------------------------------
    explanation_state["ai_evaluation"]["matched_skills"] = (
        best_match_result.get("matched_skills", [])
    )

    explanation_state["ai_evaluation"]["missing_skills"] = (
        best_match_result.get("missing_skills", [])
    )

    # -------------------------------------------------
    # 5) RECRUITMENT DECISION
    # -------------------------------------------------
    matched_count = len(
        best_match_result.get("matched_skills", [])
    )

    # NOTE: dict.get(key, default) evaluates `default` eagerly even when
    # `key` is already present — so we can't write
    # thresholds.get("min_skill_match", st.session_state.get(...)) here,
    # that would touch st.session_state on every call regardless, including
    # from a background worker thread where that's unsafe. Explicit
    # "is it already provided?" checks avoid touching session_state at all
    # when the caller (e.g. the parallel-processing path) already supplied
    # every value.
    thresholds = thresholds or {}
    min_required = thresholds["min_skill_match"] if "min_skill_match" in thresholds \
        else st.session_state.get("min_skill_match", 5)
    shortlist_th = thresholds["shortlist_score_threshold"] if "shortlist_score_threshold" in thresholds \
        else st.session_state.get("shortlist_score_threshold", 70)
    hold_th = thresholds["hold_score_threshold"] if "hold_score_threshold" in thresholds \
        else st.session_state.get("hold_score_threshold", 40)
    reject_th = thresholds["reject_score_threshold"] if "reject_score_threshold" in thresholds \
        else st.session_state.get("reject_score_threshold", 30)

    smart_status = classify_candidate_status(
        matched_count, min_required, best_score, shortlist_th, hold_th, reject_th
    )

    # -------------------------------------------------
    # 6) BUILD CANDIDATE RESULT
    # -------------------------------------------------
    candidate = {
        "name": resume_data.get(
            "name",
            "Unknown"
        ),

        "email": resume_data.get(
            "email",
            ""
        ),

        "phone": resume_data.get(
            "phone",
            ""
        ),

        "resume_data": resume_data,

        "match_result": best_match_result,

        "ats_breakdown": best_breakdown,

        "ai_evaluation": explanation_state[
            "ai_evaluation"
        ],

        "ai_recommendation": explanation_state[
            "ai_recommendation"
        ],

        "jd_data": best_job,

        "file_name": file_entry["name"],

        "file_content": file_entry.get(
            "content",
            b""
        ),

        "file_type": file_entry.get(
            "type",
            "txt"
        ),

        "content_hash": file_entry.get("content_hash", ""),

        "text": file_entry["text"],

        "best_role": best_job.get(
            "role",
            "Unknown"
        ),

        "ats_score": best_score,

        "matched_skill_count": matched_count,

        "min_skill_threshold": min_required,

        "injection_flag": injection_flag,

        "status": smart_status,

        "recruiter_decision": "Not Decided",

        "recruiter_notes": "",

        "recruiter_reason": "",

        "selected_for_comparison": False,

        "evaluated_at": datetime.now().isoformat(),

        "source": "Upload",

        # Stable id derived from the resume's content, not a timestamp, so
        # re-evaluating the same resume (e.g. after a cache clear) upserts
        # the same DB row instead of creating a duplicate candidate record.
        "id": (file_entry.get("content_hash") or hashlib.md5(
            f"{file_entry['name']}_{datetime.now().isoformat()}".encode()
        ).hexdigest())[:12]
    }

    if resume_cache is None:
        # Only touch st.session_state directly when we're on the main
        # thread (i.e. the caller didn't hand us an explicit cache). When
        # called from a worker thread, the caller stores this into
        # st.session_state.resume_cache itself, back on the main thread.
        st.session_state.resume_cache[cache_key] = candidate

    if progress_callback:
        progress_callback("✅ Candidate analysis completed.")

    return candidate
