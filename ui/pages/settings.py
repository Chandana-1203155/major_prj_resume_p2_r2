"""Settings page."""

import streamlit as st


def render_settings():
    st.header("Settings")
    st.write("Configure default model and behavior.")
    st.markdown("---")

    st.subheader("Data Management")
    if st.button("Reset All Data", key="reset_data", type="primary"):
        for key in ["candidates", "jobs", "selected_candidates", "resume_files", "analysis_history", "analysis_errors", "decision_history"]:
            st.session_state[key] = []
        st.session_state.resume_cache = {}
        st.session_state.analysis_complete = False
        st.session_state.min_skill_match = 5
        st.session_state.processing_stats = {"processed": 0, "skipped": 0, "failed": 0}
        if "comparison_generated" in st.session_state:
            del st.session_state.comparison_generated
        st.success("All data reset successfully.")

    if st.button("Clear Resume Cache", key="clear_cache"):
        st.session_state.resume_cache = {}
        st.success("Resume cache cleared. Previously analyzed resumes will be re-evaluated on next analysis.")

    st.markdown("---")
    st.subheader("Platform Information")
    st.markdown("""
**HireGenAI** — AI Hiring Intelligence Platform

**Target Users:** HR Teams, Recruiters, Hiring Managers, Department Heads,Campus Hiring Teams

**Unique Selling Points:**
- AI-powered candidate evaluation with multi-agent LangGraph pipeline
- Automated Candidate Match Scoring with customizable weights (internal methodology, not an official ATS)
- Multi-candidate comparison with radar charts and ranking
- Skill gap analysis and demand trends
- Hiring funnel analytics and recruitment insights
- Fast resume parsing (PDF, DOCX, TXT, ZIP)
- Enterprise-grade candidate management workflow
""")
