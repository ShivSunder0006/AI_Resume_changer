"""
Pydantic schemas for API request/response models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────

class TailorRequest(BaseModel):
    """Request body for the tailor endpoint (when using JSON)."""
    job_description: str = Field(
        ...,
        description="Full text of the job description",
        min_length=50,
    )


# ── Responses ─────────────────────────────────────────────

class ValidationReport(BaseModel):
    format_preserved: bool = False
    score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)


class EvaluationScores(BaseModel):
    keyword_match: float | None = None
    keywords_found: int | None = None
    keywords_total: int | None = None
    ats_similarity: float | None = None
    original_ats_similarity: float | None = None
    ats_improvement: float | None = None
    content_integrity: float | None = None
    format_score: float | None = None
    format_preserved: bool | None = None
    overall: float | None = None


class TailorResponse(BaseModel):
    """Response from the tailor endpoint."""
    success: bool
    session_id: str | None = None
    output_pdf_path: str | None = None
    validation: ValidationReport | None = None
    evaluation: EvaluationScores | None = None
    modifications_count: int = 0
    llm_provider: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    groq_configured: bool = False
    gemini_configured: bool = False


class SessionInfo(BaseModel):
    id: str
    created_at: str
    status: str
