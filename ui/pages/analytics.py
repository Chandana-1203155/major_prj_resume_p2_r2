"""Concise, recruiter-focused analytics."""

from collections import Counter
import math
from numbers import Real

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from scoring.deterministic import (
    candidate_skill_gaps,
    normalize_skill,
)
from services.decisions import current_decision, get_ai_decision
from ui.components import _light_style, _render_fig

DECISION_CATEGORIES = ("Shortlist", "On Hold", "Not Selected")
DECISION_LABELS = {
    "Shortlist": "Shortlisted",
    "On Hold": "On Hold",
    "Reject": "Not Selected",
}
COLORS = {
    "blue": "#3b82f6",
    "green": "#16a34a",
    "teal": "#0891b2",
    "red": "#dc2626",
    "purple": "#8b5cf6",
    "amber": "#d97706",
}


def _is_failed(candidate):
    return bool(candidate.get("error"))


def _valid_score(candidate):
    score = candidate.get("ats_score")
    return isinstance(score, Real) and math.isfinite(float(score))


def _skill_gap_counts(candidates):
    """Aggregate deterministic, evidence-checked gaps by canonical skill."""
    gap_counts = Counter()
    labels = {}
    for candidate in candidates:
        for skill in candidate_skill_gaps(candidate):
            canonical = normalize_skill(skill)
            gap_counts[canonical] += 1
            labels.setdefault(canonical, skill.strip())
    top_gaps = gap_counts.most_common(10)
    return [(labels[skill], count) for skill, count in top_gaps]


