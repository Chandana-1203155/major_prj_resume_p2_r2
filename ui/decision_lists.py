"""Recommendation-grouped candidate decisions for the Shortlist Workspace."""

import html

import pandas as pd
import streamlit as st

from services.decisions import (
    ACTIONABLE_DECISIONS,
    ALL_DECISIONS,
    NOT_DECIDED,
    apply_manual_decision,
    bulk_apply_ai,
    bulk_apply_manual,
    current_decision,
    decision_provenance,
    format_timestamp,
    get_ai_decision,
    get_history,
    preview_ai,
    preview_manual,
    source_label,
)
from ui.components import render_quick_view_block, render_why_score_block

GROUP_ORDER = ("shortlist", "on_hold", "not_selected", "not_decided")
GROUP_TITLES = {
    "shortlist": "AI Recommends Shortlist",
    "on_hold": "AI Recommends On Hold",
    "not_selected": "AI Recommends Not Selected",
    "not_decided": "Not Decided / No AI Recommendation",
}
DISPLAY_DECISION = {
    "Shortlist": "Shortlist",
    "On Hold": "On Hold",
    "Reject": "Not Selected",
    NOT_DECIDED: NOT_DECIDED,
}
SELECT_DECISION = {
    "Shortlist": "Shortlist",
    "On Hold": "On Hold",
    "Not Selected": "Reject",
    NOT_DECIDED: NOT_DECIDED,
}


def _group_for_candidate(candidate):
    ai_decision = get_ai_decision(candidate)
    if ai_decision == "Shortlist":
        return "shortlist"
    if ai_decision == "On Hold":
        return "on_hold"
    if ai_decision == "Reject":
        return "not_selected"
    return "not_decided"


def _is_needs_review(candidate):
    return bool(candidate.get("error"))


def _group_candidates(candidates):
    grouped = {group: [] for group in GROUP_ORDER}
    needs_review = []
    for candidate in candidates:
        if _is_needs_review(candidate):
            needs_review.append(candidate)
        else:
            grouped[_group_for_candidate(candidate)].append(candidate)

    for members in grouped.values():
        members.sort(key=lambda candidate: candidate.get("ats_score", 0), reverse=True)
    return grouped, needs_review


def _selection_key(candidate_id):
    return f"workspace_selected_{candidate_id}"


def _selected(group_members):
    return [
        candidate for candidate in group_members
        if st.session_state.get(_selection_key(candidate["id"]), False)
    ]


def _reset_selection(candidate_ids):
    for candidate_id in candidate_ids:
        st.session_state[_selection_key(candidate_id)] = False


def _request_bulk(group_key, action, candidate_ids, target=None):
    members_by_id = {
        candidate["id"]: candidate
        for candidate in st.session_state.candidates
        if not _is_needs_review(candidate)
    }
    scoped_ids = [
        candidate_id for candidate_id in candidate_ids
        if candidate_id in members_by_id
        and _group_for_candidate(members_by_id[candidate_id]) == group_key
        and st.session_state.get(_selection_key(candidate_id), False)
    ]
    if not scoped_ids:
        st.session_state["workspace_flash"] = ("warning", "Select at least one candidate in this section.")
        return
    st.session_state["workspace_pending"] = {
        "group": group_key,
        "action": action,
        "target": target,
        "ids": scoped_ids,
    }


def _cancel_bulk():
    st.session_state.pop("workspace_pending", None)


def _confirm_bulk():
    pending = st.session_state.pop("workspace_pending", None)
    if not pending:
        return

    by_id = {
        candidate["id"]: candidate
        for candidate in st.session_state.candidates
        if not _is_needs_review(candidate)
    }
    chosen = [
        by_id[candidate_id]
        for candidate_id in pending["ids"]
        if candidate_id in by_id
        and _group_for_candidate(by_id[candidate_id]) == pending["group"]
    ]
    if not chosen:
        st.session_state["workspace_flash"] = ("warning", "No selected candidates remain in this section.")
        return

    if pending["action"] == "ai":
        results = bulk_apply_ai(chosen, get_history(), via="workspace_bulk_ai")
        message = (
            f"Applied each candidate's AI recommendation to {len(chosen)} selected "
            f"candidate(s): {results['moved']} changed, {results['confirmed']} confirmed, "
            f"{results['already_applied']} already applied, {results['no_recommendation']} without a recommendation."
        )
    else:
        target = pending["target"]
        results = bulk_apply_manual(chosen, target, get_history(), via="workspace_bulk_manual")
        message = (
            f"Set {len(chosen)} selected candidate(s) to "
            f"{DISPLAY_DECISION[target]}: {results['moved']} changed, {results['unchanged']} unchanged."
        )

    _reset_selection(pending["ids"])
    for candidate in chosen:
        st.session_state[f"workspace_change_decision_{candidate['id']}"] = DISPLAY_DECISION[
            current_decision(candidate)
        ]
    st.session_state["workspace_flash"] = ("success", message)


