"""
Tests for the PDF reconstructor module.
"""

import fitz
import pytest
from pathlib import Path
from src.pdf.parser import parse_pdf, TextSpan
from src.pdf.reconstructor import reconstruct_pdf, SpanModification, _map_font


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Create a test PDF for reconstruction."""
    pdf_path = tmp_path / "original.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)

    page.insert_text((72, 60), "John Doe", fontname="helv", fontsize=20)
    page.insert_text((72, 90), "Software Engineer", fontname="helv", fontsize=12)
    page.insert_text(
        (72, 130),
        "Developed web applications using Python and Django",
        fontname="helv",
        fontsize=10,
    )
    page.insert_text(
        (72, 150),
        "Managed database operations for production systems",
        fontname="helv",
        fontsize=10,
    )

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


# ── Tests ─────────────────────────────────────────────────

class TestFontMapping:
    def test_maps_arial_to_helv(self):
        assert _map_font("Arial") == "helv"

    def test_maps_times_to_tiro(self):
        assert _map_font("TimesNewRoman") == "tiro"

    def test_maps_courier_to_cour(self):
        assert _map_font("CourierNew") == "cour"

    def test_bold_variant(self):
        assert _map_font("Arial", bold=True) == "hebo"

    def test_italic_variant(self):
        assert _map_font("Arial", italic=True) == "heit"

    def test_unknown_font_defaults_to_helv(self):
        assert _map_font("UnknownFont") == "helv"


class TestReconstructPdf:
    def test_reconstruct_no_modifications(self, sample_pdf, tmp_path):
        output_path = tmp_path / "output.pdf"
        stats = reconstruct_pdf(sample_pdf, output_path, [])
        # With no modifications, file should still be created (copy)
        assert output_path.exists()
        assert stats["total_modifications"] == 0

    def test_reconstruct_with_modification(self, sample_pdf, tmp_path):
        layout = parse_pdf(sample_pdf)
        output_path = tmp_path / "output.pdf"

        # Find a span to modify
        target_span = None
        for span in layout.all_spans:
            if "Developed" in span.text:
                target_span = span
                break

        assert target_span is not None

        mod = SpanModification(
            original_span=target_span,
            new_text="Built scalable web apps using Python and FastAPI",
        )

        stats = reconstruct_pdf(sample_pdf, output_path, [mod])

        assert output_path.exists()
        assert stats["applied"] == 1

        # Verify the new PDF has the modified text
        new_layout = parse_pdf(output_path)
        new_text = new_layout.full_text
        assert "Built scalable" in new_text or "FastAPI" in new_text

    def test_preserves_unmodified_text(self, sample_pdf, tmp_path):
        layout = parse_pdf(sample_pdf)
        output_path = tmp_path / "output.pdf"

        target_span = None
        for span in layout.all_spans:
            if "Developed" in span.text:
                target_span = span
                break

        mod = SpanModification(
            original_span=target_span,
            new_text="Built scalable web apps",
        )

        reconstruct_pdf(sample_pdf, output_path, [mod])

        new_layout = parse_pdf(output_path)
        new_text = new_layout.full_text

        # Unmodified text should still be there
        assert "John Doe" in new_text
        assert "Software Engineer" in new_text

    def test_length_ratio(self):
        span = TextSpan(
            text="Short text",
            font="helv",
            size=10,
            color=0,
            flags=0,
            bbox=(0, 0, 100, 20),
            origin=(0, 0),
            block_idx=0,
            line_idx=0,
            span_idx=0,
            page_num=0,
        )

        mod = SpanModification(original_span=span, new_text="Much longer replacement text here")
        assert mod.length_ratio > 1.0

        mod2 = SpanModification(original_span=span, new_text="Short")
        assert mod2.length_ratio < 1.0
