import streamlit as st

# Must be the first Streamlit command in the script.
st.set_page_config(
    page_title="HireGenAI",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

import config  # noqa: F401  (loads .env on import)
import os

from state.session import init_session
from ui.pages.analytics import render_analytics
from ui.pages.candidates import render_candidates
from ui.pages.comparison import render_comparison
from ui.pages.dashboard import render_dashboard
from ui.pages.evaluation import render_evaluation
from ui.pages.reports import render_reports
from ui.pages.settings import render_settings
from ui.pages.shortlist import render_shortlist_workspace
from ui.styles import inject_styles


# -------------------------------------------------
# APP BOOTSTRAP
# -------------------------------------------------
inject_styles()

# NOTE: never log or print any part of the API key, even a prefix — that is a
# credential-leak vector once logs are shared, screen-recorded, or persisted.
if "GEMINI_API_KEY" not in os.environ or not os.environ["GEMINI_API_KEY"]:
    st.error(
        "Please set GEMINI_API_KEY in your .env file. "
        "Use your own Gemini API key and never hardcode or share it."
    )
    st.stop()

init_session()


# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
def main():
    nav_options = ["Dashboard", "Candidate Evaluation", "Candidates", "Shortlist Workspace", "Analytics", "Comparison", "Reports", "Settings"]
    current = st.session_state.get("active_section", "Dashboard")
    current_idx = nav_options.index(current) if current in nav_options else 0

    with st.sidebar:
        st.markdown(
            """<div class='brand'>
                <div class='brand-mark'>HG</div>
                <div>
                    <div class='brand-name'>HireGenAI</div>
                    <div class='brand-tag'>AI Hiring Intelligence Platform</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("<div class='side-label'>Menu</div>", unsafe_allow_html=True)
        section = st.radio(
            "Navigation",
            options=nav_options,
            index=current_idx,
            key="nav_radio"
        )
        st.session_state.active_section = section
        st.markdown("---")

        # Sidebar summary
        cand_count = len(st.session_state.candidates)
        job_count = len(st.session_state.jobs)
        resume_count = len(st.session_state.resume_files)
        st.markdown("<div class='side-label'>Overview</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='side-stats'>
            <div class='side-stat'><span class='s-name'>Candidates analyzed</span><span class='s-num' style='color:#2563eb;'>{cand_count}</span></div>
            <div class='side-stat'><span class='s-name'>Job descriptions</span><span class='s-num' style='color:#16a34a;'>{job_count}</span></div>
            <div class='side-stat'><span class='s-name'>Resumes uploaded</span><span class='s-num' style='color:#d97706;'>{resume_count}</span></div>
        </div>""", unsafe_allow_html=True)

    section = st.session_state.active_section
    if section == "Dashboard":
        render_dashboard()
    elif section == "Candidate Evaluation":
        render_evaluation()
    elif section == "Candidates":
        render_candidates()
    elif section == "Shortlist Workspace":
        render_shortlist_workspace()
    elif section == "Analytics":
        render_analytics()
    elif section == "Comparison":
        render_comparison()
    elif section == "Reports":
        render_reports()
    elif section == "Settings":
        render_settings()


if __name__ == "__main__":
    main()
