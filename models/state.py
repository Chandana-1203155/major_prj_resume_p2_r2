"""LangGraph state definition."""

from typing import TypedDict


# -------------------------------------------------
# STATE
# -------------------------------------------------
class HiringState(TypedDict):
    resume_text: str
    jd_text: str
    resume_data: dict
    jd_data: dict
    match_result: dict
    ats_breakdown: dict
    ai_evaluation: dict
    ai_recommendation: dict
