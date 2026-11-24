"""Evaluation page."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import streamlit as st

from ai.agents import jd_analyzer
from config import BREAKDOWN_LABELS, GEMINI_MODEL, MAX_RESUMES, SCORING_LOGIC_VERSION
from parsing.file_extraction import extract_text_from_file, extract_zip_files
from scoring.deterministic import (
    candidate_related_skills,
    candidate_skill_gaps,
    candidate_unverified_skills,
    preferred_skill_total,
    required_skill_total,
    unresolved_skill_gaps,
)
from scoring.ats import compute_ats_score, rebalance_weights
from services.candidate_pipeline import compute_cache_key, evaluate_candidate
from state.session import assign_job_id
from ui.helpers import skill_gap_html
from utils.hashing import compute_content_hash


def _on_ats_weight_change(changed_key):
    weights = st.session_state.weights
    changed_value = st.session_state[f"weight_{changed_key}"]
    weights = rebalance_weights(changed_key, changed_value, weights)
    st.session_state.weights = weights

    for key, value in weights.items():
        st.session_state[f"weight_{key}"] = value
    for candidate in st.session_state.candidates:
        candidate["ats_score"] = compute_ats_score(candidate["ats_breakdown"], weights)


def render_evaluation():
    st.header("Candidate Evaluation")
    st.markdown("<div class='section-note'>Upload Job Description → Upload Resumes → Configure Match Weights → Click Analyze Candidates → View Ranked Results</div>", unsafe_allow_html=True)
    st.caption(
        "ℹ️ The **ATS Match Score** shown throughout this app is an internal, "
        "configurable scoring methodology computed from resume/JD content by this "
        "application — it is not an official or standardized ATS (Applicant "
        "Tracking System) score, and results should inform, not replace, human "
        "judgement in hiring decisions."
    )

    def render_step_header(step, title, icon):
        st.markdown(
            f"""<div class='section-header'><span class='step-icon'>{icon}</span>{step} — {title}</div>""",
            unsafe_allow_html=True
        )

    # Step 1: Upload Job Description
    with st.container(border=True):
        render_step_header("Step 1", "Upload Job Description", "📄")
        st.info("Upload one or more Job Descriptions or paste text to get started.")
        uploaded_jds = st.file_uploader(
            "Upload Job Descriptions (TXT, DOCX, PDF)",
            type=["txt", "docx", "pdf"],
            accept_multiple_files=True,
            key="jd_upload_input"
        )
        jd_text = st.text_area("Or paste a job description here", height=150, key="jd_text_input")
        if st.button("Add Job Description(s)", key="add_jd"):
            new_jobs = []
            if uploaded_jds:
                for f in uploaded_jds:
                    text = extract_text_from_file(f)
                    if text:
                        new_jobs.append({"name": f.name, "text": text})
            if jd_text and jd_text.strip():
                new_jobs.append({"name": "Manual JD", "text": jd_text.strip()})
            if new_jobs:
                existing_texts = {j.get("text", "") for j in st.session_state.jobs}
                added_jobs = []
                failed = []
                for j in new_jobs:
                    if j["text"] in existing_texts:
                        continue  # skip exact duplicate JD text
                    state = {"resume_text": "", "jd_text": j["text"], "resume_data": {}, "jd_data": {}, "match_result": {},"ats_breakdown": {}, "ai_evaluation": {}, "ai_recommendation": {}}
                    try:
                        output = jd_analyzer(state)
                    except Exception as e:
                        failed.append(f"{j['name']}: {e}")
                        continue
                    jd_data = output.get("jd_data", {})
                    jd_data["file_name"] = j["name"]
                    jd_data["text"] = j["text"]
                    jd_data = assign_job_id(jd_data)  # assigns a stable in-memory id
                    added_jobs.append(jd_data)
                # Append rather than overwrite, so adding more JDs doesn't
                # silently discard previously-added job descriptions.
                st.session_state.jobs = st.session_state.jobs + added_jobs
                if added_jobs:
                    st.success(f"Added {len(added_jobs)} job description(s).")
                    st.session_state.analysis_complete = False
                for err in failed:
                    st.error(f"Failed to analyze job description — {err}")
                if not added_jobs and not failed:
                    st.info("No new job descriptions to add (duplicates skipped).")
            else:
                st.warning("Please upload a Job Description.")

        if st.session_state.jobs:
            st.write(f"**{len(st.session_state.jobs)} job description(s) uploaded.**")
            for job in st.session_state.jobs:
                st.write(f"- **{job.get('role', 'Unknown Role')}** ({job.get('file_name', 'Manual JD')})")

    # Step 2: Upload Candidate Resumes
    with st.container(border=True):
        render_step_header("Step 2", "Upload Candidate Resumes", "📎")
        st.info("Upload resumes in PDF/DOCX/TXT format, or a ZIP archive with multiple resumes.")

        _used = len(st.session_state.resume_files)
        st.progress(min(1.0, _used / MAX_RESUMES), text=f"{_used} / {MAX_RESUMES} resumes uploaded")
        if _used >= MAX_RESUMES:
            st.warning(
                f"You've reached the limit of {MAX_RESUMES} resumes. Remove a resume "
                "before adding another."
            )

        uploaded_resumes = st.file_uploader(
            "Upload resumes or zip files",
            type=["pdf", "docx", "txt", "zip"],
            accept_multiple_files=True,
            key="resume_upload_input"
        )
        if st.button("Add Resume(s)", key="add_resumes"):
            added = 0
            duplicates = 0
            capped = 0
            limit = MAX_RESUMES
            # Duplicate check is by CONTENT (a hash of the actual file bytes),
            # not filename — so the same resume uploaded twice under different
            # names is correctly recognized as one candidate, and two
            # different resumes that happen to share a filename are not
            # merged together.
            existing_hashes = {r["content_hash"] for r in st.session_state.resume_files if r.get("content_hash")}
            for f in uploaded_resumes or []:
                if len(st.session_state.resume_files) >= limit:
                    capped += 1
                    continue
                if f.name.lower().endswith(".zip"):
                    extracted = extract_zip_files(f)
                    for entry in extracted:
                        if len(st.session_state.resume_files) >= limit:
                            capped += 1
                            continue
                        if entry["content_hash"] in existing_hashes:
                            duplicates += 1
                            continue
                        st.session_state.resume_files.append(entry)
                        existing_hashes.add(entry["content_hash"])
                        added += 1
                else:
                    content = f.read()
                    f.seek(0)  # IMPORTANT: reset file pointer

                    content_hash = compute_content_hash(content)

                    if content_hash in existing_hashes:
                        duplicates += 1
                        continue

                    text = extract_text_from_file(f)
                    if text:
                        entry = {
                            "name": f.name,
                            "text": text,
                            "content": content,
                            "content_hash": content_hash,
                            "type": f.name.split('.')[-1].lower()
                        }
                        st.session_state.resume_files.append(entry)
                        existing_hashes.add(content_hash)
                        added += 1
            if added:
                msg = f"Uploaded {added} resume(s)."
                if duplicates:
                    msg += f" Skipped {duplicates} duplicate(s) (identical content already uploaded)."
                if capped:
                    msg += f" Skipped {capped} file(s) — the {limit}-resume limit was reached."
                st.success(msg)
                st.session_state.analysis_complete = False
            elif capped:
                st.warning(f"Skipped {capped} file(s) — the {limit}-resume limit is already reached. Remove a resume before adding another.")
            elif duplicates:
                st.warning(f"All {duplicates} file(s) were exact duplicates of resumes already uploaded — nothing new added.")
            else:
                st.warning("No new resumes were added.")

        resume_count = len(st.session_state.resume_files)
        if resume_count:
            st.write(f"**{resume_count} resume(s) uploaded.**")
            for idx, file_entry in enumerate(st.session_state.resume_files):
                cols = st.columns([9, 1.6], vertical_alignment="center")
                cols[0].markdown(f"- {file_entry['name']}")
                if cols[1].button("Remove", key=f"remove_resume_{idx}"):
                    st.session_state.resume_files.pop(idx)
                    st.success(f"Removed {file_entry['name']}.")
                    st.session_state.analysis_complete = False
                    st.rerun()
        else:
            st.info("No resumes uploaded yet.")

    # Step 3: Configure Minimum Skill Match & ATS Weights
    with st.container(border=True):
        render_step_header("Step 3", "Configure Match Criteria", "⚙️")

        # --- Minimum Skill Match Threshold ---
        st.markdown("""<div style='background:#f1f5f9;border:1px solid #e2e8f0;border-radius:10px;padding:1rem;margin-bottom:1rem;'>
            <div style='color:#0f172a;font-weight:700;font-size:1rem;margin-bottom:.3rem;'>Minimum Matching Skills</div>
            <div style='color:#475569;font-size:.82rem;'>Set the minimum number of skills that must match between a candidate's resume and the job description. Candidates meeting or exceeding this threshold with a good ATS Match Score will be marked <strong style="color:#16a34a;">Shortlist</strong>; those below will be <strong style="color:#d97706;">On Hold</strong> or <strong style="color:#dc2626;">Reject</strong>.</div>
        </div>""", unsafe_allow_html=True)
        min_skill = st.number_input(
            "Minimum matching skills required",
            min_value=1, max_value=50,
            value=int(st.session_state.min_skill_match),
            step=1, key="min_skill_input",
            help="Candidates with at least this many skills matching the JD are eligible for Shortlist."
        )
        st.session_state.min_skill_match = min_skill

        st.markdown("---")

        # --- Decision Score Thresholds (previously hardcoded) ---
        st.markdown("""<div style='color:#0f172a;font-weight:700;font-size:1rem;margin-bottom:.3rem;'>Decision Thresholds</div>
        <div style='color:#475569;font-size:.82rem;margin-bottom:.5rem;'>ATS Match Score cut-offs (combined with the minimum matching skills above) that drive the automatic Shortlist / On Hold / Reject suggestion. These are a starting point for the recruiter — the final decision is always made manually.</div>""", unsafe_allow_html=True)
        th_cols = st.columns(3)
        with th_cols[0]:
            shortlist_th = st.number_input("Shortlist at score ≥", 0, 100, int(st.session_state.shortlist_score_threshold), key="shortlist_th_input")
        with th_cols[1]:
            hold_th = st.number_input("On Hold at score ≥", 0, 100, int(st.session_state.hold_score_threshold), key="hold_th_input")
        with th_cols[2]:
            reject_th = st.number_input("Reject below score", 0, 100, int(st.session_state.reject_score_threshold), key="reject_th_input")
        st.session_state.shortlist_score_threshold = shortlist_th
        st.session_state.hold_score_threshold = hold_th
        st.session_state.reject_score_threshold = reject_th
        if not (shortlist_th >= hold_th >= reject_th):
            st.warning("Thresholds should satisfy Shortlist ≥ On Hold ≥ Reject for a sensible ordering.")

        st.markdown("---")

        # --- ATS Weights ---
        st.markdown("""<div style='color:#475569;font-size:.82rem;margin-bottom:.5rem;'>
            Fine-tune how different resume sections contribute to the ATS Match Score. Total must equal 100%.
        </div>""", unsafe_allow_html=True)
        weights = st.session_state.weights
        cols = st.columns(2)
        with cols[0]:
            for key in ["skills", "experience", "education", "projects"]:
                st.slider(
                    BREAKDOWN_LABELS[key],
                    0.0,
                    100.0,
                    float(weights[key]),
                    step=0.1,
                    format="%.1f%%",
                    key=f"weight_{key}",
                    on_change=_on_ats_weight_change,
                    args=(key,),
                )
        with cols[1]:
            for key in ["certifications", "keywords"]:
                st.slider(
                    BREAKDOWN_LABELS[key],
                    0.0,
                    100.0,
                    float(weights[key]),
                    step=0.1,
                    format="%.1f%%",
                    key=f"weight_{key}",
                    on_change=_on_ats_weight_change,
                    args=(key,),
                )
        st.caption(
            "ℹ️ Certifications and Education are scored using simplified heuristics "
            "(relevance-to-keyword matching and a coarse degree-level ranking), not a "
            "precise requirement match — treat them as a rough signal, not a verdict."
        )
        total_weight = sum(weights.values())
        if abs(total_weight - 100) > 0.5:
            st.warning("Match score weights must total exactly 100%.")
        else:
            st.success(f"Match score weights total {total_weight}%. | Min skill match: {min_skill}")

    # Step 4: Analyze Candidates
    with st.container(border=True):
        render_step_header("Step 4", "Analyze Candidates", "🚀")
        st.write("Once job descriptions and resumes are ready, run the analysis to produce ATS Match Score rankings and AI insights.")
        can_analyze = bool(st.session_state.jobs) and bool(st.session_state.resume_files)
        if not st.session_state.jobs:
            st.warning("Please upload a Job Description.")
        if not st.session_state.resume_files:
            st.warning("Please upload at least one Resume.")

        analyze_button = st.button(
            "Analyze Candidates",
            key="analyze_candidates",
            type="primary",
            disabled=not can_analyze,
            help="Run the full candidate evaluation workflow." if can_analyze else "Upload a job description and at least one resume to enable.",
        )

        if analyze_button:
            st.session_state.analysis_complete = False
            st.session_state.analysis_errors = []

            stats = {
                "processed": 0,
                "skipped": 0,
                "failed": 0
            }

            total_files = len(st.session_state.resume_files)

            # -------------------------------------------------
            # Single, consistently-indented block from here on. Previously
            # `files_to_process`, `progress_bar`, `status_text`, `start_time`
            # etc. were only assigned inside an `else:` branch but then
            # referenced again at the outer indentation level further down
            # (e.g. `if not files_to_process:` and `elapsed = ...`), which
            # would raise NameError whenever total_files == 0. Everything
            # that depends on those variables now lives inside one guarded
            # block so it is only reached when there is something to do.
            # -------------------------------------------------
            if total_files > MAX_RESUMES:
                st.error(
                    f"Cannot analyze {total_files} resumes. The fixed limit is "
                    f"{MAX_RESUMES}; remove at least {total_files - MAX_RESUMES} "
                    "resume(s) before processing."
                )
            elif total_files == 0:
                st.warning("Please upload at least one Resume.")
            else:
                # Only skip resumes that have already been successfully analyzed.
                # Matched by content hash (not filename) so a renamed copy of
                # an already-analyzed resume is correctly skipped, and a
                # different resume that happens to share a filename is not.
                existing_hashes = {
                    c.get("content_hash") or c["file_name"]
                    for c in st.session_state.candidates
                }

                files_to_process = [
                    f
                    for f in st.session_state.resume_files
                    if (f.get("content_hash") or f["name"]) not in existing_hashes
                ]

                if not files_to_process:
                    st.info(
                        "All uploaded resumes have already been analyzed. "
                        "Upload new resumes to analyze."
                    )
                    stats["skipped"] = total_files

                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    temp_candidates = []
                    errors = []

                    start_time = time.time()
                    total_to_process = len(files_to_process)

                    # -------------------------------------------------
                    # PARALLEL PROCESSING: resumes are I/O-bound (mostly
                    # waiting on LLM API calls), so processing several at
                    # once — instead of strictly one-at-a-time — cuts real
                    # wall-clock time roughly in proportion to the worker
                    # count for large batches. MAX_WORKERS is capped low
                    # deliberately to stay under typical per-account LLM
                    # rate limits; raise it if your API plan allows more
                    # concurrent requests.
                    #
                    # Streamlit UI calls (st.markdown, etc.) are not safe
                    # to make from background threads, so progress_callback
                    # is intentionally NOT passed into the threaded calls —
                    # per-file status text is skipped, and only the overall
                    # progress bar (updated here in the main thread, as each
                    # future completes) is shown during a parallel batch.
                    # Thresholds are captured up front and passed explicitly
                    # for the same reason (see evaluate_candidate docstring).
                    # -------------------------------------------------
                    MAX_WORKERS = 4
                    captured_thresholds = {
                        "min_skill_match": st.session_state.min_skill_match,
                        "shortlist_score_threshold": st.session_state.shortlist_score_threshold,
                        "hold_score_threshold": st.session_state.hold_score_threshold,
                        "reject_score_threshold": st.session_state.reject_score_threshold,
                    }
                    jobs_snapshot = st.session_state.jobs
                    weights_snapshot = st.session_state.weights
                    # Snapshots of the two other pieces of session_state
                    # evaluate_candidate needs — passed explicitly so the
                    # function never touches st.session_state from inside a
                    # worker thread (that raises "st.session_state has no
                    # attribute ..." since session state isn't available
                    # off the main thread). Results are written back into
                    # the real st.session_state.resume_cache below, in the
                    # main thread, once each future completes.
                    resume_cache_snapshot = dict(st.session_state.resume_cache)
                    candidates_snapshot = list(st.session_state.candidates)

                    status_text.markdown(f"**Analyzing {total_to_process} resume(s)** with up to {MAX_WORKERS} in parallel...")

                    completed = 0
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        future_to_entry = {
                            executor.submit(
                                evaluate_candidate,
                                entry,
                                jobs_snapshot,
                                weights_snapshot,
                                None,  # no per-file UI callback from worker threads
                                captured_thresholds,
                                resume_cache_snapshot,
                                candidates_snapshot
                            ): entry
                            for entry in files_to_process
                        }

                        for future in as_completed(future_to_entry):
                            entry = future_to_entry[future]
                            filename = entry["name"]

                            try:
                                result = future.result()
                            except Exception as e:
                                # IMPORTANT: a failure in one resume must
                                # never stop the rest of the batch.
                                result = {
                                    "error": (
                                        f"Unexpected error while analyzing "
                                        f"{filename}: {str(e)}"
                                    )
                                }

                            completed += 1
                            progress_bar.progress(completed / total_to_process)

                            if result and "error" in result:
                                errors.append(result["error"])
                                stats["failed"] += 1
                                status_text.markdown(
                                    f"❌ `{filename}` failed ({completed}/{total_to_process})"
                                )
                            elif result:
                                result["id"] = (
                                    len(st.session_state.candidates)
                                    + len(temp_candidates)
                                    + 1
                                )
                                temp_candidates.append(result)
                                stats["processed"] += 1
                                # Store into the real cache here, on the main
                                # thread — evaluate_candidate skipped this
                                # itself because it was called with an
                                # explicit resume_cache snapshot (i.e. it
                                # knew it might be running off-thread).
                                cache_key = compute_cache_key(
                                    entry["text"], jobs_snapshot, GEMINI_MODEL, SCORING_LOGIC_VERSION
                                )
                                st.session_state.resume_cache[cache_key] = result
                                status_text.markdown(
                                    f"✅ `{filename}` — ATS Match Score: {result['ats_score']:.1f}% "
                                    f"({completed}/{total_to_process})"
                                )
                            else:
                                errors.append(f"Evaluation returned no result for {filename}.")
                                stats["failed"] += 1
                                status_text.markdown(
                                    f"❌ `{filename}` — no result ({completed}/{total_to_process})"
                                )

                    elapsed = round(time.time() - start_time, 1)

                    progress_bar.empty()
                    status_text.empty()

                    # Persist processing information across reruns.
                    st.session_state.processing_stats = stats
                    st.session_state.analysis_errors = errors

                    # Add every successfully analyzed candidate.
                    if temp_candidates:
                        st.session_state.candidates.extend(
                            temp_candidates
                        )

                        st.session_state.analysis_complete = True

                        st.session_state.analysis_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "count": len(temp_candidates),
                            "elapsed": elapsed
                        })

                    # Always rerun so successful candidates and
                    # persistent errors are displayed correctly.
                    st.session_state.active_section = "Dashboard"

                    st.rerun()

    # Step 5: Candidate Evaluation Results
    with st.container(border=True):
        render_step_header("Step 5", "Candidate Evaluation Results", "🏆")
        if st.session_state.get("analysis_errors"):
            st.warning("⚠️ Some resumes could not be analyzed.")

            for error in st.session_state.analysis_errors:
                st.error(error)
        if not st.session_state.analysis_complete or not st.session_state.candidates:
            st.markdown("<div class='empty-state-card'>Upload a Job Description and Candidate Resumes, then click 'Analyze Candidates' to generate ATS Match Scores and AI insights.</div>", unsafe_allow_html=True)
        else:
            candidates = sorted(st.session_state.candidates, key=lambda x: x["ats_score"], reverse=True)

            # Build HTML ranking table
            min_req = st.session_state.get("min_skill_match", 5)
            result_rows = ""
            for i, c in enumerate(candidates, 1):
                sc = c["ats_score"]
                sc_color = "#22c55e" if sc >= 70 else "#f59e0b" if sc >= 40 else "#ef4444"
                match = c.get("match_result", {})
                matched_count = len(match.get("matched_skills", []))
                total_required = required_skill_total(match)
                matched_preferred = len(match.get("preferred_matched_skills", []))
                total_preferred = preferred_skill_total(match)
                preferred_missing = unresolved_skill_gaps(
                    match.get("preferred_matched_skills", []),
                    match.get("preferred_missing_skills", []),
                )
                match_color = "#22c55e" if matched_count >= min_req else "#ef4444"
                missing_required = skill_gap_html(c, limit=4)
                dec = c.get("recruiter_decision", "Not Decided")
                dec_cls = "badge-green" if dec == "Shortlist" else "badge-red" if dec == "Reject" else "badge-yellow"
                result_rows += f"""<tr>
                    <td style='color:#64748b;font-weight:700;'>#{i}</td>
                    <td><strong>{c['name']}</strong></td>
                    <td><span class='score-pill' style='background:rgba({",".join(str(int(sc_color.lstrip("#")[j:j+2],16)) for j in (0,2,4))},.15);color:{sc_color};'>{sc}%</span></td>
                    <td style='color:{match_color};font-weight:700;'>{matched_count}/{total_required}</td>
                    <td style='color:#0891b2;font-weight:700;'>{matched_preferred}/{total_preferred}</td>
                    <td style='font-size:.78rem;'>{missing_required}</td>
                    <td style='font-size:.78rem;'>{", ".join(preferred_missing) or "None"}</td>
                    <td><span class='badge {dec_cls}'>{dec}</span></td>
                </tr>"""

            st.markdown(f"""<div class='chart-card'>
                <div class='chart-title'>Candidate Ranking <span style='color:#64748b;font-size:.8rem;font-weight:400;'>(Min skill match: {min_req})</span></div>
                <table class='rank-table'>
                    <thead><tr><th>#</th><th>Candidate</th><th>ATS Match Score</th><th>Matched Required</th><th>Matched Preferred</th><th>Missing Required</th><th>Missing Preferred</th><th>Decision</th></tr></thead>
                    <tbody>{result_rows}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)

            # Top candidate summary card
            top = candidates[0]
            top_sc = top["ats_score"]
            strengths_html = "".join(f"<div style='color:#16a34a;font-size:.85rem;'>+ {s}</div>" for s in top["ai_evaluation"].get("strengths", [])[:4])
            weaknesses_html = "".join(f"<div style='color:#dc2626;font-size:.85rem;'>- {w}</div>" for w in top["ai_evaluation"].get("weaknesses", [])[:4])
            reason = top["ai_recommendation"].get("reason", "")

            top_match_result = top.get("match_result", {})
            top_matched_count = len(top_match_result.get("matched_skills", []))
            top_required_total = required_skill_total(top_match_result)
            top_preferred_count = len(top_match_result.get("preferred_matched_skills", []))
            top_preferred_total = preferred_skill_total(top_match_result)
            top_required_missing = candidate_skill_gaps(top)
            top_preferred_missing = unresolved_skill_gaps(
                top_match_result.get("preferred_matched_skills", []),
                top_match_result.get("preferred_missing_skills", []),
            )
            top_decision = top.get("recruiter_decision", "Not Decided")
            st.markdown(f"""<div class='chart-card'>
                <div class='chart-title'>Top Candidate — {top['name']}</div>
                <div class='stat-row'>
                    <div class='stat-mini'><div class='s-val' style='color:#16a34a;'>{top_sc}%</div><div class='s-lbl'>ATS Match Score</div></div>
                    <div class='stat-mini'><div class='s-val' style='color:#2563eb;'>{top_matched_count}/{top_required_total}</div><div class='s-lbl'>Matched Required Skills</div></div>
                    <div class='stat-mini'><div class='s-val' style='color:#0891b2;'>{top_preferred_count}/{top_preferred_total}</div><div class='s-lbl'>Matched Preferred Skills</div></div>
                    <div class='stat-mini'><div class='s-val' style='color:#7c3aed;'>{top['best_role']}</div><div class='s-lbl'>Best Role</div></div>
                    <div class='stat-mini'><div class='s-val' style='color:{"#16a34a" if top_decision == "Shortlist" else "#d97706" if top_decision == "On Hold" else "#dc2626"};'>{top_decision}</div><div class='s-lbl'>Decision</div></div>
                </div>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:.8rem;'>
                    <div><div style='color:#64748b;font-size:.78rem;text-transform:uppercase;margin-bottom:.4rem;'>Strengths</div>{strengths_html}</div>
                    <div><div style='color:#64748b;font-size:.78rem;text-transform:uppercase;margin-bottom:.4rem;'>Weaknesses</div>{weaknesses_html}</div>
                </div>
                <div style='margin-top:.8rem;color:#64748b;font-size:.78rem;text-transform:uppercase;'>Missing Required Skills</div>
                <div style='color:#d97706;font-size:.85rem;'>{", ".join(top_required_missing) or "None"}</div>
                <div style='margin-top:.8rem;color:#64748b;font-size:.78rem;text-transform:uppercase;'>Missing Preferred Skills</div>
                <div style='color:#d97706;font-size:.85rem;'>{", ".join(top_preferred_missing) or "None"}</div>
                <div style='margin-top:.8rem;color:#64748b;font-size:.78rem;text-transform:uppercase;'>AI Recommendation</div>
                <div style='color:#334155;font-size:.85rem;'>{reason}</div>
            </div>""", unsafe_allow_html=True)

            # Keep CSV download
            df = pd.DataFrame([{
                "Name": c["name"], "ATS Match Score": c["ats_score"],
                "Matched Required Skills": len(c.get("match_result", {}).get("matched_skills", [])),
                "Required Skills Total": required_skill_total(c.get("match_result", {})),
                "Matched Preferred Skills": len(c.get("match_result", {}).get("preferred_matched_skills", [])),
                "Preferred Skills Total": preferred_skill_total(c.get("match_result", {})),
                "Matched Required Skill Names": ", ".join(c.get("match_result", {}).get("matched_skills", [])),
                "Missing Required Skills": ", ".join(candidate_skill_gaps(c)),
                "Matched Preferred Skill Names": ", ".join(c.get("match_result", {}).get("preferred_matched_skills", [])),
                "Missing Preferred Skills": ", ".join(unresolved_skill_gaps(
                    c.get("match_result", {}).get("preferred_matched_skills", []),
                    c.get("match_result", {}).get("preferred_missing_skills", []),
                )),
                "Related Skills Only": ", ".join(candidate_related_skills(c)),
                "Could Not Verify": ", ".join(candidate_unverified_skills(c)),
                "Decision": c.get("recruiter_decision", "Not Decided")
            } for c in candidates])
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Report", csv, "candidate_evaluation_report.csv", "text/csv")
