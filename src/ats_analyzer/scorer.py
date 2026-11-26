"""Step 3: Compare resume vs job description and produce a score + tips."""

import re
from dataclasses import dataclass, field

from .keywords import extract_keywords, tokenize

EXPECTED_SECTIONS = ["summary", "experience", "education", "skills", "projects"]


@dataclass
class AnalysisResult:
    score: int                                   # 0-100 overall ATS score
    keyword_score: int                           # % of job keywords found
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def _contains(resume_text: str, resume_tokens: set[str], term: str) -> bool:
    if " " in term:
        return term in resume_text
    return term in resume_tokens


def analyze(resume_text: str, job_text: str, top_n: int = 30) -> AnalysisResult:
    resume_lower = resume_text.lower()
    resume_tokens = set(tokenize(resume_text))

    # 1. Keyword match (70% of score)
    job_keywords = extract_keywords(job_text, top_n=top_n)
    matched = [k for k in job_keywords if _contains(resume_lower, resume_tokens, k)]
    missing = [k for k in job_keywords if k not in matched]
    keyword_score = round(100 * len(matched) / len(job_keywords)) if job_keywords else 0

    # 2. Section check (20% of score)
    missing_sections = [s for s in EXPECTED_SECTIONS if s not in resume_lower]
    section_score = 100 * (len(EXPECTED_SECTIONS) - len(missing_sections)) / len(EXPECTED_SECTIONS)

    # 3. Basic formatting / contact checks (10% of score)
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text))
    has_phone = bool(re.search(r"\+?\d[\d\s().-]{8,}\d", resume_text))
    word_count = len(resume_text.split())
    good_length = 300 <= word_count <= 1000
    format_score = 100 * sum([has_email, has_phone, good_length]) / 3

    score = round(0.7 * keyword_score + 0.2 * section_score + 0.1 * format_score)

    # Suggestions
    suggestions = []
    if missing:
        suggestions.append("Add these job keywords where truthful: " + ", ".join(missing[:10]))
    if missing_sections:
        suggestions.append("Add clear section headings: " + ", ".join(s.title() for s in missing_sections))
    if not has_email:
        suggestions.append("Add an email address.")
    if not has_phone:
        suggestions.append("Add a phone number.")
    if word_count < 300:
        suggestions.append(f"Resume is short ({word_count} words). Aim for 300-1000 words.")
    elif word_count > 1000:
        suggestions.append(f"Resume is long ({word_count} words). Aim for 300-1000 words.")

    return AnalysisResult(
        score=score,
        keyword_score=keyword_score,
        matched_keywords=matched,
        missing_keywords=missing,
        missing_sections=missing_sections,
        suggestions=suggestions,
    )
