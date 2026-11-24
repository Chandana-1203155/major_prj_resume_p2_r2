"""Reports page."""

import pandas as pd
import streamlit as st

from scoring.deterministic import candidate_skill_gaps


def render_reports():
    st.header("Reports")
    candidates = st.session_state.candidates
    if not candidates:
        st.info("No candidate data to export.")
        return
    export_data = []
    for c in candidates:
        export_data.append({
            "Name": c["name"],
            "Email": c["resume_data"].get("email", ""),
            "Phone": c["resume_data"].get("phone", ""),
            "ATS Match Score": c["ats_score"],
            "Best Role": c["best_role"],
            "AI Recommendation": c["ai_recommendation"].get("decision", ""),
            "Recruiter Decision": c["recruiter_decision"],
            "Matched Skills": ", ".join(c.get("match_result", {}).get("matched_skills", [])),
            "Missing Skills": ", ".join(candidate_skill_gaps(c)),
            "Recruiter Notes": c["recruiter_notes"],
            "Recruiter Reason": c["recruiter_reason"]
        })
    df = pd.DataFrame(export_data)
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False)
    st.download_button("Download CSV Report", csv, "candidates_report.csv", "text/csv")
