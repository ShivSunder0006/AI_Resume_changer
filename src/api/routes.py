"""
FastAPI routes for the Job Application Agent API.
"""

from __future__ import annotations

import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from src.api.schemas import (
    TailorResponse,
    HealthResponse,
    ValidationReport,
    EvaluationScores,
    SessionInfo,
)
from src.agents.graph import run_agent
from src.memory.store import MemoryStore
from src.config.settings import get_settings

router = APIRouter()
memory = MemoryStore()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and configuration status."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        groq_configured=bool(settings.GROQ_API_KEY),
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )


@router.post("/tailor", response_model=TailorResponse)
async def tailor_resume(
    resume: UploadFile = File(..., description="Resume PDF file"),
    job_description: str = Form(..., description="Job description text"),
    urls: str = Form(None, description="Optional GitHub or Portfolio URLs"),
):
    """
    Tailor a resume PDF to match a job description.

    Upload a PDF resume and provide the job description text.
    Returns the path to the tailored PDF along with validation
    and evaluation results.
    """
    # Validate file type
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    if len(job_description.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description must be at least 50 characters",
        )

    session_id = uuid.uuid4().hex

    try:
        # Save uploaded file
        settings = get_settings()
        upload_dir = settings.output_path / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_path = upload_dir / f"{session_id}_{resume.filename}"

        with open(upload_path, "wb") as f:
            content = await resume.read()
            f.write(content)

        logger.info(
            f"Session {session_id}: uploaded {resume.filename} "
            f"({len(content)} bytes)"
        )

        # Create session
        memory.create_session(
            session_id=session_id,
            resume_path=str(upload_path),
            jd=job_description,
        )

        # Run the agent
        memory.update_session(session_id, status="processing")
        final_state = run_agent(
            resume_pdf_path=str(upload_path),
            job_description=job_description,
            external_urls=urls,
        )

        # Build response
        error = final_state.get("error")
        output_path = final_state.get("output_pdf_path")
        validation = final_state.get("validation_result")
        evaluation = final_state.get("evaluation_scores")

        # Update session
        memory.update_session(
            session_id,
            status="completed" if output_path and not error else "failed",
            output_path=output_path,
            validation_result=validation,
            evaluation_scores=evaluation,
        )

        response = TailorResponse(
            success=bool(output_path and not error),
            session_id=session_id,
            output_pdf_path=output_path,
            validation=ValidationReport(**validation) if validation else None,
            evaluation=EvaluationScores(**{
                k: v for k, v in (evaluation or {}).items()
                if k in EvaluationScores.model_fields
            }) if evaluation else None,
            modifications_count=final_state.get("modifications_count", 0),
            llm_provider=final_state.get("llm_provider_used"),
            error=error,
        )

        return response

    except Exception as e:
        logger.error(f"Session {session_id} failed: {e}")
        memory.update_session(session_id, status="error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine/{session_id}", response_model=TailorResponse)
async def refine_resume(session_id: str, prompt: str = Form(...)):
    """Re-run tailoring with user conversational feedback."""
    session = memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        # Load state from memory - Note: Currently MemoryStore only stores summary.
        # For a full refine, we would need to persist the full LangGraph state.
        # Since we don't have full state checkpointing, we will re-run `run_agent` 
        # but pass the prompt in via a hack, or we construct the full state.
        
        from src.agents.graph import run_agent
        
        # Currently, since memory only stores original inputs in our SQLite MVP:
        resume_path = session.get("resume_path")
        jd = session.get("job_description")
        
        if not resume_path or not jd:
            raise HTTPException(status_code=400, detail="Incomplete session data to refine")
        
        # Re-run agent but pass the feedback
        final_state = run_agent(
            resume_pdf_path=resume_path,
            job_description=jd,
            user_feedback=prompt,
        )
        
        output_path = final_state.get("output_pdf_path")
        error = final_state.get("error")
        validation = final_state.get("validation_result")
        evaluation = final_state.get("evaluation_scores")
        
        memory.update_session(
            session_id,
            status="completed" if output_path and not error else "failed",
            output_path=output_path,
        )
        
        return TailorResponse(
            success=bool(output_path and not error),
            session_id=session_id,
            output_pdf_path=output_path,
            validation=ValidationReport(**validation) if validation else None,
            evaluation=EvaluationScores(**{k:v for k,v in (evaluation or {}).items() if k in EvaluationScores.model_fields}) if evaluation else None,
            modifications_count=final_state.get("modifications_count", 0),
            error=error,
        )
        
    except Exception as e:
        logger.error(f"Refine {session_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{session_id}")
async def download_tailored_pdf(session_id: str):
    """Download the tailored PDF for a given session."""
    session = memory.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    output_path = session.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Tailored PDF not found for this session",
        )

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=f"tailored_resume_{session_id[:8]}.pdf",
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """List recent tailoring sessions."""
    sessions = memory.list_sessions()
    return [SessionInfo(**s) for s in sessions]


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get details of a specific session."""
    session = memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
