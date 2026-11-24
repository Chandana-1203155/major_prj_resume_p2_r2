"""Reusable UI components and chart helpers."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st

from config import BREAKDOWN_LABELS
from scoring.ats import compute_ats_score
from scoring.deterministic import (
    candidate_skill_gaps,
    preferred_skill_total,
    required_skill_total,
)
from ui.helpers import decision_color


# -------------------------------------------------
# UI COMPONENTS
# -------------------------------------------------
def kpi_card(title, value, color="#2563eb"):
    st.markdown(
        f"""<div class='kpi-card'>
            <div class='kpi-title'>{title}</div>
            <div class='kpi-value' style='color:{color};'>{value}</div>
        </div>""",
        unsafe_allow_html=True
    )


def _render_fig(fig):
    """Render a matplotlib figure in Streamlit and close it to free memory."""
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _light_style(ax, fig):
    """Apply clean light theme to matplotlib axes and figure."""
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    ax.tick_params(colors='#475569', labelsize=9)
    ax.xaxis.label.set_color('#475569')
    ax.yaxis.label.set_color('#475569')
    ax.title.set_color('#0f172a')
    for spine in ax.spines.values():
        spine.set_color('#e2e8f0')


def _html_bar_chart(items, max_val, color="#38bdf8"):
    """Return HTML for a CSS bar chart. items = [(label, value), ...]"""
    if max_val == 0:
        max_val = 1
    rows = ""
    for label, val in items:
        pct = min(int(val / max_val * 100), 100)
        rows += f"""<div class='bar-row'>
            <span class='bar-label' title='{label}'>{label}</span>
            <div class='bar-track'><div class='bar-fill' style='width:{pct}%;background:{color};'>{val}</div></div>
        </div>"""
    return f"<div class='css-bar-chart'>{rows}</div>"


def _html_donut(segments, center_text="", center_sub=""):
    """Return HTML for a CSS conic-gradient donut. segments = [(label, value, color), ...]"""
    total = sum(v for _, v, _ in segments) or 1
    stops = []
    cum = 0
    for _, val, col in segments:
        start = cum / total * 360
        cum += val
        end = cum / total * 360
        stops.append(f"{col} {start:.1f}deg {end:.1f}deg")
    gradient = ", ".join(stops) if stops else "#e2e8f0 0deg 360deg"
    legend = ""
    for lbl, val, col in segments:
        pct = round(val / total * 100, 1) if total else 0
        legend += f"<div class='legend-item'><span class='legend-dot' style='background:{col};'></span>{lbl}: {val} ({pct}%)</div>"
    return f"""<div class='donut-wrap'>
        <div class='donut' style='background:conic-gradient({gradient});'>
            <div class='donut-hole'><span class='num'>{center_text}</span><span class='sub'>{center_sub}</span></div>
        </div>
        <div class='donut-legend'>{legend}</div>
    </div>"""


def render_quick_view_block(c, rank=None, total=None):
    """
    Compact, scan-in-5-seconds summary of a candidate: reuses fields already
    computed during evaluation (match_result, ai_evaluation) —
    no new scoring, no new AI call. Used both in the Candidates page (as a
    tab) and in the Shortlist Workspace, so the same "quick read" looks and
    behaves identically everywhere it appears.
    """
    match = c.get("match_result", {})
    ai_eval = c.get("ai_evaluation", {})
    req_matched = match.get("matched_skills", [])
    req_missing = candidate_skill_gaps(c)
    pref_matched = match.get("preferred_matched_skills", [])
    req_total = required_skill_total(match)
    pref_total = preferred_skill_total(match)

    rank_html = f"<div class='stat-mini'><div class='s-val' style='color:#7c3aed;'>#{rank}{f' / {total}' if total else ''}</div><div class='s-lbl'>Rank</div></div>" if rank else ""

    st.html(f"""<div class='stat-row'>
        {rank_html}
        <div class='stat-mini'><div class='s-val' style='color:#2563eb;'>{len(req_matched)}/{req_total}</div><div class='s-lbl'>Matched Required Skills</div></div>
        <div class='stat-mini'><div class='s-val' style='color:#0891b2;'>{len(pref_matched)}/{pref_total}</div><div class='s-lbl'>Matched Preferred Skills</div></div>
        <div class='stat-mini'><div class='s-val' style='color:{decision_color(c.get("recruiter_decision","Not Decided"))};'>{c.get("recruiter_decision","Not Decided")}</div><div class='s-lbl'>Decision</div></div>
    </div>""")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Key Strengths**")
        strengths = ai_eval.get("strengths", [])[:3]
        if strengths:
            for s in strengths:
                st.markdown(f"<div style='color:#16a34a;font-size:.88rem;'>+ {s}</div>", unsafe_allow_html=True)
        else:
            st.caption("None recorded.")
    with col2:
        st.markdown("**⚠️ Key Gaps**")
        gaps = req_missing[:5]
        if gaps:
            st.markdown(", ".join(f"<span class='badge badge-red'>{g}</span>" for g in gaps), unsafe_allow_html=True)
        else:
            st.caption("No missing required skills.")

    summary = ai_eval.get("summary", "")
    if summary:
        st.caption(summary)


def render_why_score_block(c):
    """
    Optional component breakdown using the exact formula used for ats_score.
    """
    breakdown = c.get("ats_breakdown", {})
    weights = st.session_state.weights
    rows = []
    for key, label in BREAKDOWN_LABELS.items():
        component_score = breakdown.get(key, 0)
        weight = weights.get(key, 0)
        contribution = component_score * weight / 100
        rows.append(
            f"| {label} | {component_score:g}% | {weight:g}% | {contribution:.4f} pts |"
        )

    score = compute_ats_score(breakdown, weights)
    st.markdown(
        "| Component | Score | Weight | Contribution |\n"
        "|---|---:|---:|---:|\n"
        + "\n".join(rows)
        + f"\n\n**ATS Match Score: {score:.2f}%**"
    )
    st.caption(
        "Contribution = component score × weight ÷ 100. "
        "The final score is the sum of contributions, rounded to 2 decimals."
    )
