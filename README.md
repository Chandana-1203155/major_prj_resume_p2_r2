# HireGenAI (modular)

AI hiring-intelligence platform, refactored from a single `app.py` into modules.
Gemini is used through LangChain/LangGraph. The ATS Match Score weights Skills (40%),
Experience (20%), Education (20%), Projects (8%), Certifications (6%), and Keywords (6%).
Profile Completeness is not part of ATS scoring.
Candidate Evaluation accepts and processes at most four resumes per batch.
All data lives in `st.session_state` only (nothing is persisted).

## Run
```bash
pip install -r requirements.txt
# Set GEMINI_API_KEY in .env to your key from Google AI Studio
streamlit run app.py
```

## Layout
| Path | Responsibility |
|---|---|
| `app.py` | Entry point: page config, API-key check, styles, session init, sidebar + routing |
| `config.py` | `.env` loading, model name, limits, `SCORING_LOGIC_VERSION`, `BREAKDOWN_LABELS` |
| `models/` | Pydantic schemas (`schemas.py`), LangGraph `HiringState` (`state.py`) |
| `state/session.py` | `init_session`, `assign_job_id` |
| `ai/llm.py` | Lazy Gemini client + `safe_llm_invoke` |
| `ai/security.py` | Prompt-injection detection / untrusted-data wrapping |
| `ai/agents.py` | `resume_parser`, `jd_analyzer`, `ai_evaluation_agent`, `ai_recommendation_agent` |
| `ai/graphs.py` | Compiled LangGraph graphs |
| `parsing/` | PDF/DOCX/TXT/ZIP extraction (`file_extraction.py`), optional OCR (`ocr.py`) |
| `scoring/` | Deterministic scoring (`deterministic.py`), ATS score / status / weights (`ats.py`) |
| `services/candidate_pipeline.py` | `evaluate_candidate`, `compute_cache_key` |
| `services/decisions.py` | AI-vs-recruiter decision logic, decision history, single/bulk apply (no UI) |
| `utils/hashing.py` | Content / resume hashes |
| `ui/` | `styles.py`, `helpers.py`, `components.py`, `decision_lists.py`, and one file per page in `ui/pages/` |

The Gemini client is created lazily through `ai.llm.get_llm()`. Set `GEMINI_API_KEY` in
`.env` and optionally choose a model with `GEMINI_MODEL` (defaults to `gemini-3.5-flash-lite`).
The four agents use the same `get_llm()` client and preserve their structured-output flow.

## Decision lists (Shortlist Workspace → "Decision Lists")
Candidates are listed by their current recruiter decision (Shortlisted / On Hold / Rejected / Not Decided).
Moving a candidate's decision moves them to the matching list automatically.

* **Apply AI recommendations to all** in a list, or **to selected** (checkboxes) - both ask for confirmation first and show a preview.
* **Use AI** button beside each candidate applies only that candidate's own AI recommendation.
* **Set decision** selector on every candidate (works from any list).
* **Shortlist Selected / On Hold Selected / Reject Selected** bulk buttons - confirmation required (bulk reject shows an error-level warning).
* You can mix: accept the AI for some candidates and override others in the same list.

**AI recommendation vs. recruiter decision:** the AI recommendation (`candidate["ai_recommendation"]`) is never modified.
Every decision change is appended to `st.session_state.decision_history` with: candidate, from -> to, whether it was
*accepted from the AI* or *manual* (and whether it overrides the AI), what the AI recommended at that time,
the action that caused it, and a timestamp. The existing Save buttons (Candidates page, Shortlist Workspace) and the
"Shortlist all qualifying / top N" buttons keep working exactly as before and now write to the same history.
History is in-memory only (cleared by *Reset All Data*), like everything else in the app.




Steps to run the prj;
1.Create and activate a virtual environment:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

2.Install dependencies:
pip install -r requirements.txt

3. Set your Gemini key in `.env`:
`GEMINI_API_KEY=your-own-gemini-api-key`
Replace the placeholder with your key from Google AI Studio.

4.Start the app:
streamlit run app.py

note:If streamlit is not recognized, use:
python -m streamlit run app.py

Then open the local URL it prints, usually:
http://localhost:8501