def _select_all(candidate_ids):
    for candidate_id in candidate_ids:
        st.session_state[_selection_key(candidate_id)] = True


def _clear_selection(candidate_ids):
    _reset_selection(candidate_ids)


def _candidate_by_id(candidate_id):
    return next(
        (candidate for candidate in st.session_state.candidates if candidate.get("id") == candidate_id),
        None,
    )


def _save_manual_decision(candidate_id, selected_label):
    candidate = _candidate_by_id(candidate_id)
    if candidate is None:
        return
    target = SELECT_DECISION[selected_label]
    result = apply_manual_decision(
        candidate,
        target,
        get_history(),
        via="workspace_manual",
    )
    if result == "moved":
        _reset_selection([candidate_id])
        st.session_state["workspace_flash"] = (
            "success",
            f"{candidate.get('name', 'Candidate')}: recruiter decision set to {selected_label}.",
        )


def _render_bulk_confirmation(group_key):
    pending = st.session_state.get("workspace_pending")
    if not pending or pending["group"] != group_key:
        return

    by_id = {
        candidate["id"]: candidate
        for candidate in st.session_state.candidates
    }
    chosen = [by_id[cid] for cid in pending["ids"] if cid in by_id]
    if not chosen:
        _cancel_bulk()
        return

    action_label = (
        "apply each candidate's AI recommendation"
        if pending["action"] == "ai"
        else f"set the recruiter decision to {DISPLAY_DECISION[pending['target']]}"
    )
    st.warning(
        f"Confirm: {action_label} for these {len(chosen)} selected candidate(s) "
        f"from **{GROUP_TITLES[group_key]}**?"
    )
    rows = preview_ai(chosen, get_history()) if pending["action"] == "ai" else preview_manual(
        chosen, pending["target"]
    )
    for row in rows:
        if row.get("AI Recommendation"):
            row["AI Recommendation"] = DISPLAY_DECISION.get(
                row["AI Recommendation"], row["AI Recommendation"]
            )
        if row.get("Current"):
            row["Current"] = DISPLAY_DECISION.get(row["Current"], row["Current"])
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    confirm, cancel = st.columns([1, 1])
    confirm.button(
        "Confirm",
        type="primary",
        key=f"workspace_confirm_{group_key}",
        on_click=_confirm_bulk,
    )
    cancel.button("Cancel", key=f"workspace_cancel_{group_key}", on_click=_cancel_bulk)


def _render_toolbar(group_key, members):
    member_ids = [candidate["id"] for candidate in members]
    selected = _selected(members)

    # Row 1: selection controls
    count_col, select_all, clear_selection = st.columns([2.2, 1, 1], vertical_alignment="center")
    count_col.markdown(f"**Selected:** {len(selected)} of {len(members)}")
    select_all.button(
        "Select All",
        key=f"workspace_select_all_{group_key}",
        disabled=not members,
        on_click=_select_all,
        args=(member_ids,),
    )
    clear_selection.button(
        "Clear Selection",
        key=f"workspace_clear_{group_key}",
        disabled=not selected,
        on_click=_clear_selection,
        args=(member_ids,),
    )

    # Row 2: bulk actions for the selected candidates
    apply_ai_col, shortlist_col, hold_col, not_selected_col = st.columns(4)
    apply_ai_col.button(
        "Apply AI Recommendation",
        key=f"workspace_apply_ai_{group_key}",
        disabled=not selected or group_key == "not_decided",
        on_click=_request_bulk,
        args=(group_key, "ai", member_ids),
        help="Sets only selected candidates' recruiter decisions to their own AI recommendations.",
    )
    shortlist_col.button(
        "Shortlist Selected",
        key=f"workspace_set_shortlist_{group_key}",
        disabled=not selected,
        on_click=_request_bulk,
        args=(group_key, "manual", member_ids, "Shortlist"),
    )
    hold_col.button(
        "Hold Selected",
        key=f"workspace_set_hold_{group_key}",
        disabled=not selected,
        on_click=_request_bulk,
        args=(group_key, "manual", member_ids, "On Hold"),
    )
    not_selected_col.button(
        "Not Select Selected",
        key=f"workspace_set_not_selected_{group_key}",
        disabled=not selected,
        on_click=_request_bulk,
        args=(group_key, "manual", member_ids, "Reject"),
    )
    _render_bulk_confirmation(group_key)


