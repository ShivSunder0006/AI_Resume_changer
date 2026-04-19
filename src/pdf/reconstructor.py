"""
Format-preserving PDF reconstructor using PyMuPDF redaction + overlay.

Strategy:
  1. Open original PDF
  2. For each modified span: redact old text → write new text at same coords
  3. Preserve all non-text elements (images, lines, shapes)
"""

from __future__ import annotations

import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

from src.pdf.parser import TextSpan, ResumeLayout, _is_symbol_font


# ── Font Mapping ──────────────────────────────────────────

# Map common PDF fonts → PyMuPDF built-in fonts
FONT_MAP: dict[str, str] = {
    # Sans-serif
    "arial": "helv",
    "helvetica": "helv",
    "calibri": "helv",
    "verdana": "helv",
    "tahoma": "helv",
    "segoeui": "helv",
    "trebuchetms": "helv",
    "opensans": "helv",
    "roboto": "helv",
    "lato": "helv",
    "inter": "helv",
    "sourcesanspro": "helv",
    "nunitosans": "helv",
    "outfit": "helv",
    # Serif
    "timesnewroman": "tiro",
    "times": "tiro",
    "georgia": "tiro",
    "garamond": "tiro",
    "cambria": "tiro",
    "palatino": "tiro",
    "bookantiqua": "tiro",
    # Monospace
    "couriernew": "cour",
    "courier": "cour",
    "consolas": "cour",
    "monaco": "cour",
    "lucidaconsole": "cour",
}


def _map_font(font_name: str, bold: bool = False, italic: bool = False) -> str:
    """Map an original font name to the closest PyMuPDF built-in font."""
    cleaned = font_name.lower().replace(" ", "").replace("-", "")
    # Strip common suffixes
    for suffix in ("regular", "bold", "italic", "bolditalic", "light", "medium", "semibold"):
        cleaned = cleaned.replace(suffix, "")

    base = FONT_MAP.get(cleaned, "helv")  # default to Helvetica

    # Apply bold/italic variants
    if base == "helv":
        if bold and italic:
            return "hebi"
        elif bold:
            return "hebo"
        elif italic:
            return "heit"
        return "helv"
    elif base == "tiro":
        if bold and italic:
            return "tibi"
        elif bold:
            return "tibo"
        elif italic:
            return "tiit"
        return "tiro"
    elif base == "cour":
        if bold and italic:
            return "cobi"
        elif bold:
            return "cobo"
        elif italic:
            return "coit"
        return "cour"

    return base


# ── Modification Container ────────────────────────────────

@dataclass
class SpanModification:
    """Describes a text replacement for a single span."""
    original_span: TextSpan
    new_text: str

    @property
    def length_ratio(self) -> float:
        """Ratio of new text length to original."""
        if not self.original_span.text:
            return 1.0
        return len(self.new_text) / len(self.original_span.text)


# ── Reconstructor ─────────────────────────────────────────

def reconstruct_pdf(
    original_path: str | Path,
    output_path: str | Path,
    modifications: list[SpanModification],
) -> dict:
    """
    Rebuild a PDF with modified text while preserving layout.

    Uses the redaction-based replacement method:
      1. For each modification, redact the original text
      2. Insert new text at the same position
      3. Preserve all non-text elements

    Returns a summary dict with stats about the reconstruction.
    """
    original_path = Path(original_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Reconstructing PDF: {original_path} → {output_path} "
        f"({len(modifications)} modifications)"
    )

    fitz.TOOLS.set_small_glyph_heights(True)

    doc = fitz.open(str(original_path))
    stats = {
        "total_modifications": len(modifications),
        "applied": 0,
        "skipped_symbol": 0,
        "length_warnings": [],
    }

    # Group modifications by page
    mods_by_page: dict[int, list[SpanModification]] = {}
    for mod in modifications:
        pg = mod.original_span.page_num
        mods_by_page.setdefault(pg, []).append(mod)

    for page_num, page_mods in mods_by_page.items():
        if page_num >= doc.page_count:
            logger.warning(f"Page {page_num} out of range, skipping")
            continue

        page = doc[page_num]

        for mod in page_mods:
            span = mod.original_span

            # Skip symbol/icon fonts — never modify them
            if _is_symbol_font(span.font):
                stats["skipped_symbol"] += 1
                logger.debug(f"Skipping symbol font span: {span.font}")
                continue

            # Skip empty text
            if not span.text.strip() and not mod.new_text.strip():
                continue

            # Length guard
            if mod.length_ratio > 1.15:
                warning = (
                    f"Page {page_num}: text '{span.text[:30]}...' → "
                    f"'{mod.new_text[:30]}...' is {mod.length_ratio:.0%} "
                    f"of original length (may overflow)"
                )
                stats["length_warnings"].append(warning)
                logger.warning(warning)

            rect = fitz.Rect(span.bbox)

            # Add redaction annotation to just wipe out the old text background
            page.add_redact_annot(
                rect,
                fill=(1, 1, 1),  # white background to cover old text
            )

            stats["applied"] += 1

        # Apply all redactions for this page at once (erases original text)
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE  # preserve images
        )
        
        # Now insert the new text allowing wrapping but fixing font size
        for mod in page_mods:
            span = mod.original_span
            if _is_symbol_font(span.font) or (not span.text.strip() and not mod.new_text.strip()):
                continue
                
            mapped_font = _map_font(span.font, span.is_bold, span.is_italic)
            r, g, b = span.color_rgb
            text_color = (r / 255.0, g / 255.0, b / 255.0)
            
            # Expand the rect. We use the original x0, y0.
            # Right edge goes up to page margin (width - 36), bottom edge expands significantly.
            target_rect = fitz.Rect(
                span.bbox[0],
                span.bbox[1],
                min(page.rect.width - 36, span.bbox[0] + 500),  # Max 500pt wide
                span.bbox[3] + 200  # Allow deep vertical expansion for wrapping
            )
            
            # insert_textbox handles line wrapping natively
            page.insert_textbox(
                target_rect,
                mod.new_text,
                fontname=mapped_font,
                fontsize=span.size,
                color=text_color,
                align=fitz.TEXT_ALIGN_LEFT
            )

    # Save
    doc.save(str(output_path), garbage=4, deflate=True)
    doc.close()

    logger.info(
        f"Reconstruction complete: {stats['applied']} applied, "
        f"{stats['skipped_symbol']} symbol-skipped, "
        f"{len(stats['length_warnings'])} length warnings"
    )

    return stats
