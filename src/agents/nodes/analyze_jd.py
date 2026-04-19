"""
Node: Analyze Job Description to extract structured requirements.
"""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.agents.state import AgentState
from src.agents.prompts.analyze import JD_ANALYSIS_SYSTEM, JD_ANALYSIS_HUMAN
from src.llm.router import LLMRouter


def analyze_jd_node(state: AgentState) -> dict:
    """Extract structured requirements from the job description."""
    logger.info("=== NODE: analyze_jd ===")

    try:
        jd_text = state["job_description"]

        if not jd_text or not jd_text.strip():
            return {
                "error": "Job description is empty",
                "current_step": "analyze_jd_error",
                "messages": [AIMessage(content="Error: Job description is empty")],
            }

        # Build messages
        messages = [
            SystemMessage(content=JD_ANALYSIS_SYSTEM),
            HumanMessage(content=JD_ANALYSIS_HUMAN.format(job_description=jd_text)),
        ]

        # Call LLM via router
        router = LLMRouter()
        response = router.invoke(messages)

        # Parse JSON response
        response_text = response.content

        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        jd_analysis = json.loads(json_text.strip())

        logger.info(
            f"JD Analysis: {jd_analysis.get('job_title', 'N/A')} at "
            f"{jd_analysis.get('company', 'N/A')}, "
            f"{len(jd_analysis.get('keywords', []))} keywords extracted"
        )

        return {
            "jd_analysis": jd_analysis,
            "current_step": "analyze_jd_complete",
            "llm_provider_used": router.last_provider,
            "messages": [
                AIMessage(
                    content=f"JD analyzed: {jd_analysis.get('job_title', 'Unknown')} "
                    f"— {len(jd_analysis.get('keywords', []))} keywords, "
                    f"{len(jd_analysis.get('required_skills', []))} required skills"
                )
            ],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JD analysis JSON: {e}")
        return {
            "error": f"JD analysis JSON parsing failed: {str(e)}",
            "current_step": "analyze_jd_error",
            "messages": [AIMessage(content=f"Error parsing JD analysis: {e}")],
        }
    except Exception as e:
        logger.error(f"JD analysis failed: {e}")
        return {
            "error": f"JD analysis failed: {str(e)}",
            "current_step": "analyze_jd_error",
            "messages": [AIMessage(content=f"Error analyzing JD: {e}")],
        }
