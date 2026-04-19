"""
Tests for the PDF validator module.
"""

import fitz
import pytest
from pathlib import Path
from src.pdf.validator import validate_pdf, ValidationResult


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def original_pdf(tmp_path) -> Path:
    """Create an original test PDF."""
    pdf_path = tmp_path / "original.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 60), "John Doe", fontname="hebo", fontsize=18)
    page.insert_text((72, 100), "EXPERIENCE", fontname="hebo", fontsize=14)
    page.insert_text((72, 125), "• Built microservices", fontname="helv", fontsize=10)
    page.insert_text((72, 145), "• Led engineering team", fontname="helv", fontsize=10)
    page.insert_text((72, 190), "SKILLS", fontname="hebo", fontsize=14)
    page.insert_text((72, 215), "Python, Docker, AWS", fontname="helv", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def matching_pdf(tmp_path) -> Path:
    """Create a PDF that closely matches the original."""
    pdf_path = tmp_path / "matching.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 60), "John Doe", fontname="hebo", fontsize=18)
    page.insert_text((72, 100), "EXPERIENCE", fontname="hebo", fontsize=14)
    page.insert_text((72, 125), "• Developed microservices", fontname="helv", fontsize=10)
    page.insert_text((72, 145), "• Managed engineering team", fontname="helv", fontsize=10)
    page.insert_text((72, 190), "SKILLS", fontname="hebo", fontsize=14)
    page.insert_text((72, 215), "Python, Docker, AWS, K8s", fontname="helv", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def changed_pdf(tmp_path) -> Path:
    """Create a PDF with significant layout changes."""
    pdf_path = tmp_path / "changed.pdf"
    doc = fitz.open()

    # Two pages instead of one
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((72, 60), "John Doe", fontname="hebo", fontsize=18)
    page1.insert_text((72, 100), "SKILLS", fontname="hebo", fontsize=14)  # Order changed

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72, 60), "EXPERIENCE", fontname="hebo", fontsize=14)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ── Tests ─────────────────────────────────────────────────

class TestValidatePdf:
    def test_matching_pdfs_pass(self, original_pdf, matching_pdf):
        result = validate_pdf(str(original_pdf), str(matching_pdf))
        assert isinstance(result, ValidationResult)
        assert result.format_preserved is True
        assert result.score >= 0.6

    def test_changed_pdfs_fail(self, original_pdf, changed_pdf):
        result = validate_pdf(str(original_pdf), str(changed_pdf))
        assert result.score < 1.0
        assert len(result.issues) > 0

    def test_page_count_check(self, original_pdf, changed_pdf):
        result = validate_pdf(str(original_pdf), str(changed_pdf))
        assert "page_count" in result.details

    def test_result_to_dict(self, original_pdf, matching_pdf):
        result = validate_pdf(str(original_pdf), str(matching_pdf))
        d = result.to_dict()
        assert "format_preserved" in d
        assert "score" in d
        assert "issues" in d

    def test_self_comparison_perfect(self, original_pdf):
        result = validate_pdf(str(original_pdf), str(original_pdf))
        assert result.format_preserved is True
        assert result.score >= 0.8
