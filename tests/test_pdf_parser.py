"""
Tests for the PDF parser module.
"""

import fitz
import pytest
from pathlib import Path
from src.pdf.parser import parse_pdf, detect_columns, ResumeLayout, TextSpan


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Create a simple test PDF with known content."""
    pdf_path = tmp_path / "test_resume.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)  # Letter size

    # Header
    page.insert_text(
        (72, 60),
        "John Doe",
        fontname="helv",
        fontsize=20,
    )

    # Contact
    page.insert_text(
        (72, 85),
        "john@example.com | (555) 123-4567",
        fontname="helv",
        fontsize=10,
    )

    # Section heading
    page.insert_text(
        (72, 120),
        "EXPERIENCE",
        fontname="hebo",
        fontsize=14,
    )

    # Bullet points
    bullets = [
        "• Developed scalable microservices using Python and FastAPI",
        "• Led a team of 5 engineers to deliver CI/CD pipeline",
        "• Reduced API response time by 40% through optimization",
    ]
    y = 145
    for bullet in bullets:
        page.insert_text(
            (72, y),
            bullet,
            fontname="helv",
            fontsize=10,
        )
        y += 18

    # Another section
    page.insert_text(
        (72, y + 20),
        "SKILLS",
        fontname="hebo",
        fontsize=14,
    )

    page.insert_text(
        (72, y + 45),
        "Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL, Redis",
        fontname="helv",
        fontsize=10,
    )

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


@pytest.fixture
def two_column_pdf(tmp_path) -> Path:
    """Create a two-column test PDF."""
    pdf_path = tmp_path / "two_col.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)

    # Left column content
    page.insert_text((50, 60), "Skills", fontname="hebo", fontsize=14)
    page.insert_text((50, 85), "Python", fontname="helv", fontsize=10)
    page.insert_text((50, 100), "JavaScript", fontname="helv", fontsize=10)
    page.insert_text((50, 115), "Docker", fontname="helv", fontsize=10)

    # Right column content
    page.insert_text((330, 60), "Experience", fontname="hebo", fontsize=14)
    page.insert_text((330, 85), "Software Engineer at TechCo", fontname="helv", fontsize=10)
    page.insert_text((330, 100), "Led backend development", fontname="helv", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


# ── Tests ─────────────────────────────────────────────────

class TestParsePdf:
    def test_parse_returns_layout(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        assert isinstance(layout, ResumeLayout)
        assert len(layout.pages) == 1
        assert len(layout.all_spans) > 0

    def test_extracts_text(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        full_text = layout.full_text
        assert "John Doe" in full_text
        assert "EXPERIENCE" in full_text
        assert "Python" in full_text

    def test_extracts_font_metadata(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        # Find the name span
        name_spans = [s for s in layout.all_spans if "John Doe" in s.text]
        assert len(name_spans) > 0
        assert name_spans[0].size == 20.0

    def test_extracts_bbox(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        for span in layout.all_spans:
            if span.text.strip():
                assert span.bbox[2] > span.bbox[0]  # x1 > x0
                assert span.bbox[3] > span.bbox[1]  # y1 > y0

    def test_detects_sections(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        sections = layout.get_sections()
        section_titles = [s["title"] for s in sections]
        assert "EXPERIENCE" in section_titles
        assert "SKILLS" in section_titles

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_pdf("nonexistent.pdf")


class TestDetectColumns:
    def test_single_column(self, sample_pdf):
        layout = parse_pdf(sample_pdf)
        assert detect_columns(layout) == 1

    def test_two_columns(self, two_column_pdf):
        layout = parse_pdf(two_column_pdf)
        assert detect_columns(layout) == 2
