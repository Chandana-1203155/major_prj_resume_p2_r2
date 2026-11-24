"""Comparison page."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from scoring.deterministic import (
    candidate_skill_gaps,
    preferred_skill_total,
    required_skill_total,
    unresolved_skill_gaps,
)
from ui.components import _light_style, _render_fig


def render_comparison():
    st.header("Candidate Comparison")
    candidates = st.session_state.candidates
    if not candidates:
        st.info("No candidates available. Evaluate resumes first.")
        return

    # Step 1: Select number of candidates
    st.subheader("Step 1 — Select Number of Candidates")
    num_candidates = st.selectbox(
        "How many candidates to compare?",
        options=[2, 3, 4, 5],
        index=0,
        key="compare_count"
    )

    # Step 2: Choose candidates
    st.subheader("Step 2 — Choose Candidates")
    candidate_options = {f"{c['name']} ({c['best_role']})": c["id"] for c in candidates}
    selected_labels = st.multiselect(
        f"Select up to {num_candidates} candidates",
        options=list(candidate_options.keys()),
        max_selections=num_candidates,
        key="compare_candidates_select"
    )
    selected_ids = [candidate_options[label] for label in selected_labels]
    selected = [c for c in candidates if c["id"] in selected_ids]

    for c in st.session_state.candidates:
        c["selected_for_comparison"] = c["id"] in selected_ids

    if len(selected) < 2:
        st.info(f"Select at least 2 candidates to compare (selected {len(selected)}).")
        return

    # Step 3: Compare button
    st.subheader("Step 3 — Compare")
    compare_clicked = st.button("Generate Comparison Report", key="generate_comparison", type="primary")

    if not compare_clicked and "comparison_generated" not in st.session_state:
        st.info("Click 'Generate Comparison Report' to view the comparison.")
        return

    if compare_clicked:
        st.session_state.comparison_generated = True

    # Step 4: Comparison Report
    st.subheader("Step 4 — Comparison Report")
    st.markdown("---")

    # --- Grouped Bar Chart ---
    st.markdown("### Visual Comparison — Score Breakdown")
    categories = ["Skills", "Experience", "Education", "Projects", "Certs", "Keywords"]
    cat_keys = ["skills", "experience", "education", "projects", "certifications", "keywords"]
    bar_colors = ["#3b82f6", "#16a34a", "#d97706", "#dc2626", "#8b5cf6"]

    x = np.arange(len(categories))
    n = len(selected)
    width = 0.7 / n

    fig, ax = plt.subplots(figsize=(10, 5))
    _light_style(ax, fig)
    for idx, c in enumerate(selected):
        values = [c["ats_breakdown"].get(k, 0) for k in cat_keys]
        offset = (idx - n / 2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=c["name"],
                      color=bar_colors[idx % len(bar_colors)], edgecolor='none')
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, str(val),
                    ha='center', va='bottom', fontsize=7, color='#475569', fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel("Score (%)", fontsize=10)
    ax.set_ylim(0, 110)
    ax.set_title("Score Breakdown Comparison", fontsize=13, fontweight='bold', pad=12)
    ax.legend(fontsize=9, framealpha=0.9, edgecolor='#e2e8f0')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    _render_fig(fig)

    # --- Comparison Table ---
    st.markdown("### Detailed Comparison Table")
    comparison_data = {
        "Metric": [
            "Name", "ATS Match Score", "Best Role", "Experience (Years)", "Education", "Education Level",
            "Skills Score", "Experience Score", "Education Score",
            "Projects Score", "Certifications Score", "Keywords Score",
            "Matched Required Skills", "Missing Required Skills",
            "Matched Preferred Skills", "Missing Preferred Skills",
            "Certifications", "AI Decision"
        ]
    }
    for c in selected:
        comparison_data[c["name"]] = [
            c["name"],
            f"{c['ats_score']}%",
            c["best_role"],
            f"{c['resume_data'].get('experience_years', 0)}",
            c["resume_data"].get("education", "N/A"),
            c["resume_data"].get("education_level", "N/A"),
            f"{c['ats_breakdown'].get('skills', 0)}%",
            f"{c['ats_breakdown'].get('experience', 0)}%",
            f"{c['ats_breakdown'].get('education', 0)}%",
            f"{c['ats_breakdown'].get('projects', 0)}%",
            f"{c['ats_breakdown'].get('certifications', 0)}%",
            f"{c['ats_breakdown'].get('keywords', 0)}%",
            f"{len(c.get('match_result', {}).get('matched_skills', []))} of {required_skill_total(c.get('match_result', {}))}",
            ", ".join(candidate_skill_gaps(c)[:5]) or "None",
            f"{len(c.get('match_result', {}).get('preferred_matched_skills', []))} of {preferred_skill_total(c.get('match_result', {}))}",
            ", ".join(unresolved_skill_gaps(
                c.get("match_result", {}).get("preferred_matched_skills", []),
                c.get("match_result", {}).get("preferred_missing_skills", []),
            )[:5]) or "None",
            ", ".join(c["resume_data"].get("certifications", [])[:3]) or "None",
            c["ai_recommendation"].get("decision", "On Hold")
        ]
    df_compare = pd.DataFrame(comparison_data)
    st.dataframe(df_compare, use_container_width=True, hide_index=True)

    # --- Ranking Summary ---
    best_overall = max(selected, key=lambda x: x["ats_score"])
    best_technical = max(selected, key=lambda x: x["ats_breakdown"].get("skills", 0))
    best_skill_match = max(
        selected,
        key=lambda candidate: len(candidate.get("match_result", {}).get("matched_skills", [])),
    )
    best_skill_match_result = best_skill_match.get("match_result", {})
    most_experienced = max(selected, key=lambda x: x["resume_data"].get("experience_years", 0))

    st.markdown(f"""<div class='chart-card'>
        <div class='chart-title'>Ranking Summary</div>
        <div class='dash-grid' style='grid-template-columns:repeat(2,1fr);'>
            <div class='dash-kpi'>
                <div class='label'>Best Overall Candidate</div>
                <div class='val' style='color:#16a34a;font-size:1.3rem;'>{best_overall['name']}</div>
                <div style='color:#64748b;font-size:.8rem;'>ATS Match Score: {best_overall['ats_score']}%</div>
            </div>
            <div class='dash-kpi'>
                <div class='label'>Strongest Technical</div>
                <div class='val' style='color:#2563eb;font-size:1.3rem;'>{best_technical['name']}</div>
                <div style='color:#64748b;font-size:.8rem;'>Technical: {best_technical['ats_breakdown'].get('skills', 0)}%</div>
            </div>
            <div class='dash-kpi'>
                <div class='label'>Best Skills Match</div>
                <div class='val' style='color:#d97706;font-size:1.3rem;'>{best_skill_match['name']}</div>
                <div style='color:#64748b;font-size:.8rem;'>Required: {len(best_skill_match_result.get('matched_skills', []))} of {required_skill_total(best_skill_match_result)} · Preferred: {len(best_skill_match_result.get('preferred_matched_skills', []))} of {preferred_skill_total(best_skill_match_result)}</div>
            </div>
            <div class='dash-kpi'>
                <div class='label'>Most Experienced</div>
                <div class='val' style='color:#7c3aed;font-size:1.3rem;'>{most_experienced['name']}</div>
                <div style='color:#64748b;font-size:.8rem;'>Experience: {most_experienced['resume_data'].get('experience_years', 0)} yrs</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # --- Export Comparison ---
    csv = df_compare.to_csv(index=False).encode("utf-8")
    st.download_button("Download Comparison Report", csv, "candidate_comparison.csv", "text/csv")
