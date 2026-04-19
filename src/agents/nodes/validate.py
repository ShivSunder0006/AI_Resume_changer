"""
Node: Validate the reconstructed PDF for format preservation.
"""

from loguru import logger
from langchain_core.messages import AIMessage

from src.agents.state import AgentState
from src.pdf.validator import validate_pdf


def validate_node(state: AgentState) -> dict:
    """
    Run format preservation validation.

    If validation fails and retries remain, the graph will loop
    back to the tailoring step.
    """
    logger.info("=== NODE: validate ===")

    try:
        original_path = state["resume_pdf_path"]
        output_path = state.get("output_pdf_path")

        if not output_path:
            return {
                "error": "No output PDF to validate",
                "current_step": "validate_error",
                "messages": [AIMessage(content="Error: No output PDF found")],
            }

        # Run validation
        result = validate_pdf(original_path, output_path)
        result_dict = result.to_dict()

        logger.info(
            f"Validation: preserved={result.format_preserved}, "
            f"score={result.score:.2f}"
        )

        return {
            "validation_result": result_dict,
            "current_step": "validate_complete",
            "messages": [
                AIMessage(
                    content=f"Validation: format_preserved={result.format_preserved}, "
                    f"score={result.score:.2f}, "
                    f"issues={len(result.issues)}"
                )
            ],
        }

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "validation_result": {
                "format_preserved": False,
                "score": 0.0,
                "issues": [f"Validation error: {str(e)}"],
            },
            "current_step": "validate_error",
            "messages": [AIMessage(content=f"Validation error: {e}")],
        }
