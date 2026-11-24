"""Pydantic schemas for structured LLM output."""

import re
from typing import List

from pydantic import BaseModel, Field, field_validator


# -------------------------------------------------
# PYDANTIC MODELS
# -------------------------------------------------
class ResumeData(BaseModel):
    name: str = Field(default="Unknown")
    email: str = Field(default="")
    phone: str = Field(default="")
    skills: List[str] = Field(default_factory=list)
    experience_years: float = Field(default=0.0)
    # Kept separate from experience_years rather than folded into it — an
    # internship is real signal for a candidate but is not "professional
    # work experience" and must never inflate the experience score or the
    # years shown as a candidate's professional tenure.
    internship_experience_years: float = Field(default=0.0)
    education: str = Field(default="Not specified")
    education_level: str = Field(default="")
    projects: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

    @field_validator('experience_years', 'internship_experience_years', mode='before')
    @classmethod
    def validate_experience(cls, v):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            return float(match.group(1)) if match else 0.0
        return 0.0

    @field_validator('skills', 'projects', 'certifications', 'keywords', mode='before')
    @classmethod
    def validate_lists(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        if isinstance(v, list):
            return v
        return []


class JDData(BaseModel):
    role: str = Field(default="Unknown Role")
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    min_experience: float = Field(default=0.0)
    education_requirement: str = Field(default="")
    keywords: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)

    @field_validator('min_experience', mode='before')
    @classmethod
    def validate_min_experience(cls, v):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            return float(match.group(1)) if match else 0.0
        return 0.0

    @field_validator('required_skills', 'preferred_skills', 'keywords', 'responsibilities', mode='before')
    @classmethod
    def validate_lists(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        if isinstance(v, list):
            return v
        return []


class ATSBreakdown(BaseModel):
    skills: float = Field(default=0.0, ge=0, le=100)
    experience: float = Field(default=0.0, ge=0, le=100)
    education: float = Field(default=0.0, ge=0, le=100)
    projects: float = Field(default=0.0, ge=0, le=100)
    certifications: float = Field(default=0.0, ge=0, le=100)
    keywords: float = Field(default=0.0, ge=0, le=100)

    @field_validator('*', mode='before')
    @classmethod
    def validate_scores(cls, v):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            return min(100, max(0, float(match.group(1)))) if match else 0.0
        return 0.0


class MatchResult(BaseModel):
    skill_match_score: float = Field(default=0.0, ge=0, le=100)
    experience_match_score: float = Field(default=0.0, ge=0, le=100)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

    @field_validator('skill_match_score', 'experience_match_score', mode='before')
    @classmethod
    def validate_scores(cls, v):
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            return min(100, max(0, float(match.group(1)))) if match else 0.0
        return 0.0

    @field_validator('matched_skills', 'missing_skills', mode='before')
    @classmethod
    def validate_lists(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        if isinstance(v, list):
            return v
        return []



class AIEvaluation(BaseModel):
    summary: str = Field(default="")
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    skill_gap_analysis: str = Field(default="")
    projects_analysis: str = Field(default="")
    certifications_analysis: str = Field(default="")

    @field_validator('matched_skills', 'missing_skills', 'strengths', 'weaknesses', mode='before')
    @classmethod
    def validate_lists(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        if isinstance(v, list):
            return v
        return []


class AIRecommendation(BaseModel):
    decision: str = Field(default="On Hold")
    confidence: float = Field(default=0.0, ge=0, le=100)
    reason: str = Field(default="")


class SkillMapping(BaseModel):
    """One job skill checked against the resume (see ai/skill_mapper.py)."""
    jd_skill: str = Field(default="")
    verdict: str = Field(default="none")  # match | related | none
    resume_skill: str = Field(default="")
    evidence: str = Field(default="")


class SkillMappingResult(BaseModel):
    mappings: List[SkillMapping] = Field(default_factory=list)
