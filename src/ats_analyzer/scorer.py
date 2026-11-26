"""Step 4: Validate a resume against a job description.

Produces matched / missing skills and keywords, experience and education
checks, a 0-100 score with a breakdown, and improvement suggestions.
"""

import re
from dataclasses import dataclass, field

from .keywords import extract_keywords, stem, tokenize
from .sections import (
    REQUIRED_SECTIONS,
    education_levels,
    split_sections,
    years_from_dates,
    years_stated,
)
from .skills import find_skills, skill_words

PREFERRED_HINTS = re.compile(r"prefer|nice to have|nice-to-have|bonus|plus|good to have|desirable|optional", re.I)

# How much each part counts toward the final score (normalized when a part
# doesn't apply, e.g. the job lists no years of experience).
WEIGHTS = {
    "Skills": 50,
    "Keywords": 15,
    "Experience": 10,
    "Education": 5,
    "Sections": 12,
    "Contact & Length": 8,
}


@dataclass
class SkillMatch:
    name: str
    category: str
    required: bool  # False = "preferred / nice to have"
    found: bool


@dataclass
class ScorePart:
    name: str
    score: int
    weight: int
    detail: str


@dataclass
class AnalysisResult:
    score: int
    parts: list[ScorePart] = field(default_factory=list)
    skills: list[SkillMatch] = field(default_factory=list)
    extra_skills: list[str] = field(default_factory=list)  # in resume, not asked for
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    required_years: int | None = None
    resume_years: float = 0.0
    required_education: str | None = None
    resume_education: str | None = None
    missing_sections: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def matched_skills(self) -> list[str]:
        return [s.name for s in self.skills if s.found]

    @property
    def missing_skills(self) -> list[str]:
        return [s.name for s in self.skills if not s.found]


