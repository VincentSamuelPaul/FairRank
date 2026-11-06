"""Pydantic schemas for everything the LLM returns. LLM output is never trusted unparsed."""
from pydantic import BaseModel, Field


class ExtractedCriterion(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    is_must_have: bool = False


class JDExtraction(BaseModel):
    """What the AI pulls out of a pasted job description (JD intake)."""

    title: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=120)
    exp_min_years: float | None = Field(default=None, ge=0, le=60)
    exp_max_years: float | None = Field(default=None, ge=0, le=60)
    notice_max_days: int | None = Field(default=None, ge=0, le=365)
    ctc_min: float | None = Field(default=None, ge=0)  # INR per year (A12)
    ctc_max: float | None = Field(default=None, ge=0)
    criteria: list[ExtractedCriterion] = Field(min_length=1, max_length=15)


class CriterionResult(BaseModel):
    criterion_id: int
    points: int = Field(ge=0, le=100)
    confidence: float = Field(default=1.0, ge=0, le=1)
    quote: str = Field(default="", max_length=600)
    rationale: str = Field(default="", max_length=500)


class CVScoring(BaseModel):
    results: list[CriterionResult]
