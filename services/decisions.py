"""Recruiter decisions: AI recommendation vs. recruiter decision, with history.

Design rules (all enforced here, in one place):

* The AI recommendation (``candidate["ai_recommendation"]``) is NEVER written
  to by anything in this module. Recruiter decisions live only in
  ``candidate["recruiter_decision"]``.
* Every decision change is appended to an in-memory history list
  (``st.session_state.decision_history``) recording what changed, whether it
  came from accepting the AI recommendation or from the recruiter manually,
  what the AI recommended at that moment, and when it happened.
* Nothing is persisted to disk - the history lives for the Streamlit session.

The functions that take a ``history`` list are pure (no Streamlit) so they are
easy to test; ``set_recruiter_decision`` is a thin session-state wrapper used
by the pre-existing Save buttons so they feed the same history.
"""

import re
from collections import Counter
from datetime import datetime

import streamlit as st

NOT_DECIDED = "Not Decided"
ACTIONABLE_DECISIONS = ("Shortlist", "On Hold", "Reject")
ALL_DECISIONS = (NOT_DECIDED,) + ACTIONABLE_DECISIONS

SOURCE_AI = "ai_recommendation"   # recruiter accepted the AI recommendation
SOURCE_MANUAL = "manual"          # recruiter chose the decision themselves

_ALIASES = {
    "shortlist": "Shortlist", "shortlisted": "Shortlist",
    "on hold": "On Hold", "hold": "On Hold", "onhold": "On Hold",
    "reject": "Reject", "rejected": "Reject",
}


# -------------------------------------------------
# AI recommendation (read-only access)
# -------------------------------------------------
def normalize_decision(raw):
    """Map free-text decision wording to one of ACTIONABLE_DECISIONS, else None."""
    if raw is None:
        return None
    key = re.sub(r"[\s_-]+", " ", str(raw).strip().lower())
    return _ALIASES.get(key)


def get_ai_decision(candidate):
    """The AI's recommended decision as a valid recruiter decision, or None
    when there is no usable recommendation. Never modifies the candidate."""
    rec = candidate.get("ai_recommendation") or {}
    return normalize_decision(rec.get("decision"))


def current_decision(candidate):
    d = candidate.get("recruiter_decision", NOT_DECIDED)
    return d if d in ALL_DECISIONS else NOT_DECIDED


# -------------------------------------------------
# History
# -------------------------------------------------
def last_entry(history, candidate_id):
    for entry in reversed(history):
        if entry.get("candidate_id") == candidate_id:
            return entry
    return None


def source_label(entry):
    if entry["source"] == SOURCE_AI:
        return "Accepted AI recommendation"
    if entry.get("ai_decision") is None:
        return "Manual"
    return "Manual override" if entry.get("overrides_ai") else "Manual (matches AI)"


def decision_provenance(candidate, history):
    """Describe how the candidate's *current* decision was made, or None if the
    history has nothing consistent with it (e.g. never decided)."""
    if current_decision(candidate) == NOT_DECIDED:
        return None
    entry = last_entry(history, candidate.get("id"))
    if not entry or entry["to_decision"] != current_decision(candidate):
        return None
    return {"label": source_label(entry), "timestamp": entry["timestamp"], "entry": entry}


