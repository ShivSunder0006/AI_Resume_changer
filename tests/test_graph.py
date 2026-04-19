"""
Integration test for the LangGraph workflow.
"""

import fitz
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage


@pytest.fixture
def test_resume_pdf(tmp_path) -> Path:
    """Create a realistic test resume PDF."""
    pdf_path = tmp_path / "resume.pdf"
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)

    # Name
    page.insert_text((72, 50), "Jane Smith", fontname="hebo", fontsize=22)
    page.insert_text((72, 72), "jane@email.com | (555) 987-6543 | linkedin.com/in/janesmith",
                     fontname="helv", fontsize=9)

    # Summary
    page.insert_text((72, 105), "PROFESSIONAL SUMMARY", fontname="hebo", fontsize=13)
    page.insert_text((72, 125),
        "Experienced software engineer with 5+ years building scalable applications.",
        fontname="helv", fontsize=10)

    # Experience
    page.insert_text((72, 160), "EXPERIENCE", fontname="hebo", fontsize=13)
    page.insert_text((72, 182), "Senior Software Engineer | TechCorp | 2021 - Present",
                     fontname="helv", fontsize=10)
    page.insert_text((72, 200), "• Designed and implemented RESTful APIs serving 1M+ requests/day",
                     fontname="helv", fontsize=10)
    page.insert_text((72, 218), "• Led migration from monolith to microservices architecture",
                     fontname="helv", fontsize=10)
    page.insert_text((72, 236), "• Mentored 3 junior developers and conducted code reviews",
                     fontname="helv", fontsize=10)

    # Skills
    page.insert_text((72, 275), "SKILLS", fontname="hebo", fontsize=13)
    page.insert_text((72, 295), "Python, Java, Docker, Kubernetes, AWS, PostgreSQL, Redis, Git",
                     fontname="helv", fontsize=10)

    # Education
    page.insert_text((72, 335), "EDUCATION", fontname="hebo", fontsize=13)
    page.insert_text((72, 355), "B.S. Computer Science | State University | 2018",
                     fontname="helv", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def test_job_description() -> str:
    return """
    Senior Backend Engineer at CloudScale Inc.

    We are looking for a Senior Backend Engineer to join our platform team.

    Requirements:
    - 5+ years of experience in backend development
    - Strong proficiency in Python and Go
    - Experience with cloud platforms (AWS, GCP)
    - Knowledge of containerization and orchestration (Docker, Kubernetes)
    - Experience with distributed systems and microservices
    - Strong SQL and database design skills
    - CI/CD pipeline experience

    Responsibilities:
    - Design and build scalable backend services
    - Optimize API performance and reliability
    - Collaborate with cross-functional teams
    - Contribute to architecture decisions
    - Write comprehensive tests and documentation
    """


class TestGraphIntegration:
    """Test the full LangGraph pipeline with mocked LLM calls."""

    @patch("src.agents.nodes.tailor_resume.LLMRouter")
    @patch("src.agents.nodes.analyze_jd.LLMRouter")
    def test_full_pipeline(
        self,
        MockAnalyzeRouter,
        MockTailorRouter,
        test_resume_pdf,
        test_job_description,
        tmp_path,
    ):
        """Test the complete pipeline with mocked LLM responses."""
        import json

        # Mock JD analysis response
        jd_response = json.dumps({
            "job_title": "Senior Backend Engineer",
            "company": "CloudScale Inc.",
            "required_skills": ["Python", "Go", "AWS", "Docker", "Kubernetes"],
            "preferred_skills": ["GCP", "distributed systems"],
            "keywords": ["backend", "scalable", "microservices", "CI/CD", "API"],
            "experience_years": "5+",
            "education": "Bachelor's in CS",
            "responsibilities": ["Design backend services", "Optimize API performance"],
            "industry_terms": ["orchestration", "containerization"],
            "tone": "corporate",
        })

        mock_analyze = MockAnalyzeRouter.return_value
        mock_analyze.invoke.return_value = AIMessage(content=jd_response)
        mock_analyze.last_provider = "groq"

        # Mock tailoring response
        tailor_response = json.dumps({
            "modifications": [
                {
                    "original_text": "Designed and implemented RESTful APIs serving 1M+ requests/day",
                    "new_text": "Architected scalable backend APIs serving 1M+ requests/day",
                    "section": "EXPERIENCE",
                    "reason": "Added 'scalable' and 'backend' keywords",
                },
                {
                    "original_text": "Led migration from monolith to microservices architecture",
                    "new_text": "Led migration to distributed microservices architecture",
                    "section": "EXPERIENCE",
                    "reason": "Added 'distributed' keyword from JD",
                },
            ]
        })

        mock_tailor = MockTailorRouter.return_value
        mock_tailor.invoke.return_value = AIMessage(content=tailor_response)
        mock_tailor.last_provider = "groq"

        # Patch output dir
        with patch("src.agents.nodes.reconstruct_pdf.get_settings") as mock_settings:
            mock_settings.return_value.output_path = tmp_path

            from src.agents.graph import run_agent

            result = run_agent(
                resume_pdf_path=str(test_resume_pdf),
                job_description=test_job_description,
            )

        # Verify results
        assert result.get("error") is None or result.get("output_pdf_path") is not None
        assert result.get("resume_text") is not None
        assert "Jane Smith" in result["resume_text"]
