"""
Node: Tailor resume content using LLM.

Uses strict constraints to prevent hallucination.
Only modifies descriptive text — never names, companies, dates.
"""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.agents.state import AgentState
from src.agents.prompts.tailor import TAILOR_SYSTEM, TAILOR_HUMAN
from src.llm.router import LLMRouter
from src.utils.scraper import enrich_from_urls


def tailor_resume_node(state: AgentState) -> dict:
    """Generate text modifications for the resume based on JD analysis."""
    logger.info("=== NODE: tailor_resume ===")

    try:
        resume_sections = state.get("resume_sections", [])
        jd_analysis = state.get("jd_analysis", {})

        if not resume_sections:
            return {
                "error": "No resume sections to tailor",
                "current_step": "tailor_error",
                "messages": [AIMessage(content="Error: No resume sections found")],
            }

        if not jd_analysis:
            return {
                "error": "No JD analysis available",
                "current_step": "tailor_error",
                "messages": [AIMessage(content="Error: No JD analysis available")],
            }

        # Format sections for the prompt
        sections_formatted = ""
        for section in resume_sections:
            sections_formatted += f"\n### {section['title']}\n"
            sections_formatted += section["content"] + "\n"

        external_data = ""
        if state.get("external_urls"):
            external_data = enrich_from_urls(state["external_urls"])
            if external_data:
                jd_analysis["EXTRACTED_EXTERNAL_CONTEXT"] = external_data

        feedback_instruction = ""
        if state.get("user_feedback"):
            feedback_instruction = f"\n\nCRITICAL USER FEEDBACK FOR PREVIOUS ATTEMPT:\n{state['user_feedback']}\nYou MUST incorporate these instructions immediately into the generated modifications."

        # Build messages
        system_content = TAILOR_SYSTEM + feedback_instruction
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(
                content=TAILOR_HUMAN.format(
                    resume_sections=sections_formatted,
                    jd_analysis=json.dumps(jd_analysis, indent=2),
                )
            ),
        ]

        # Call LLM
        router = LLMRouter()
        response = router.invoke(messages)

        # Parse response
        response_text = response.content
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]

        result = json.loads(json_text.strip())
        modifications = result.get("modifications", [])

        # Validate modifications — filter out any that violate constraints
        validated_mods = []
        for mod in modifications:
            original = mod.get("original_text", "")
            new_text = mod.get("new_text", "")

            if not original or not new_text:
                continue

            # Length guard: new text should be within ±20% of original
            if len(original) > 0:
                ratio = len(new_text) / len(original)
                if ratio > 1.20:
                    # Truncate to fit approximately
                    logger.warning(
                        f"Modification too long ({ratio:.0%}), trimming: "
                        f"'{new_text[:40]}...'"
                    )
                    new_text = new_text[:int(len(original) * 1.15)]
                    mod["new_text"] = new_text

            validated_mods.append(mod)

        logger.info(
            f"Tailoring: {len(validated_mods)} modifications "
            f"(from {len(modifications)} proposed)"
        )

        return {
            "tailoring_instructions": validated_mods,
            "modifications_count": len(validated_mods),
            "current_step": "tailor_complete",
            "llm_provider_used": router.last_provider,
            "messages": [
                AIMessage(
                    content=f"Generated {len(validated_mods)} resume modifications"
                )
            ],
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse tailoring JSON: {e}")
        return {
            "error": f"Tailoring JSON parsing failed: {str(e)}",
            "current_step": "tailor_error",
            "messages": [AIMessage(content=f"Error parsing tailoring output: {e}")],
        }
    except Exception as e:
        logger.error(f"Resume tailoring failed: {e}")
        return {
            "error": f"Resume tailoring failed: {str(e)}",
            "current_step": "tailor_error",
            "messages": [AIMessage(content=f"Error tailoring resume: {e}")],
        }
