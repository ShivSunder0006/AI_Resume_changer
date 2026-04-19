"""
LangGraph shared state for the Job Application Agent.
"""

from __future__ import annotations

from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """
    Shared state that flows through every node in the LangGraph.

    All nodes read from and write to this state.
    """
    # ── Inputs ────────────────────────────────────────────
    resume_pdf_path: str
    job_description: str
    external_urls: str | None
    user_feedback: str | None

    # ── Parsed Data ───────────────────────────────────────
    resume_layout: dict | None          # Serialised ResumeLayout
    resume_text: str | None             # Full extracted text
    resume_sections: list[dict] | None  # Detected sections

    # ── JD Analysis ───────────────────────────────────────
    jd_analysis: dict | None            # Extracted requirements

    # ── Tailoring Output ──────────────────────────────────
    tailoring_instructions: list[dict] | None  # Per-span modifications
    modifications_count: int

    # ── Reconstruction ────────────────────────────────────
    output_pdf_path: str | None
    reconstruction_stats: dict | None

    # ── Validation ────────────────────────────────────────
    validation_result: dict | None

    # ── Evaluation ────────────────────────────────────────
    evaluation_scores: dict | None

    # ── Control Flow ──────────────────────────────────────
    error: str | None
    retry_count: int
    current_step: str
    llm_provider_used: str | None

    # ── Messages (for LangGraph tracing) ──────────────────
    messages: Annotated[list[BaseMessage], operator.add]