def format_timestamp(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y %H:%M:%S")
    except (TypeError, ValueError):
        return str(iso)


def record_decision(candidate, new_decision, history, source=SOURCE_MANUAL, via="", now=None):
    """Set the recruiter decision and append a history entry. Returns the entry.

    Only ``recruiter_decision`` is written on the candidate; the AI
    recommendation is left untouched.
    """
    if new_decision not in ALL_DECISIONS:
        raise ValueError(f"Invalid decision: {new_decision!r}")
    if source not in (SOURCE_AI, SOURCE_MANUAL):
        raise ValueError(f"Invalid source: {source!r}")
    old = current_decision(candidate)
    ai = get_ai_decision(candidate)
    candidate["recruiter_decision"] = new_decision
    entry = {
        "seq": len(history) + 1,
        "candidate_id": candidate.get("id"),
        "candidate_name": candidate.get("name", ""),
        "from_decision": old,
        "to_decision": new_decision,
        "source": source,
        "via": via,
        "ai_decision": ai,
        "overrides_ai": bool(ai is not None and new_decision != ai),
        "timestamp": (now or datetime.now()).isoformat(timespec="seconds"),
    }
    history.append(entry)
    return entry


# -------------------------------------------------
# Single-candidate and bulk actions
# -------------------------------------------------
def ai_already_applied(candidate, history):
    """True if the candidate's current decision is already the AI's, applied by
    accepting the AI recommendation (so applying again would change nothing)."""
    ai = get_ai_decision(candidate)
    if ai is None or current_decision(candidate) != ai:
        return False
    entry = last_entry(history, candidate.get("id"))
    return bool(entry and entry["source"] == SOURCE_AI and entry["to_decision"] == ai)


def apply_ai_recommendation(candidate, history, via="", now=None):
    """Adopt the candidate's existing AI recommendation as the recruiter decision.

    Returns one of: 'moved' (decision changed), 'confirmed' (decision already
    equalled the AI's but is now recorded as accepted), 'already_applied',
    'no_recommendation'.
    """
    ai = get_ai_decision(candidate)
    if ai is None:
        return "no_recommendation"
    if ai_already_applied(candidate, history):
        return "already_applied"
    old = current_decision(candidate)
    record_decision(candidate, ai, history, source=SOURCE_AI, via=via, now=now)
    return "moved" if old != ai else "confirmed"


def apply_manual_decision(candidate, target, history, via="", now=None):
    """Recruiter manually sets a decision. Returns 'moved' or 'unchanged'."""
    if current_decision(candidate) == target:
        return "unchanged"
    record_decision(candidate, target, history, source=SOURCE_MANUAL, via=via, now=now)
    return "moved"


def bulk_apply_ai(candidates, history, via="", now=None):
    """Apply each candidate's own AI recommendation. Returns a Counter of outcomes."""
    return Counter(apply_ai_recommendation(c, history, via=via, now=now) for c in candidates)


def bulk_apply_manual(candidates, target, history, via="", now=None):
    """Apply one manual decision to every candidate. Returns a Counter of outcomes."""
    return Counter(apply_manual_decision(c, target, history, via=via, now=now) for c in candidates)


# -------------------------------------------------
# Previews shown in the confirmation step
# -------------------------------------------------
def preview_ai(candidates, history):
    rows = []
    for c in candidates:
        ai = get_ai_decision(c)
        cur = current_decision(c)
        if ai is None:
            result = "No AI recommendation - unchanged"
        elif ai_already_applied(c, history):
            result = f"Already {ai} (AI applied) - unchanged"
        elif ai == cur:
            result = f"Stays {ai} (recorded as AI-accepted)"
        else:
            result = f"{cur} -> {ai}"
        rows.append({"Candidate": c.get("name", ""), "Current": cur,
                     "AI Recommendation": ai or "-", "Result": result})
    return rows


def preview_manual(candidates, target):
    rows = []
    for c in candidates:
        cur = current_decision(c)
        ai = get_ai_decision(c)
        rows.append({
            "Candidate": c.get("name", ""), "Current": cur,
            "AI Recommendation": ai or "-",
            "Result": "Unchanged" if cur == target else f"{cur} -> {target}"
                      + (" (overrides AI)" if ai is not None and ai != target else ""),
        })
    return rows


# -------------------------------------------------
# Session-state wrapper for the pre-existing "Save" / bulk-shortlist buttons
# -------------------------------------------------
def get_history():
    if "decision_history" not in st.session_state:
        st.session_state.decision_history = []
    return st.session_state.decision_history


def set_recruiter_decision(candidate, decision, via="manual"):
    """Drop-in replacement for ``candidate["recruiter_decision"] = decision``
    that also writes a history entry when the decision actually changes."""
    if current_decision(candidate) == decision and candidate.get("recruiter_decision") == decision:
        return None
    return record_decision(candidate, decision, get_history(), source=SOURCE_MANUAL, via=via)
