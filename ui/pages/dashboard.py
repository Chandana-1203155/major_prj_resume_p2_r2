"""Dashboard page."""

from collections import Counter

import streamlit as st

from scoring.deterministic import (
    candidate_skill_gaps,
    normalize_skill,
    preferred_skill_total,
    required_skill_total,
)
from ui.components import _html_bar_chart, _html_donut


def render_dashboard():
    candidates = st.session_state.candidates

    total = len(candidates)
    shortlisted = sum(1 for c in candidates if c["recruiter_decision"] == "Shortlist" )
    on_hold = sum(1 for c in candidates if c["recruiter_decision"] == "On Hold")
    rejected = sum(1 for c in candidates if c["recruiter_decision"] == "Reject")
    not_decided = sum(
    1 for c in candidates
    if c.get("recruiter_decision", "Not Decided") == "Not Decided")
    under_review = not_decided
    scores = [c["ats_score"] for c in candidates] if candidates else []
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    top_score = max(scores) if scores else 0

    # ── KPI row ──
    kpi_html = f"""<div class='dash-grid'>
        <div class='dash-kpi'><div class='label'>Total Candidates</div><div class='val' style='color:#2563eb;'>{total}</div></div>
        <div class='dash-kpi'><div class='label'>Shortlisted</div><div class='val' style='color:#16a34a;'>{shortlisted}</div></div>
        <div class='dash-kpi'><div class='label'>On Hold</div><div class='val' style='color:#d97706;'>{on_hold}</div></div>
        <div class='dash-kpi'><div class='label'>Rejected</div><div class='val' style='color:#dc2626;'>{rejected}</div></div>
        <div class='dash-kpi'><div class='label'>Avg ATS Match Score</div><div class='val' style='color:#2563eb;'>{avg_score}%</div></div>
        <div class='dash-kpi'><div class='label'>Top ATS Match Score</div><div class='val' style='color:#16a34a;'>{top_score}%</div></div>
    </div>"""
    st.markdown(kpi_html, unsafe_allow_html=True)

    if not candidates:
        st.markdown("""<div class='chart-card' style='text-align:center;padding:3rem;'>
            <div style='font-size:2.5rem;margin-bottom:.5rem;'>📊</div>
            <div style='color:#64748b;font-size:1rem;'>Upload resumes and run evaluation to see live analytics</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Row 1: Status Donut + Skills Bar ──
    status_donut = _html_donut(
        [
    ("Shortlisted", shortlisted, "#22c55e"),
    ("Not Decided", not_decided, "#38bdf8"),
    ("On Hold", on_hold, "#f59e0b"),
    ("Rejected", rejected, "#ef4444")],
    str(total), "total"
    )

    all_skills = []
    for c in candidates:
        all_skills.extend(c["resume_data"].get("skills", []))
    skill_counts = Counter(all_skills)
    top_skills = skill_counts.most_common(12)
    skills_max = top_skills[0][1] if top_skills else 1
    skills_chart = _html_bar_chart(top_skills, skills_max, "#38bdf8") if top_skills else "<div style='color:#64748b;text-align:center;padding:1rem;'>No skill data yet</div>"

    st.markdown(f"""<div class='dash-row'>
        <div class='chart-card'><div class='chart-title'>Candidate Status Distribution</div>{status_donut}</div>
        <div class='chart-card'><div class='chart-title'>Top Skills Across Candidates</div>{skills_chart}</div>
    </div>""", unsafe_allow_html=True)

    # ── Row 2: Experience Distribution + Role Analysis ──
    exp_ranges = {"0-2 Yrs": 0, "3-5 Yrs": 0, "6-10 Yrs": 0, "10+ Yrs": 0}
    exp_colors = {"0-2 Yrs": "#38bdf8", "3-5 Yrs": "#22c55e", "6-10 Yrs": "#f59e0b", "10+ Yrs": "#a855f7"}
    for c in candidates:
        yrs = c["resume_data"].get("experience_years", 0)
        if yrs <= 2: exp_ranges["0-2 Yrs"] += 1
        elif yrs <= 5: exp_ranges["3-5 Yrs"] += 1
        elif yrs <= 10: exp_ranges["6-10 Yrs"] += 1
        else: exp_ranges["10+ Yrs"] += 1
    exp_donut = _html_donut([(k, v, exp_colors[k]) for k, v in exp_ranges.items()], str(total), "candidates")

    roles = [c["best_role"] for c in candidates if c.get("best_role")]
    role_counts = Counter(roles)
    top_roles = role_counts.most_common(10)
    roles_max = top_roles[0][1] if top_roles else 1
    roles_chart = _html_bar_chart(top_roles, roles_max, "#a855f7") if top_roles else "<div style='color:#64748b;text-align:center;padding:1rem;'>No role data yet</div>"

    st.markdown(f"""<div class='dash-row'>
        <div class='chart-card'><div class='chart-title'>Experience Distribution</div>{exp_donut}</div>
        <div class='chart-card'><div class='chart-title'>Candidates per Role</div>{roles_chart}</div>
    </div>""", unsafe_allow_html=True)

    # ── Row 3: Score Distribution + Top Ranked Candidates ──
    high = sum(1 for s in scores if s >= 70)
    mid = sum(1 for s in scores if 40 <= s < 70)
    low = sum(1 for s in scores if s < 40)
    score_donut = _html_donut(
        [("High 70-100", high, "#22c55e"), ("Medium 40-69", mid, "#f59e0b"), ("Low 0-39", low, "#ef4444")],
        f"{avg_score}%", "avg"
    )

    ranked = sorted(candidates, key=lambda x: x["ats_score"], reverse=True)[:10]
    rank_rows = ""
    for i, c in enumerate(ranked, 1):
        sc = c["ats_score"]
        sc_color = "#22c55e" if sc >= 70 else "#f59e0b" if sc >= 40 else "#ef4444"
        dec = c.get("recruiter_decision", "Not Decided")
        dec_cls = "badge-green" if dec == "Shortlist" else "badge-red" if dec == "Reject" else "badge-yellow"
        match = c.get("match_result", {})
        matched_ct = len(match.get("matched_skills", []))
        required_total = required_skill_total(match)
        preferred_ct = len(match.get("preferred_matched_skills", []))
        preferred_total = preferred_skill_total(match)
        rank_rows += f"""<tr>
            <td style='color:#64748b;font-weight:700;'>#{i}</td>
            <td>{c['name']}</td>
            <td><span class='score-pill' style='background:rgba({",".join(str(int(sc_color.lstrip("#")[j:j+2],16)) for j in (0,2,4))},.12);color:{sc_color};'>{sc}%</span></td>
            <td>{c['best_role']}</td>
            <td style='color:#64748b;font-size:.8rem;'>{matched_ct}/{required_total} required · {preferred_ct}/{preferred_total} preferred</td>
            <td><span class='badge {dec_cls}'>{dec}</span></td>
        </tr>"""
    rank_table = f"""<table class='rank-table'>
        <thead><tr><th>#</th><th>Candidate</th><th>ATS Match Score</th><th>Role</th><th>Matched Required / Preferred Skills</th><th>Decision</th></tr></thead>
        <tbody>{rank_rows}</tbody>
    </table>""" if ranked else "<div style='color:#64748b;text-align:center;padding:1rem;'>No ranked candidates yet</div>"

    st.markdown(f"""<div class='dash-row'>
        <div class='chart-card'><div class='chart-title'>ATS Match Score Distribution</div>{score_donut}</div>
        <div class='chart-card'><div class='chart-title'>Top Ranked Candidates</div>{rank_table}</div>
    </div>""", unsafe_allow_html=True)

    # ── Row 4: Quick Stats ──
    missing_counts = Counter()
    missing_labels = {}
    for c in candidates:
        for skill in candidate_skill_gaps(c):
            key = normalize_skill(skill)
            missing_counts[key] += 1
            missing_labels.setdefault(key, skill)
    top_missing = [
        (missing_labels[key], count)
        for key, count in missing_counts.most_common(5)
    ]
    missing_html = " ".join(f"<span class='badge badge-red'>{s}</span>" for s, _ in top_missing) if top_missing else "<span style='color:#64748b;'>None</span>"
    top_candidate = ranked[0] if ranked else None
    top_name = top_candidate["name"] if top_candidate else "—"

    st.markdown(f"""<div class='chart-card'>
        <div class='chart-title'>Quick Insights</div>
        <div class='stat-row'>
            <div class='stat-mini'><div class='s-val' style='color:#16a34a;'>{top_name}</div><div class='s-lbl'>Top Candidate</div></div>
            <div class='stat-mini'><div class='s-val' style='color:#d97706;'>{len(st.session_state.resume_files)}</div><div class='s-lbl'>Resumes Uploaded</div></div>
            <div class='stat-mini'><div class='s-val' style='color:#7c3aed;'>{len(st.session_state.jobs)}</div><div class='s-lbl'>Job Descriptions</div></div>
        </div>
        <div style='margin-top:.5rem;'><span style='color:#64748b;font-size:.8rem;'>Top Skill Gaps: </span>{missing_html}</div>
    </div>""", unsafe_allow_html=True)
