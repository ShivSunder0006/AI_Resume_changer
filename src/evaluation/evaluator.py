"""
Evaluation system — scores the quality of resume tailoring.

Metrics:
  1. Keyword Match Score  — % of JD keywords in tailored resume
  2. ATS Simulation       — TF-IDF cosine similarity
  3. Content Integrity    — No hallucinated entities
  4. Format Score         — From validator
"""

from __future__ import annotations

import re
from loguru import logger


def evaluate_result(
    original_resume_text: str,
    job_description: str,
    jd_analysis: dict,
    tailored_pdf_path: str | None,
    validation_result: dict | None,
) -> dict:
    """
    Run all evaluation metrics on the tailoring result.

    Returns a dict of scores.
    """
    scores: dict = {}

    # ── 1. Keyword Match Score ────────────────────────────
    try:
        keywords = jd_analysis.get("keywords", []) + jd_analysis.get("required_skills", [])
        keywords = [k.lower().strip() for k in keywords if k.strip()]

        if tailored_pdf_path:
            from src.pdf.parser import parse_pdf
            tailored_layout = parse_pdf(tailored_pdf_path)
            tailored_text = tailored_layout.full_text.lower()
        else:
            tailored_text = original_resume_text.lower()

        if keywords:
            matched = sum(1 for kw in keywords if kw in tailored_text)
            scores["keyword_match"] = round(matched / len(keywords), 3)
            scores["keywords_found"] = matched
            scores["keywords_total"] = len(keywords)
        else:
            scores["keyword_match"] = 0.0

    except Exception as e:
        logger.warning(f"Keyword match scoring failed: {e}")
        scores["keyword_match"] = None

    # ── 2. ATS Simulation (TF-IDF Cosine) ─────────────────
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        if tailored_pdf_path:
            from src.pdf.parser import parse_pdf
            tailored_layout = parse_pdf(tailored_pdf_path)
            tailored_text_full = tailored_layout.full_text
        else:
            tailored_text_full = original_resume_text

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=500,
        )
        tfidf = vectorizer.fit_transform([job_description, tailored_text_full])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]

        scores["ats_similarity"] = round(float(similarity), 3)

        # Also compute original similarity for comparison
        tfidf_orig = vectorizer.transform([original_resume_text])
        orig_similarity = cosine_similarity(tfidf[0:1], tfidf_orig)[0][0]
        scores["original_ats_similarity"] = round(float(orig_similarity), 3)
        scores["ats_improvement"] = round(
            scores["ats_similarity"] - scores["original_ats_similarity"], 3
        )

    except Exception as e:
        logger.warning(f"ATS scoring failed: {e}")
        scores["ats_similarity"] = None

    # ── 3. Content Integrity ──────────────────────────────
    try:
        # Extract company names and dates from original
        # Simple pattern: capitalized multi-word phrases that look like company names
        original_lower = original_resume_text.lower()

        if tailored_pdf_path:
            from src.pdf.parser import parse_pdf
            tailored_layout = parse_pdf(tailored_pdf_path)
            tailored_lower = tailored_layout.full_text.lower()
        else:
            tailored_lower = original_lower

        # Check for new company-like strings in tailored that aren't in original
        # Simple heuristic: look for capitalized words followed by Inc/Corp/LLC etc
        company_patterns = re.findall(
            r"(?:at|for|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            tailored_lower,
        )

        original_companies = set(
            re.findall(
                r"(?:at|for|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
                original_lower,
            )
        )

        hallucinated = [c for c in company_patterns if c not in original_companies]
        scores["content_integrity"] = 1.0 if not hallucinated else 0.5
        scores["potential_hallucinations"] = hallucinated[:5]  # limit output

    except Exception as e:
        logger.warning(f"Content integrity check failed: {e}")
        scores["content_integrity"] = None

    # ── 4. Format Score ───────────────────────────────────
    if validation_result:
        scores["format_score"] = validation_result.get("score", 0)
        scores["format_preserved"] = validation_result.get("format_preserved", False)
    else:
        scores["format_score"] = None

    # ── Overall Score ─────────────────────────────────────
    numeric_scores = [
        v for k, v in scores.items()
        if isinstance(v, (int, float)) and k in (
            "keyword_match", "ats_similarity",
            "content_integrity", "format_score"
        )
    ]
    if numeric_scores:
        scores["overall"] = round(sum(numeric_scores) / len(numeric_scores), 3)
    else:
        scores["overall"] = 0.0

    logger.info(f"Evaluation scores: {scores}")
    return scores
