"""
Node: Reconstruct the tailored PDF preserving original formatting.
"""

import uuid
from pathlib import Path
from loguru import logger
from langchain_core.messages import AIMessage

from src.agents.state import AgentState
from src.pdf.parser import parse_pdf, TextSpan
from src.pdf.reconstructor import SpanModification, reconstruct_pdf
from src.config.settings import get_settings


def reconstruct_pdf_node(state: AgentState) -> dict:
    """Apply text modifications to the PDF using redaction+overlay."""
    logger.info("=== NODE: reconstruct_pdf ===")

    try:
        original_path = state["resume_pdf_path"]
        instructions = state.get("tailoring_instructions", [])
        layout_dict = state.get("resume_layout")

        if not instructions:
            return {
                "error": "No tailoring instructions to apply",
                "current_step": "reconstruct_error",
                "messages": [AIMessage(content="Error: No modifications to apply")],
            }

        if not layout_dict:
            return {
                "error": "No resume layout data available",
                "current_step": "reconstruct_error",
                "messages": [AIMessage(content="Error: Resume layout not parsed")],
            }

        # Re-parse to get fresh TextSpan objects
        layout = parse_pdf(original_path)

        # Match LLM modifications to actual PDF spans
        modifications: list[SpanModification] = []
        matched = 0
        unmatched = 0

        for instruction in instructions:
            original_text = instruction.get("original_text", "").strip()
            new_text = instruction.get("new_text", "").strip()

            if not original_text or not new_text:
                continue

            # Find matching span(s) in the layout
            found = False
            for span in layout.all_spans:
                span_text = span.text.strip()

                # Exact match
                if span_text == original_text:
                    modifications.append(
                        SpanModification(original_span=span, new_text=new_text)
                    )
                    found = True
                    matched += 1
                    break

                # Partial match — if the original_text is a substring
                # of a longer span, replace within that span
                if original_text in span_text and len(original_text) > 10:
                    new_span_text = span_text.replace(original_text, new_text, 1)
                    modifications.append(
                        SpanModification(original_span=span, new_text=new_span_text)
                    )
                    found = True
                    matched += 1
                    break

            if not found:
                # Try fuzzy matching — find span with most overlap
                best_span = None
                best_overlap = 0

                for span in layout.all_spans:
                    span_text = span.text.strip()
                    if not span_text:
                        continue

                    # Simple word overlap
                    orig_words = set(original_text.lower().split())
                    span_words = set(span_text.lower().split())
                    if not orig_words:
                        continue

                    overlap = len(orig_words & span_words) / len(orig_words)

                    if overlap > best_overlap and overlap > 0.6:
                        best_overlap = overlap
                        best_span = span

                if best_span:
                    modifications.append(
                        SpanModification(original_span=best_span, new_text=new_text)
                    )
                    matched += 1
                    logger.debug(
                        f"Fuzzy matched: '{original_text[:30]}...' → "
                        f"'{best_span.text[:30]}...' (overlap={best_overlap:.0%})"
                    )
                else:
                    unmatched += 1
                    logger.warning(
                        f"Could not match modification: '{original_text[:50]}...'"
                    )

        if not modifications:
            logger.warning("No modifications matched to PDF spans. Returning original file.")
            return {
                "output_pdf_path": original_path,
                "reconstruction_stats": {"matched": 0, "unmatched": unmatched, "applied": 0},
                "current_step": "reconstruct_complete",
                "messages": [AIMessage(content="Warning: No modifications matched. Original PDF returned.")],
            }

        # Generate output path
        settings = get_settings()
        output_filename = f"tailored_{uuid.uuid4().hex[:8]}.pdf"
        output_path = str(settings.output_path / output_filename)

        # Reconstruct
        stats = reconstruct_pdf(original_path, output_path, modifications)
        stats["matched"] = matched
        stats["unmatched"] = unmatched

        logger.info(
            f"Reconstruction: {matched} matched, {unmatched} unmatched, "
            f"{stats['applied']} applied"
        )

        return {
            "output_pdf_path": output_path,
            "reconstruction_stats": stats,
            "current_step": "reconstruct_complete",
            "messages": [
                AIMessage(
                    content=f"PDF reconstructed: {stats['applied']} modifications applied, "
                    f"saved to {output_filename}"
                )
            ],
        }

    except Exception as e:
        logger.error(f"PDF reconstruction failed: {e}")
        return {
            "error": f"PDF reconstruction failed: {str(e)}",
            "current_step": "reconstruct_error",
            "messages": [AIMessage(content=f"Error reconstructing PDF: {e}")],
        }
