"""
Format-preserving PDF parser using PyMuPDF (fitz).

Extracts every text span with full positional + font metadata,
preserving the exact coordinates needed for reconstruction.
"""

from __future__ import annotations

import fitz  # PyMuPDF
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


# ── Data Structures ───────────────────────────────────────

@dataclass
class TextSpan:
    """A single text span with full layout metadata."""
    text: str
    font: str
    size: float
    color: int                   # sRGB int
    flags: int                   # bold/italic/superscript flags
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    origin: tuple[float, float]  # baseline origin point
    block_idx: int
    line_idx: int
    span_idx: int
    page_num: int

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 2**4)  # bit 4 = bold

    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2**1)  # bit 1 = italic

    @property
    def color_rgb(self) -> tuple[int, int, int]:
        """Convert sRGB int to (R, G, B)."""
        r = (self.color >> 16) & 0xFF
        g = (self.color >> 8) & 0xFF
        b = self.color & 0xFF
        return (r, g, b)


@dataclass
class PageLayout:
    """Layout data for a single page."""
    page_num: int
    width: float
    height: float
    spans: list[TextSpan] = field(default_factory=list)


@dataclass
class ResumeLayout:
    """Complete parsed layout of a resume PDF."""
    pages: list[PageLayout] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source_path: str = ""

    @property
    def all_spans(self) -> list[TextSpan]:
        spans = []
        for page in self.pages:
            spans.extend(page.spans)
        return spans

    @property
    def full_text(self) -> str:
        return "\n".join(s.text for s in self.all_spans if s.text.strip())

    def get_sections(self) -> list[dict]:
        """
        Heuristically detect sections by looking for larger/bold text
        that starts a new conceptual block.
        """
        sections: list[dict] = []
        current_section: dict | None = None
        all_sizes = [s.size for s in self.all_spans if s.text.strip()]
        if not all_sizes:
            return sections

        median_size = sorted(all_sizes)[len(all_sizes) // 2]

        for span in self.all_spans:
            text = span.text.strip()
            if not text:
                continue

            # A heading if: bold, or noticeably larger than median
            is_heading = span.is_bold and span.size >= median_size
            is_heading = is_heading or span.size > median_size * 1.15

            if is_heading and len(text) < 60:
                current_section = {
                    "title": text,
                    "page": span.page_num,
                    "spans": [span],
                    "bbox": span.bbox,
                }
                sections.append(current_section)
            elif current_section is not None:
                current_section["spans"].append(span)

        return sections


# ── Parser ────────────────────────────────────────────────

# Map for detecting symbol / icon fonts that should NOT be modified
SYMBOL_FONTS = {
    "wingdings", "webdings", "symbol", "zapfdingbats",
    "fontawesome", "material icons", "fa-solid", "fa-regular",
    "fa-brands", "icomoon", "glyphicons",
}


def _is_symbol_font(font_name: str) -> bool:
    """Check if a font is likely an icon/symbol font."""
    return any(sym in font_name.lower() for sym in SYMBOL_FONTS)


def parse_pdf(pdf_path: str | Path) -> ResumeLayout:
    """
    Parse a PDF into a ResumeLayout with full positional data.

    Uses PyMuPDF's get_text("dict") to extract every span
    with bounding boxes, font info, and colors.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Parsing PDF: {pdf_path}")

    # Enable small glyph heights to prevent bbox overlaps
    fitz.TOOLS.set_small_glyph_heights(True)

    doc = fitz.open(str(pdf_path))
    layout = ResumeLayout(
        source_path=str(pdf_path),
        metadata={
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "page_count": doc.page_count,
        },
    )

    for page_num in range(doc.page_count):
        page = doc[page_num]
        page_layout = PageLayout(
            page_num=page_num,
            width=page.rect.width,
            height=page.rect.height,
        )

        # Extract structured text data
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block_idx, block in enumerate(text_dict.get("blocks", [])):
            # Skip image blocks
            if block.get("type") != 0:
                continue

            for line_idx, line in enumerate(block.get("lines", [])):
                for span_idx, span in enumerate(line.get("spans", [])):
                    text = span.get("text", "")

                    ts = TextSpan(
                        text=text,
                        font=span.get("font", ""),
                        size=round(span.get("size", 0), 2),
                        color=span.get("color", 0),
                        flags=span.get("flags", 0),
                        bbox=tuple(round(v, 2) for v in span.get("bbox", (0, 0, 0, 0))),
                        origin=tuple(round(v, 2) for v in span.get("origin", (0, 0))),
                        block_idx=block_idx,
                        line_idx=line_idx,
                        span_idx=span_idx,
                        page_num=page_num,
                    )
                    page_layout.spans.append(ts)

        layout.pages.append(page_layout)

    doc.close()
    logger.info(
        f"Parsed {len(layout.pages)} page(s), "
        f"{len(layout.all_spans)} span(s) total"
    )
    return layout


def detect_columns(layout: ResumeLayout) -> int:
    """
    Detect if the resume uses multi-column layout.

    Returns estimated number of columns (1 or 2).
    """
    if not layout.pages:
        return 1

    page = layout.pages[0]
    if not page.spans:
        return 1

    # Collect x-centers of all spans
    x_centers = [
        (s.bbox[0] + s.bbox[2]) / 2
        for s in page.spans
        if s.text.strip()
    ]

    if not x_centers:
        return 1

    mid = page.width / 2
    left_count = sum(1 for x in x_centers if x < mid * 0.85)
    right_count = sum(1 for x in x_centers if x > mid * 1.15)
    total = len(x_centers)

    # If both sides have significant content → 2 columns
    if left_count > total * 0.25 and right_count > total * 0.25:
        logger.info("Detected 2-column layout")
        return 2

    logger.info("Detected single-column layout")
    return 1