def _render_candidate_card(candidate, history, group_key):
    candidate_id = candidate["id"]
    current = current_decision(candidate)
    ai_decision = get_ai_decision(candidate)
    rec = candidate.get("ai_recommendation") or {}
    provenance = decision_provenance(candidate, history)

    with st.container(border=True):
        checkbox, details = st.columns([0.35, 6.65], vertical_alignment="top")
        checkbox.checkbox(
            f"Select {candidate.get('name', 'candidate')}",
            key=_selection_key(candidate_id),
            label_visibility="collapsed",
        )
        with details:
            name_col, score_col = st.columns([3, 1], vertical_alignment="center")
            name_col.markdown(f"**{candidate.get('name', 'Unknown candidate')}**")
            score = candidate.get("ats_score", 0)
            score_col.markdown(f"**ATS Match Score**  \n{score:.2f}%")

            ai_col, decision_col = st.columns(2)
            ai_label = DISPLAY_DECISION.get(ai_decision, "No AI Recommendation")
            ai_col.markdown(f"**AI Recommendation**  \n{ai_label}")
            if rec.get("reason"):
                st.caption(rec["reason"])

            decision_label = DISPLAY_DECISION[current]
            decision_col.markdown(f"**Recruiter Final Decision**  \n{decision_label}")

            if provenance:
                source = source_label(provenance["entry"])
                timestamp = format_timestamp(provenance["timestamp"])
                if provenance["entry"].get("overrides_ai"):
                    st.warning(f"Manual Override · {timestamp}")
                else:
                    st.caption(f"{source} · {timestamp}")

            select_key = f"workspace_change_decision_{candidate_id}"
            current_label = DISPLAY_DECISION[current]
            if select_key not in st.session_state:
                st.session_state[select_key] = current_label
            decision_options = [NOT_DECIDED, "Shortlist", "On Hold", "Not Selected"]
            control, save = st.columns([3, 1], vertical_alignment="center")
            selected_label = control.selectbox(
                "Change recruiter decision",
                options=decision_options,
                key=select_key,
                label_visibility="collapsed",
            )
            save.button(
                "Change Decision",
                key=f"workspace_save_decision_{candidate_id}",
                disabled=SELECT_DECISION[selected_label] == current,
                on_click=_save_manual_decision,
                args=(candidate_id, selected_label),
            )

            with st.expander("View Details"):
                render_quick_view_block(candidate)
                with st.expander("Why this ATS Match Score?"):
                    render_why_score_block(candidate)


def _render_group(group_key, members, history):
    title = GROUP_TITLES[group_key]
    with st.container(border=True):
        st.subheader(f"{title} — {len(members)} Candidate(s)")
        _render_toolbar(group_key, members)
        if not members:
            st.caption("No candidates in this section.")
            return
        for candidate in members:
            _render_candidate_card(candidate, history, group_key)


def _render_needs_review(needs_review, errors):
    review_items = []
    for candidate in needs_review:
        review_items.append((
            candidate.get("name") or candidate.get("file_name") or "Candidate",
            str(candidate["error"]),
        ))
    for error in errors:
        if isinstance(error, dict):
            review_items.append((
                error.get("name") or error.get("file_name") or "Analysis error",
                str(error.get("error", error)),
            ))
        else:
            review_items.append(("Analysis error", str(error)))

    with st.container(border=True):
        st.subheader(f"Needs Review — {len(review_items)} Candidate(s)")
        if not review_items:
            st.caption("No failed analyses or review errors.")
            return
        for name, error in review_items:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.error(error)


def _render_history(history):
    with st.expander(f"Decision History ({len(history)})"):
        if not history:
            st.caption("No decisions recorded yet this session.")
            return
        rows = [{
            "When": format_timestamp(entry["timestamp"]),
            "Candidate": entry["candidate_name"],
            "From": DISPLAY_DECISION.get(entry["from_decision"], entry["from_decision"]),
            "To": DISPLAY_DECISION.get(entry["to_decision"], entry["to_decision"]),
            "How": source_label(entry),
            "AI recommended": DISPLAY_DECISION.get(
                entry["ai_decision"], entry["ai_decision"] or "-"
            ),
            "Action": entry["via"],
        } for entry in reversed(history)]
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, width="stretch")
        st.download_button(
            "Download Decision History",
            df.to_csv(index=False).encode("utf-8"),
            "decision_history.csv",
            "text/csv",
            key="workspace_history_csv",
        )
        st.caption("History is kept for this session only and is cleared by 'Reset All Data'.")


def render_decision_lists(candidates):
    st.header("Candidate Decisions")
    st.caption("Review AI recommendations and make the recruiter's final decision.")

    flash = st.session_state.pop("workspace_flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])

    grouped, needs_review = _group_candidates(candidates)
    history = get_history()
    for group_key in GROUP_ORDER:
        _render_group(group_key, grouped[group_key], history)

    _render_needs_review(needs_review, st.session_state.get("analysis_errors", []))
    _render_history(history)
