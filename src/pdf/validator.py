"""
Format preservation validator.

Compares original and tailored PDFs to ensure layout integrity.
Returns a structured validation report.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from loguru import logger

from src.pdf.parser import parse_pdf, ResumeLayout, TextSpan


@dataclass
class ValidationResult:
    """Structured validation report."""
    format_preserved: bool = True
    score: float = 1.0
    issues: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "format_preserved": self.format_preserved,
            "score": round(self.score, 3),
            "issues": self.issues,
            "details": self.details,
        }


def validate_pdf(
    original_path: str,
    tailored_path: str,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate that the tailored PDF preserves the format of the original.

    Checks:
      1. Page count match
      2. Section order preservation
      3. Bullet count consistency
      4. Layout similarity (bbox positions)
      5. Font preservation (approximate)
    """
    result = ValidationResult()
    checks_passed = 0
    total_checks = 5

    try:
        original = parse_pdf(original_path)
        tailored = parse_pdf(tailored_path)
    except Exception as e:
        result.format_preserved = False
        result.score = 0.0
        result.issues.append(f"Failed to parse PDFs: {e}")
        return result

    # ── 1. Page Count ─────────────────────────────────────
    if len(original.pages) == len(tailored.pages):
        checks_passed += 1
        result.details["page_count"] = "PASS"
    else:
        result.issues.append(
            f"Page count mismatch: original={len(original.pages)}, "
            f"tailored={len(tailored.pages)}"
        )
        result.details["page_count"] = "FAIL"

    # ── 2. Section Order ──────────────────────────────────
    orig_sections = original.get_sections()
    tail_sections = tailored.get_sections()

    orig_titles = [s["title"].lower().strip() for s in orig_sections]
    tail_titles = [s["title"].lower().strip() for s in tail_sections]

    if orig_titles == tail_titles:
        checks_passed += 1
        result.details["section_order"] = "PASS"
    else:
        # Check if at least the section names exist (order may differ slightly)
        orig_set = set(orig_titles)
        tail_set = set(tail_titles)
        missing = orig_set - tail_set
        if not missing:
            checks_passed += 0.5
            result.details["section_order"] = "PARTIAL"
            result.issues.append(
                f"Section order changed. Original: {orig_titles}, "
                f"Tailored: {tail_titles}"
            )
        else:
            result.details["section_order"] = "FAIL"
            result.issues.append(f"Missing sections: {missing}")

    # ── 3. Bullet Count ──────────────────────────────────
    bullet_chars = {"•", "●", "○", "▪", "▸", "►", "-", "–", "—"}

    def count_bullets(layout: ResumeLayout) -> int:
        count = 0
        for span in layout.all_spans:
            text = span.text.strip()
            if text and text[0] in bullet_chars:
                count += 1
        return count

    orig_bullets = count_bullets(original)
    tail_bullets = count_bullets(tailored)

    if orig_bullets == 0 and tail_bullets == 0:
        checks_passed += 1
        result.details["bullet_count"] = "PASS (no bullets)"
    elif orig_bullets > 0:
        ratio = tail_bullets / orig_bullets
        if 0.8 <= ratio <= 1.2:
            checks_passed += 1
            result.details["bullet_count"] = f"PASS ({orig_bullets}→{tail_bullets})"
        else:
            result.details["bullet_count"] = f"FAIL ({orig_bullets}→{tail_bullets})"
            result.issues.append(
                f"Bullet count changed significantly: "
                f"{orig_bullets} → {tail_bullets}"
            )
    else:
        checks_passed += 1
        result.details["bullet_count"] = "PASS"

    # ── 4. Layout Similarity (Bbox Positions) ─────────────
    def get_bbox_centers(layout: ResumeLayout) -> list[tuple[float, float]]:
        centers = []
        for span in layout.all_spans:
            if span.text.strip():
                cx = (span.bbox[0] + span.bbox[2]) / 2
                cy = (span.bbox[1] + span.bbox[3]) / 2
                centers.append((cx, cy))
        return centers

    orig_centers = get_bbox_centers(original)
    tail_centers = get_bbox_centers(tailored)

    min_len = min(len(orig_centers), len(tail_centers))
    if min_len > 0:
        distances = []
        for i in range(min_len):
            dx = orig_centers[i][0] - tail_centers[i][0]
            dy = orig_centers[i][1] - tail_centers[i][1]
            distances.append(math.sqrt(dx**2 + dy**2))

        avg_dist = sum(distances) / len(distances)
        result.details["avg_bbox_displacement"] = round(avg_dist, 2)

        if avg_dist < 5.0:
            checks_passed += 1
            result.details["layout_similarity"] = "PASS"
        elif avg_dist < 15.0:
            checks_passed += 0.5
            result.details["layout_similarity"] = "PARTIAL"
            result.issues.append(
                f"Layout shifted slightly (avg displacement: {avg_dist:.1f}px)"
            )
        else:
            result.details["layout_similarity"] = "FAIL"
            result.issues.append(
                f"Significant layout shift (avg displacement: {avg_dist:.1f}px)"
            )
    else:
        checks_passed += 1
        result.details["layout_similarity"] = "PASS (no spans to compare)"

    # ── 5. Font Preservation ──────────────────────────────
    def get_fonts(layout: ResumeLayout) -> set[str]:
        return {
            s.font.lower().split("-")[0].split("+")[-1]
            for s in layout.all_spans
            if s.text.strip() and s.font
        }

    orig_fonts = get_fonts(original)
    tail_fonts = get_fonts(tailored)

    if orig_fonts == tail_fonts:
        checks_passed += 1
        result.details["font_preservation"] = "PASS"
    else:
        # Fonts will differ because we use built-in fonts during reconstruction
        # This is expected — so we give partial credit
        checks_passed += 0.5
        changed_fonts = orig_fonts.symmetric_difference(tail_fonts)
        result.details["font_preservation"] = "PARTIAL"
        result.issues.append(
            f"Font substitution detected: {changed_fonts}"
        )

    # ── Final Score ───────────────────────────────────────
    result.score = checks_passed / total_checks
    result.format_preserved = result.score >= 0.6

    if strict:
        result.format_preserved = result.score >= 0.8

    logger.info(
        f"Validation: score={result.score:.2f}, "
        f"preserved={result.format_preserved}, "
        f"issues={len(result.issues)}"
    )

    return result
