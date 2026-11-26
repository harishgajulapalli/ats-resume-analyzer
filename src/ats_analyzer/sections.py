"""Split a resume into sections (Summary, Experience, ...) and read dates."""

import re
from datetime import date

SECTION_NAMES = {
    "summary": ["summary", "profile", "objective", "about me", "professional summary", "career objective"],
    "experience": ["experience", "work experience", "employment", "work history",
                   "professional experience", "employment history", "internships", "internship"],
    "education": ["education", "academic", "academics", "qualifications", "educational qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack", "key skills"],
    "projects": ["projects", "personal projects", "academic projects", "key projects"],
    "certifications": ["certifications", "certificates", "licenses", "courses"],
}
REQUIRED_SECTIONS = ["summary", "experience", "education", "skills"]


def split_sections(text: str) -> dict[str, str]:
    """Return {section name: text} using short heading lines like 'Experience:'."""
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        heading = re.sub(r"[^a-z ]", "", line.lower()).strip()
        found = None
        if heading and len(heading.split()) <= 4:
            for name, synonyms in SECTION_NAMES.items():
                if heading in synonyms:
                    found = name
                    break
        if found:
            current = found
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_MONTH = r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*)?"
_NUM_MONTH = r"(?:(\d{1,2})[/.-])?"
DATE_RANGE = re.compile(
    rf"{_MONTH}{_NUM_MONTH}((?:19|20)\d{{2}})\s*(?:-|–|—|to|till|until)\s*"
    rf"{_MONTH}{_NUM_MONTH}((?:19|20)\d{{2}}|present|current|now|today|date)",
    re.IGNORECASE,
)


def years_from_dates(text: str, today: date | None = None) -> float:
    """Total years covered by date ranges like 'Jan 2020 - Present' (overlaps merged)."""
    today = today or date.today()
    intervals = []
    for m in DATE_RANGE.finditer(text):
        m1, n1, y1, m2, n2, y2 = m.groups()
        start = int(y1) + ((MONTHS.get((m1 or "")[:3].lower()) or int(n1 or 1)) - 1) / 12
        if y2.isdigit():
            # End month counts fully ("Dec 2021" means through end of December).
            end = int(y2) + (MONTHS.get((m2 or "")[:3].lower()) or int(n2 or 12)) / 12
        else:
            end = today.year + (today.month - 1) / 12
        if end > start:
            intervals.append((start, end))

    total, last_end = 0.0, None
    for start, end in sorted(intervals):
        if last_end is not None and start < last_end:
            start = last_end
        if end > start:
            total += end - start
            last_end = end if last_end is None else max(last_end, end)
    return round(total, 1)


YEARS_STATED = re.compile(r"(\d{1,2})(?:\.\d)?\s*\+?\s*(?:-|to)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def years_stated(text: str) -> list[int]:
    """Numbers in phrases like '3+ years', '3-5 yrs' (lower bound of ranges)."""
    return [int(n) for n in YEARS_STATED.findall(text) if 0 < int(n) <= 30]


EDUCATION_LEVELS = [
    (4, "PhD", r"ph\.?\s?d|doctorate|doctoral"),
    (3, "Master's", r"master'?s?|m\.?\s?s\b|m\.?\s?sc|m\.?\s?tech|m\.?\s?e\b|mba|mca|post\s?graduate"),
    (2, "Bachelor's", r"bachelor'?s?|b\.?\s?s\b|b\.?\s?sc|b\.?\s?tech|b\.?\s?e\b|b\.?\s?a\b|bca|b\.?\s?com|undergraduate|graduate degree|degree in"),
    (1, "Diploma", r"diploma|associate'?s? degree"),
]


def education_levels(text: str) -> list[tuple[int, str]]:
    found = []
    for level, label, pattern in EDUCATION_LEVELS:
        if re.search(rf"(?<![a-z]){pattern}", text, re.IGNORECASE):
            found.append((level, label))
    return found
