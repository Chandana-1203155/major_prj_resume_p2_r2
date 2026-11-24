"""Streamlit session-state initialisation (in-memory only; nothing is persisted)."""

import hashlib

import streamlit as st

from config import DEFAULT_ATS_WEIGHTS


# -------------------------------------------------
# IN-MEMORY HELPERS
# All application data lives only in st.session_state for the current
# Streamlit session. Nothing is written to disk; a restart/new session
# starts empty.
# -------------------------------------------------
def assign_job_id(job):
    """Return a copy of the job dict with a stable in-memory id."""
    job = dict(job)
    job["id"] = job.get("id") or hashlib.md5(job.get("text", "").encode()).hexdigest()[:12]
    return job


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
def init_session():
    defaults = {
        "candidates": [],
        "jobs": [],
        "selected_candidates": [],
        "weights": dict(DEFAULT_ATS_WEIGHTS),
        "min_skill_match": 5,
        "shortlist_score_threshold": 70,
        "hold_score_threshold": 40,
        "reject_score_threshold": 30,
        "processing_stats": {"processed": 0, "skipped": 0, "failed": 0},
        "active_section": "Dashboard",
        "jd_upload_key": 0,
        "resume_upload_key": 0,
        "jd_sources": [],
        "resume_files": [],
        "analysis_complete": False,
        "analysis_history": [],
        "analysis_errors": [],
        "decision_history": [],
        "resume_cache": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state.pop("max_resumes_limit", None)
    st.session_state.pop("max_resumes_limit_input", None)

    weights = st.session_state.weights
    if (
        not isinstance(weights, dict)
        or set(weights) != set(DEFAULT_ATS_WEIGHTS)
        or abs(sum(weights.values()) - 100) > 0.05
    ):
        st.session_state.weights = dict(DEFAULT_ATS_WEIGHTS)
        for key in DEFAULT_ATS_WEIGHTS:
            st.session_state.pop(f"weight_{key}", None)
