"""
LangGraph graph definition — the core agentic workflow.

Flow:
  START → parse_resume → analyze_jd → tailor_resume → reconstruct_pdf → validate
                                                                          ↓
                                                                Pass → END
                                                                Fail → tailor_resume (max 2 retries)
"""

from loguru import logger
from langgraph.graph import StateGraph, END

from src.agents.state import AgentState
from src.agents.nodes.parse_resume import parse_resume_node
from src.agents.nodes.analyze_jd import analyze_jd_node
from src.agents.nodes.tailor_resume import tailor_resume_node
from src.agents.nodes.reconstruct_pdf import reconstruct_pdf_node
from src.agents.nodes.validate import validate_node
from src.evaluation.evaluator import evaluate_result


# ── Conditional Edge: Validation Router ───────────────────

def validation_router(state: AgentState) -> str:
    """Decide whether to accept the result or retry tailoring."""
    validation = state.get("validation_result", {})
    retry_count = state.get("retry_count", 0)
    error = state.get("error")

    # If there's a hard error, end immediately
    if error:
        logger.error(f"Pipeline error, ending: {error}")
        return "evaluate"

    # Check validation
    is_preserved = validation.get("format_preserved", False)
    score = validation.get("score", 0)

    if is_preserved or score >= 0.6:
        logger.info(f"Validation passed (score={score}), proceeding to evaluation")
        return "evaluate"

    # Retry if under limit
    if retry_count < 2:
        logger.warning(
            f"Validation failed (score={score}), retrying "
            f"(attempt {retry_count + 1}/2)"
        )
        return "retry_tailor"

    logger.warning("Max retries reached, accepting current result")
    return "evaluate"


def increment_retry(state: AgentState) -> dict:
    """Increment retry counter before re-tailoring."""
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "error": None,  # Clear previous error
    }


def evaluate_node(state: AgentState) -> dict:
    """Run evaluation scoring on the final result."""
    logger.info("=== NODE: evaluate ===")

    try:
        resume_text = state.get("resume_text", "")
        jd_text = state.get("job_description", "")
        jd_analysis = state.get("jd_analysis", {})
        output_path = state.get("output_pdf_path")
        validation = state.get("validation_result", {})

        scores = evaluate_result(
            original_resume_text=resume_text,
            job_description=jd_text,
            jd_analysis=jd_analysis,
            tailored_pdf_path=output_path,
            validation_result=validation,
        )

        return {
            "evaluation_scores": scores,
            "current_step": "evaluate_complete",
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            "evaluation_scores": {"error": str(e)},
            "current_step": "evaluate_error",
        }


# ── Error checker edges ──────────────────────────────────

def check_parse_error(state: AgentState) -> str:
    if state.get("error"):
        return "evaluate"
    return "analyze_jd"


def check_jd_error(state: AgentState) -> str:
    if state.get("error"):
        return "evaluate"
    return "tailor_resume"


def check_tailor_error(state: AgentState) -> str:
    if state.get("error"):
        return "evaluate"
    return "reconstruct_pdf"


def check_reconstruct_error(state: AgentState) -> str:
    if state.get("error"):
        return "evaluate"
    return "validate"


# ── Build Graph ───────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    logger.info("Building LangGraph workflow...")

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("parse_resume", parse_resume_node)
    workflow.add_node("analyze_jd", analyze_jd_node)
    workflow.add_node("tailor_resume", tailor_resume_node)
    workflow.add_node("reconstruct_pdf", reconstruct_pdf_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("increment_retry", increment_retry)
    workflow.add_node("evaluate", evaluate_node)

    # Set entry point
    workflow.set_entry_point("parse_resume")

    # Add edges with error checking
    workflow.add_conditional_edges("parse_resume", check_parse_error)
    workflow.add_conditional_edges("analyze_jd", check_jd_error)
    workflow.add_conditional_edges("tailor_resume", check_tailor_error)
    workflow.add_conditional_edges("reconstruct_pdf", check_reconstruct_error)

    # Validation → conditional (pass/retry)
    workflow.add_conditional_edges(
        "validate",
        validation_router,
        {
            "evaluate": "evaluate",
            "retry_tailor": "increment_retry",
        },
    )

    # Retry loop
    workflow.add_edge("increment_retry", "tailor_resume")

    # Evaluate → END
    workflow.add_edge("evaluate", END)

    graph = workflow.compile()
    logger.info("LangGraph workflow compiled successfully")

    return graph


def run_agent(
    resume_pdf_path: str,
    job_description: str,
    external_urls: str = None,
    user_feedback: str = None,
) -> AgentState:
    """
    Run the full resume tailoring pipeline.

    Args:
        resume_pdf_path: Path to the original resume PDF
        job_description: Full text of the job description
        external_urls: Links to Github/Portfolio

    Returns:
        Final AgentState with all results
    """
    logger.info("=" * 60)
    logger.info("STARTING JOB APPLICATION AGENT")
    logger.info("=" * 60)

    graph = build_graph()

    initial_state: AgentState = {
        "resume_pdf_path": resume_pdf_path,
        "job_description": job_description,
        "external_urls": external_urls,
        "user_feedback": user_feedback,
        "resume_layout": None,
        "resume_text": None,
        "resume_sections": None,
        "jd_analysis": None,
        "tailoring_instructions": None,
        "modifications_count": 0,
        "output_pdf_path": None,
        "reconstruction_stats": None,
        "validation_result": None,
        "evaluation_scores": None,
        "error": None,
        "retry_count": 0,
        "current_step": "start",
        "llm_provider_used": None,
        "messages": [],
    }

    # Run the graph
    final_state = graph.invoke(initial_state)

    logger.info("=" * 60)
    logger.info(f"AGENT COMPLETE — step: {final_state.get('current_step')}")
    if final_state.get("output_pdf_path"):
        logger.info(f"Output: {final_state['output_pdf_path']}")
    if final_state.get("error"):
        logger.error(f"Error: {final_state['error']}")
    logger.info("=" * 60)

    return final_state

def run_refine_agent(state: AgentState, user_feedback: str) -> AgentState:
    """
    Re-run the agent starting from tailor_resume with user feedback.
    """
    logger.info("=" * 60)
    logger.info(f"STARTING REFINE AGENT: {user_feedback}")
    logger.info("=" * 60)
    
    state["user_feedback"] = user_feedback
    state["retry_count"] = 0
    state["error"] = None
    
    # We must explicitly re-run the nodes since we don't have persistent checkpoints
    state = tailor_resume_node(state)
    if state.get("error"): return state
    
    state = reconstruct_pdf_node(state)
    if state.get("error"): return state
    
    state = validate_node(state)
    
    # Simple validation router logic
    validation = state.get("validation_result", {})
    if validation.get("format_preserved", False) or validation.get("score", 0) >= 0.6:
        state = evaluate_node(state)
    else:
        logger.warning("Refined validation failed, returning as is.")
        
    return state