def analyze(resume_text: str, job_text: str) -> AnalysisResult:
    result = AnalysisResult(score=0)
    parts: list[ScorePart] = []

    # ---- 1. Skills ---------------------------------------------------------
    job_skills = find_skills(job_text)
    resume_skills = find_skills(resume_text)
    preferred = _preferred_skills(job_text)
    for name, category in job_skills.items():
        result.skills.append(SkillMatch(name, category, name not in preferred, name in resume_skills))
    result.skills.sort(key=lambda s: (not s.required, s.category, s.name))
    result.extra_skills = sorted(set(resume_skills) - set(job_skills))
    if result.skills:
        total = sum(1.0 if s.required else 0.5 for s in result.skills)
        got = sum(1.0 if s.required else 0.5 for s in result.skills if s.found)
        parts.append(ScorePart("Skills", round(100 * got / total), WEIGHTS["Skills"],
                               f"{len(result.matched_skills)} of {len(result.skills)} skills found"))

    # ---- 2. Other keywords -------------------------------------------------
    ignore = skill_words()
    keywords = [k for k in extract_keywords(job_text, top_n=40)
                if not any(w in ignore for w in k.split())][:20]
    resume_stems = {stem(t) for t in tokenize(resume_text)}
    resume_lower = resume_text.lower()
    for k in keywords:
        found = (k in resume_lower) if " " in k else (stem(k) in resume_stems)
        (result.matched_keywords if found else result.missing_keywords).append(k)
    if keywords:
        parts.append(ScorePart("Keywords", round(100 * len(result.matched_keywords) / len(keywords)),
                               WEIGHTS["Keywords"], f"{len(result.matched_keywords)} of {len(keywords)} keywords found"))

    # ---- 3. Experience -----------------------------------------------------
    sections = split_sections(resume_text)
    stated_job = years_stated(job_text)
    result.required_years = max(stated_job) if stated_job else None
    exp_text = sections.get("experience", "")
    result.resume_years = max([years_from_dates(exp_text), *years_stated(sections.get("summary", "") + "\n" + sections.get("header", ""))], default=0)
    if result.required_years:
        ratio = min(1.0, result.resume_years / result.required_years)
        parts.append(ScorePart("Experience", round(100 * ratio), WEIGHTS["Experience"],
                               f"{result.resume_years:g} yrs found vs {result.required_years}+ required"))

    # ---- 4. Education ------------------------------------------------------
    job_edu = education_levels(job_text)
    resume_edu = education_levels(sections.get("education", "") or resume_text)
    if job_edu:
        need_level, result.required_education = min(job_edu)
        have_level, result.resume_education = max(resume_edu) if resume_edu else (0, None)
        parts.append(ScorePart("Education", 100 if have_level >= need_level else 0, WEIGHTS["Education"],
                               f"{result.resume_education or 'Not found'} vs {result.required_education} required"))

    # ---- 5. Sections -------------------------------------------------------
    result.missing_sections = [s for s in REQUIRED_SECTIONS if s not in sections]
    have = len(REQUIRED_SECTIONS) - len(result.missing_sections)
    parts.append(ScorePart("Sections", round(100 * have / len(REQUIRED_SECTIONS)), WEIGHTS["Sections"],
                           f"{have} of {len(REQUIRED_SECTIONS)} standard sections"))

    # ---- 6. Contact info & length -----------------------------------------
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text))
    has_phone = bool(re.search(r"\+?\d[\d\s().-]{8,}\d", resume_text))
    words = len(resume_text.split())
    good_length = 250 <= words <= 1000
    checks = [has_email, has_phone, good_length]
    parts.append(ScorePart("Contact & Length", round(100 * sum(checks) / 3), WEIGHTS["Contact & Length"],
                           f"email {'✓' if has_email else '✗'}, phone {'✓' if has_phone else '✗'}, {words} words"))

    # ---- Final score -------------------------------------------------------
    total_weight = sum(p.weight for p in parts)
    result.score = round(sum(p.score * p.weight for p in parts) / total_weight)
    result.parts = parts

    # ---- Suggestions -------------------------------------------------------
    tips = result.suggestions
    missing_req = [s.name for s in result.skills if s.required and not s.found]
    missing_pref = [s.name for s in result.skills if not s.required and not s.found]
    if missing_req:
        tips.append("Add these required skills (only if you really have them): " + ", ".join(missing_req))
    if missing_pref:
        tips.append("Nice-to-have skills you could mention: " + ", ".join(missing_pref))
    if result.missing_keywords:
        tips.append("Use these words from the job description in your bullet points: "
                    + ", ".join(result.missing_keywords[:10]))
    if result.required_years and result.resume_years < result.required_years:
        tips.append(f"The job asks for {result.required_years}+ years. Show dates (e.g. 'Jan 2021 - Present') "
                    "for every role so ATS can count your experience.")
    if result.required_education and not result.resume_education:
        tips.append(f"Mention your degree clearly (job asks for {result.required_education}).")
    if result.missing_sections:
        tips.append("Add section headings: " + ", ".join(s.title() for s in result.missing_sections))
    if not has_email:
        tips.append("Add an email address at the top.")
    if not has_phone:
        tips.append("Add a phone number at the top.")
    if words < 250:
        tips.append(f"Your resume is short ({words} words). Aim for 250-1000 words.")
    elif words > 1000:
        tips.append(f"Your resume is long ({words} words). Aim for 250-1000 words.")
    return result


def _preferred_skills(job_text: str) -> set[str]:
    """Skills that only appear on 'preferred / nice to have / bonus' lines."""
    preferred_lines, required_lines = [], []
    in_preferred_block = False
    for line in job_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        is_heading = len(stripped.split()) <= 6 and stripped.endswith(":")
        if is_heading:
            in_preferred_block = bool(PREFERRED_HINTS.search(stripped))
        if in_preferred_block or PREFERRED_HINTS.search(stripped):
            preferred_lines.append(stripped)
        else:
            required_lines.append(stripped)
    preferred = set(find_skills("\n".join(preferred_lines)))
    required = set(find_skills("\n".join(required_lines)))
    return preferred - required