def _render_score_chart(candidates):
    st.subheader("ATS Match Score")
    ranked = sorted(candidates, key=lambda candidate: float(candidate["ats_score"]), reverse=True)
    if not ranked:
        st.info("No analyzed candidate scores are available.")
        return

    labels = [str(candidate.get("name") or candidate.get("file_name") or "Candidate") for candidate in ranked]
    scores = [float(candidate["ats_score"]) for candidate in ranked]
    fig, ax = plt.subplots(figsize=(10, max(3.2, 0.42 * len(ranked))))
    _light_style(ax, fig)
    bars = ax.barh(labels[::-1], scores[::-1], color=COLORS["blue"], height=0.66, edgecolor="none")
    for bar, score in zip(bars, scores[::-1]):
        ax.text(
            bar.get_width() + 0.8,
            bar.get_y() + bar.get_height() / 2,
            f"{score:.2f}%",
            va="center",
            ha="left",
            color="#334155",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_xlabel("ATS Match Score (%)")
    ax.set_ylabel("Candidate")
    ax.set_xlim(0, max(105, max(scores) + 12))
    ax.set_xticks(range(0, 101, 20))
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _render_fig(fig)





def _render_skill_gaps(candidates):
    st.subheader("Top Skill Gaps")
    top_gaps = _skill_gap_counts(candidates)
    if not top_gaps:
        st.info("No deterministic skill gaps are available.")
        return

    labels = [skill for skill, _ in top_gaps]
    counts = [count for _, count in top_gaps]
    fig, ax = plt.subplots(figsize=(10, max(3.0, 0.48 * len(labels) + 1.0)))
    _light_style(ax, fig)
    bars = ax.barh(labels[::-1], counts[::-1], color=COLORS["red"], height=0.64, edgecolor="none")
    for bar, count in zip(bars, counts[::-1]):
        ax.text(
            bar.get_width() + 0.08,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            va="center",
            ha="left",
            color="#334155",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_xlabel("Number of Candidates")
    ax.set_ylabel("Skill")
    ax.set_xlim(0, max(counts) + 1)
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _render_fig(fig)


def _render_decision_chart(candidates):
    st.subheader("AI Recommendation vs Recruiter Final Decision")
    ai_counts = Counter()
    recruiter_counts = Counter()
    for candidate in candidates:
        ai_decision = get_ai_decision(candidate)
        if ai_decision in DECISION_CATEGORIES:
            ai_counts[ai_decision] += 1
        recruiter_decision = current_decision(candidate)
        if recruiter_decision in DECISION_CATEGORIES:
            recruiter_counts[recruiter_decision] += 1

    categories = [
        decision for decision in DECISION_CATEGORIES
        if ai_counts[decision] or recruiter_counts[decision]
    ]
    if not categories:
        st.info("No AI recommendations or recruiter final decisions are available.")
        return

    x = list(range(len(categories)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.2))
    _light_style(ax, fig)
    ai_bars = ax.bar(
        [position - width / 2 for position in x],
        [ai_counts[decision] for decision in categories],
        width,
        label="AI Recommendation",
        color=COLORS["purple"],
        edgecolor="none",
    )
    recruiter_bars = ax.bar(
        [position + width / 2 for position in x],
        [recruiter_counts[decision] for decision in categories],
        width,
        label="Recruiter Final Decision",
        color=COLORS["green"],
        edgecolor="none",
    )
    for bars in (ai_bars, recruiter_bars):
        for bar in bars:
            count = int(bar.get_height())
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.08,
                str(count),
                ha="center",
                va="bottom",
                color="#334155",
                fontsize=9,
                fontweight="bold",
            )
    ax.set_xticks(x, [DECISION_LABELS[decision] for decision in categories])
    ax.set_xlabel("Decision Category")
    ax.set_ylabel("Number of Candidates")
    ax.set_ylim(0, max(
        [ai_counts[decision] for decision in categories]
        + [recruiter_counts[decision] for decision in categories]
        + [1]
    ) + 1)
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _render_fig(fig)


def _experience_values(candidates):
    values = []
    for candidate in candidates:
        resume_data = candidate.get("resume_data") or {}
        years = resume_data.get("experience_years")
        if isinstance(years, Real) and not isinstance(years, bool):
            years = float(years)
            if math.isfinite(years) and years >= 0:
                values.append(years)
    return values


def _render_experience_chart(candidates):
    st.subheader("Experience Distribution")
    years = _experience_values(candidates)
    if len(years) < 2 or not any(year > 0 for year in years):
        st.info("Experience data is unavailable for the analyzed candidates.")
        return

    buckets = {
        "0–2 years": 0,
        "2–5 years": 0,
        "5–8 years": 0,
        "8+ years": 0,
    }
    for year in years:
        if year <= 2:
            buckets["0–2 years"] += 1
        elif year <= 5:
            buckets["2–5 years"] += 1
        elif year <= 8:
            buckets["5–8 years"] += 1
        else:
            buckets["8+ years"] += 1

    labels = [label for label, count in buckets.items() if count]
    counts = [count for count in buckets.values() if count]
    fig, ax = plt.subplots(figsize=(10, 4.0))
    _light_style(ax, fig)
    bars = ax.bar(labels, counts, color=COLORS["amber"], width=0.58, edgecolor="none")
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.08,
            str(count),
            ha="center",
            va="bottom",
            color="#334155",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_xlabel("Experience Range (Years)")
    ax.set_ylabel("Number of Candidates")
    ax.set_ylim(0, max(counts) + 1)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _render_fig(fig)


def render_analytics():
    st.header("Analytics")
    candidates = st.session_state.candidates
    if not candidates:
        st.info("No data available. Evaluate candidates first to see analytics.")
        return

    analyzed = [
        candidate for candidate in candidates
        if not _is_failed(candidate) and _valid_score(candidate)
    ]
    needs_review = sum(_is_failed(candidate) for candidate in candidates)
    needs_review += len(st.session_state.get("analysis_errors", []))
    highest_score = max(
        (float(candidate["ats_score"]) for candidate in analyzed),
        default=None,
    )
    shortlisted = sum(
        current_decision(candidate) == "Shortlist"
        for candidate in candidates
        if not _is_failed(candidate)
    )
    highest_label = f"{highest_score:.2f}%" if highest_score is not None else "—"

    st.markdown(f"""<div class='dash-grid'>
        <div class='dash-kpi'><div class='label'>Total Candidates</div><div class='val' style='color:#2563eb;'>{len(analyzed)}</div></div>
        <div class='dash-kpi'><div class='label'>Highest ATS Match Score</div><div class='val' style='color:#16a34a;'>{highest_label}</div></div>
        <div class='dash-kpi'><div class='label'>Shortlisted</div><div class='val' style='color:#16a34a;'>{shortlisted}</div></div>
        <div class='dash-kpi'><div class='label'>Needs Review</div><div class='val' style='color:#d97706;'>{needs_review}</div></div>
    </div>""", unsafe_allow_html=True)

    _render_score_chart(analyzed)
    _render_skill_gaps(analyzed)
    _render_decision_chart(analyzed)
    _render_experience_chart(analyzed)
