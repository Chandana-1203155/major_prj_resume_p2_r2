"""Small presentational helpers."""

import base64
import html

from scoring.deterministic import candidate_skill_gaps


def candidate_matches_search(candidate, query):
    """Match the Candidates search against candidate names and resume keywords."""
    query = query.strip().casefold()
    if not query:
        return True

    resume_data = candidate.get("resume_data") or {}
    keywords = resume_data.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    searchable_text = [
        candidate.get("name", ""),
        candidate.get("text", ""),
        *keywords,
    ]
    return any(query in str(value).casefold() for value in searchable_text)


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def status_color(status):
    return {
        "New": "#64748b",
        "AI Evaluated": "#38bdf8",
        "Shortlisted": "#22c55e",
        "On Hold": "#f59e0b",
        "Rejected": "#ef4444",
    }.get(status, "#64748b")


def decision_color(decision):
    return {
        "Shortlist": "#16a34a",
        "On Hold": "#d97706",
        "Reject": "#dc2626"
    }.get(decision, "#64748b")


def skill_gap_html(candidate, limit=None):
    """HTML for genuinely missing candidate skills, shared by results views.

    Related and unverified skills are intentionally excluded; they are
    available in the optional Skill Details section.
    """
    missing = candidate_skill_gaps(candidate)
    shown = missing if limit is None else missing[:limit]
    text = ", ".join(html.escape(s) for s in shown) or "None"
    if limit is not None and len(missing) > limit:
        text += f" <span style='color:#64748b;'>(+{len(missing) - limit} more)</span>"
    return text


def get_resume_preview_html(candidate):
    file_type = candidate.get("file_type", "txt")
    content = candidate.get("file_content", b"")
    if file_type == "pdf" and content:
        b64 = base64.b64encode(content).decode()
        return f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500px" style="border:none;"></iframe>'
    return None
