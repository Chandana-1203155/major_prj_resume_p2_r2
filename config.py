"""Central configuration: environment, model name, limits and shared constants."""

import os

from dotenv import load_dotenv


# Load .env first so every os.getenv() below sees it.
load_dotenv()

# Model is configurable via environment variable so it can be
# swapped without code changes if the model changes.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Bumping this invalidates the resume/JD evaluation cache whenever the
# scoring logic, prompts, or schema change, so stale results are never
# silently reused across app versions.
#
# v5: skill matching is now general (stop-word/plural/bracket-acronym
# normalization) plus a verified LLM skill-equivalence check; results gain
# related_skills / unverified_skills.
# v4: deterministic skill matching now uses a controlled, expanded alias map.
# v3: resume_parser's prompt was tightened to strictly separate professional
# work experience from internships/academic projects/training/certifications
# (previously these could leak into experience_years, e.g. a candidate with
# no job history showing a nonzero "0.33 years" derived from an internship
# or coursework). Bumped so every previously-cached candidate is re-extracted
# under the corrected prompt instead of continuing to serve the old,
# incorrect experience_years from cache.
SCORING_LOGIC_VERSION = "v6-six-component-ats-score"

# Fixed candidate upload and evaluation cap.
MAX_RESUMES = 4

# -------------------------------------------------
# FILE EXTRACTION LIMITS
# -------------------------------------------------
OCR_MIN_TEXT_CHARS = 40  # below this, a PDF is treated as "no extractable text" and OCR is tried
OCR_MAX_PAGES = 12       # cap OCR cost/time on very long scanned documents

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024      # 10 MB per individual resume/JD file
MAX_ZIP_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024  # 100 MB extracted, across the whole ZIP
MAX_ZIP_ENTRIES = 200                        # cap file count to avoid zip-bomb-style entry floods

# -------------------------------------------------
# ATS SCORE
# -------------------------------------------------
DEFAULT_ATS_WEIGHTS = {
    "skills": 40,
    "experience": 20,
    "education": 20,
    "projects": 8,
    "certifications": 6,
    "keywords": 6,
}

BREAKDOWN_LABELS = {
    "skills": "Skills",
    "experience": "Experience",
    "education": "Education",
    "projects": "Projects",
    "certifications": "Certifications",
    "keywords": "Keywords",
}
