"""Candidates page."""

import pandas as pd
import streamlit as st

from scoring.deterministic import (
    candidate_related_skills,
    candidate_skill_gaps,
    candidate_unverified_skills,
    preferred_skill_total,
    required_skill_total,
    unresolved_skill_gaps,
)
from services.decisions import set_recruiter_decision
from ui.components import render_why_score_block
from ui.helpers import candidate_matches_search, get_resume_preview_html


def render_candidates():
    st.header("Candidates")
    candidates = st.session_state.candidates
    if not candidates:
        st.info("No candidates yet. Evaluate resumes in the 'Candidate Evaluation' section.")
        return

    # Search and filters
    st.subheader("Search & Filters")
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search by candidate name or keyword", key="search")
    with col2:
        decision_filter = st.multiselect("Recruiter Decision", options=["Not Decided", "Shortlist", "On Hold", "Reject"], default=[], key="decision_filter")

    c1, c2, c3 = st.columns(3)
    with c1:
        min_score = st.number_input("Min ATS Match Score", 0.0, 100.0, 0.0, key="min_score")
    with c2:
        max_score = st.number_input("Max ATS Match Score", 0.0, 100.0, 100.0, key="max_score")
    with c3:
        top_n = st.selectbox("Show Top", options=["All", "Top 5", "Top 10", "Top 20"], index=0, key="top_n")

    filtered = candidates[:]
    if search:
        filtered = [c for c in filtered if candidate_matches_search(c, search)]
    if decision_filter:
        filtered = [c for c in filtered if c["recruiter_decision"] in decision_filter]
    filtered = [c for c in filtered if min_score <= c["ats_score"] <= max_score]
    filtered = sorted(filtered, key=lambda x: x["ats_score"], reverse=True)

    if top_n == "Top 5":
        filtered = filtered[:5]
    elif top_n == "Top 10":
        filtered = filtered[:10]
    elif top_n == "Top 20":
        filtered = filtered[:20]

    st.write(f"Showing {len(filtered)} of {len(candidates)} candidates")

    # Table
    table_data = []
    for c in filtered:
        table_data.append({
            "Name": c["name"],
            "ATS Match Score": f"{c['ats_score']}%",
            "Best Role": c["best_role"],
            "AI Recommendation": c["ai_recommendation"].get("decision", "On Hold"),
            "Recruiter Decision": c["recruiter_decision"],
        })
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Bulk compare selection
    selected_ids = st.multiselect("Select candidates for comparison", options=[c["id"] for c in candidates], key="compare_select")
    for c in st.session_state.candidates:
        c["selected_for_comparison"] = c["id"] in selected_ids

    # Expandable details
    st.subheader("Candidate Details")
    for c in filtered:
        with st.expander(f"{c['name']} — {c['best_role']}"):
            if c.get("injection_flag"):
                st.warning(
                    "⚠️ This resume contains phrasing that resembles an attempt to "
                    "instruct the AI (e.g. \"ignore previous instructions\"). Scoring "
                    "in this app is deterministic and not influenced by such text, "
                    "but flagging it here for recruiter awareness."
                )
            tabs = st.tabs(["Overview", "Why This Score?", "Recruiter Decision", "Resume Preview"])

            with tabs[0]:
                match = c.get("match_result", {})
                required_matched = match.get("matched_skills", [])
                preferred_matched = match.get("preferred_matched_skills", [])
                required_missing = candidate_skill_gaps(c)
                preferred_missing = unresolved_skill_gaps(
                    preferred_matched,
                    match.get("preferred_missing_skills", []),
                )
                recommendation = c.get("ai_recommendation") or {}

                st.metric("ATS Match Score", f"{c['ats_score']:.2f}%")
                st.markdown(
                    f"**Required skills matched:** {len(required_matched)}/"
                    f"{required_skill_total(match)}"
                )
                st.markdown(
                    f"**Preferred skills matched:** {len(preferred_matched)}/"
                    f"{preferred_skill_total(match)}"
                )
                overview_col1, overview_col2 = st.columns(2)
                with overview_col1:
                    st.markdown("**Matched required skills**")
                    st.write(", ".join(required_matched) or "None")
                    st.markdown("**Matched preferred skills**")
                    st.write(", ".join(preferred_matched) or "None")
                with overview_col2:
                    st.markdown("**Missing required skills**")
                    st.write(", ".join(required_missing) or "None")
                    st.markdown("**Missing preferred skills**")
                    st.write(", ".join(preferred_missing) or "None")

                with st.expander("Skill Details", expanded=False):
                    st.caption(
                        "Related skills are not exact matches and do not count "
                        "toward the matched skill totals. Unverified skills are "
                        "not treated as missing."
                    )
                    for label, related, unverified in (
                        (
                            "Required",
                            candidate_related_skills(c),
                            candidate_unverified_skills(c),
                        ),
                        (
                            "Preferred",
                            match.get("preferred_related_skills", []),
                            match.get("preferred_unverified_skills", []),
                        ),
                    ):
                        st.markdown(f"**{label} related skills:**")
                        st.write(", ".join(related) or "None")
                        st.markdown(f"**{label} unverified skills:**")
                        st.write(", ".join(unverified) or "None")

                strengths = c.get("ai_evaluation", {}).get("strengths", [])
                weaknesses = c.get("ai_evaluation", {}).get("weaknesses", [])
                st.markdown(
                    f"**AI Recommendation:** {recommendation.get('decision', 'On Hold')}"
                )
                st.write(recommendation.get("reason") or "No explanation recorded.")
                overview_col1, overview_col2 = st.columns(2)
                with overview_col1:
                    st.markdown("**Strengths**")
                    st.write("\n".join(f"- {item}" for item in strengths) or "None recorded.")
                with overview_col2:
                    st.markdown("**Weaknesses**")
                    st.write("\n".join(f"- {item}" for item in weaknesses) or "None recorded.")
                st.markdown(
                    f"**Recruiter Decision:** {c.get('recruiter_decision', 'Not Decided')}"
                )
                st.markdown("---")
                st.markdown(f"**Email:** {c['resume_data'].get('email', 'N/A')}")
                st.markdown(f"**Phone:** {c['resume_data'].get('phone', 'N/A')}")
                st.markdown(f"**Experience:** {c['resume_data'].get('experience_years', 0)} years (professional employment only)")
                internship_yrs = c['resume_data'].get('internship_experience_years', 0)
                if internship_yrs:
                    st.caption(f"Plus {internship_yrs} year(s) of internship experience — shown separately, not counted toward the Experience score.")
                st.markdown(f"**Education:** {c['resume_data'].get('education', 'N/A')} ({c['resume_data'].get('education_level', '')})")
                st.markdown(f"**Professional Summary:** {c['ai_evaluation'].get('summary', '')}")
                with st.expander("AI Skill Gap Analysis", expanded=False):
                    st.write(
                        c.get("ai_evaluation", {}).get("skill_gap_analysis")
                        or "No skill gap analysis recorded."
                    )
            with tabs[1]:
                with st.expander("ATS score breakdown", expanded=False):
                    render_why_score_block(c)

            with tabs[2]:
                decision_options = ["Not Decided","Shortlist", "On Hold", "Reject"]
                new_decision = st.selectbox("Recruiter Decision", decision_options, index=decision_options.index(c["recruiter_decision"]) if c["recruiter_decision"] in decision_options else 0, key=f"decision_{c['id']}")
                notes = st.text_area("Recruiter Notes", value=c["recruiter_notes"], key=f"notes_{c['id']}")
                reason = st.text_area("Decision Reason", value=c["recruiter_reason"], key=f"reason_{c['id']}")
                if st.button("Save Decision", key=f"save_{c['id']}"):
                    set_recruiter_decision(c, new_decision, via="candidates_save")
                    c["recruiter_notes"] = notes
                    c["recruiter_reason"] = reason
                    st.success("Decision saved.")

                st.markdown("---")
                st.caption(
                    "Remove this candidate's analysis (e.g. to re-run them after a "
                    "scoring/extraction fix, or if the resume was uploaded by mistake). "
                    "The original resume file stays in your uploads — re-run 'Analyze "
                    "Candidates' afterward to get a fresh result."
                )
                if st.button("🗑️ Remove candidate & re-analyze next run", key=f"remove_candidate_{c['id']}"):
                    st.session_state.candidates = [
                        cand for cand in st.session_state.candidates if cand["id"] != c["id"]
                    ]
                    st.success(f"Removed {c['name']}. Re-run 'Analyze Candidates' in Candidate Evaluation to re-score them.")
                    st.rerun()

            
            with tabs[3]:
                preview = get_resume_preview_html(c)
                if preview:
                    st.markdown(preview, unsafe_allow_html=True)
                else:
                    st.text_area("Resume Text", c["text"], height=400)
