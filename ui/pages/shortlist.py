"""Shortlist Workspace page."""

import pandas as pd
import streamlit as st

from scoring.deterministic import preferred_skill_total, required_skill_total
from services.decisions import current_decision, get_ai_decision
from ui.decision_lists import DISPLAY_DECISION, render_decision_lists


def render_shortlist_workspace():
    candidates = st.session_state.candidates
    if not candidates:
        st.info("No candidates yet. Run an analysis in 'Candidate Evaluation' first.")
        render_decision_lists(candidates)
        return

    render_decision_lists(candidates)

    in_play = [
        candidate for candidate in candidates
        if current_decision(candidate) in ("Shortlist", "On Hold")
        and not candidate.get("error")
    ]
    if in_play:
        with st.expander("Download Shortlist Summary"):
            summary_rows = []
            for candidate in sorted(
                in_play,
                key=lambda item: item.get("ats_score", 0),
                reverse=True,
            ):
                match = candidate.get("match_result", {})
                matched_required = len(match.get("matched_skills", []))
                total_required = required_skill_total(match)
                matched_preferred = len(match.get("preferred_matched_skills", []))
                total_preferred = preferred_skill_total(match)
                summary_rows.append({
                    "Name": candidate.get("name", ""),
                    "ATS Match Score": f"{candidate.get('ats_score', 0):.2f}%",
                    "Required Skills": f"{matched_required} of {total_required}",
                    "Preferred Skills": f"{matched_preferred}/{total_preferred}",
                    "Experience (yrs)": candidate.get("resume_data", {}).get("experience_years", 0),
                    "AI Recommendation": DISPLAY_DECISION.get(
                        get_ai_decision(candidate),
                        "No AI Recommendation",
                    ),
                    "Recruiter Final Decision": DISPLAY_DECISION[current_decision(candidate)],
                })
            csv = pd.DataFrame(summary_rows).to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Shortlist Summary",
                csv,
                "shortlist_workspace.csv",
                "text/csv",
            )
