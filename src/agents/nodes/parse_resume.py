"""
Node: Parse Resume PDF into structured layout data.
"""

from loguru import logger
from langchain_core.messages import AIMessage

from src.agents.state import AgentState
from src.pdf.parser import parse_pdf, detect_columns


def parse_resume_node(state: AgentState) -> dict:
    """Parse the uploaded PDF resume into structured layout."""
    logger.info("=== NODE: parse_resume ===")

    try:
        pdf_path = state["resume_pdf_path"]
        layout = parse_pdf(pdf_path)
        num_columns = detect_columns(layout)

        # Extract sections for LLM consumption
        sections = layout.get_sections()
        sections_text = []
        for section in sections:
            title = section["title"]
            body_texts = [s.text for s in section["spans"] if s.text.strip()]
            sections_text.append({
                "title": title,
                "content": "\n".join(body_texts),
                "span_count": len(section["spans"]),
            })

        # Serialise the layout for state (convert dataclasses to dicts)
        layout_dict = {
            "pages": [
                {
                    "page_num": page.page_num,
                    "width": page.width,
                    "height": page.height,
                    "span_count": len(page.spans),
                    "spans": [
                        {
                            "text": s.text,
                            "font": s.font,
                            "size": s.size,
                            "color": s.color,
                            "flags": s.flags,
                            "bbox": list(s.bbox),
                            "origin": list(s.origin),
                            "block_idx": s.block_idx,
                            "line_idx": s.line_idx,
                            "span_idx": s.span_idx,
                            "page_num": s.page_num,
                        }
                        for s in page.spans
                    ],
                }
                for page in layout.pages
            ],
            "metadata": layout.metadata,
            "source_path": layout.source_path,
            "num_columns": num_columns,
        }

        logger.info(
            f"Parsed: {len(layout.pages)} pages, "
            f"{len(layout.all_spans)} spans, "
            f"{num_columns} column(s), "
            f"{len(sections)} sections"
        )

        return {
            "resume_layout": layout_dict,
            "resume_text": layout.full_text,
            "resume_sections": sections_text,
            "current_step": "parse_resume_complete",
            "messages": [
                AIMessage(content=f"Parsed resume: {len(layout.pages)} pages, {len(sections)} sections, {num_columns}-column layout")
            ],
        }

    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        return {
            "error": f"Resume parsing failed: {str(e)}",
            "current_step": "parse_resume_error",
            "messages": [AIMessage(content=f"Error parsing resume: {e}")],
        }
