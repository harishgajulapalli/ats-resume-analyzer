"""Step 5: Build an ATS-friendly resume tailored to a job description.

The user supplies their real details and confirms which of the job's skills
they actually have. We never invent skills or experience - we only choose
wording, ordering and emphasis so the resume lines up with the job.
"""

import io
import re
from dataclasses import dataclass, field

from .keywords import stem, tokenize
from .sections import years_from_dates
from .skills import SKILLS, find_skills


@dataclass
class Experience:
    title: str
    company: str
    start: str = ""
    end: str = ""
    location: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class Education:
    degree: str
    school: str
    year: str = ""
    details: str = ""


@dataclass
class Project:
    name: str
    tech: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class Profile:
    """What the user tells us about themselves."""
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] = field(default_factory=list)
    title: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)


@dataclass
class Resume:
    """The final, tailored resume ready to export."""
    name: str
    contact: list[str]
    title: str
    summary: str
    skills: dict[str, list[str]]
    experience: list[Experience]
    education: list[Education]
    projects: list[Project]
    certifications: list[str]


# ---------------------------------------------------------------------------
# Helpers to pre-fill the form
# ---------------------------------------------------------------------------

def guess_job_title(job_text: str) -> str:
    """The first short line of a job description is usually the job title."""
    for line in job_text.splitlines():
        line = line.strip(" \t#*:-")
        if line and len(line.split()) <= 8 and not line.endswith("."):
            return line
    return ""


def prefill_from_resume(resume_text: str) -> dict:
    """Pull name, email, phone and skills from an existing resume."""
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text)
    phone = re.search(r"\+?\d[\d\s().-]{8,}\d", resume_text)
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)/[\w/-]+", resume_text)
    name = lines[0] if lines and len(lines[0].split()) <= 5 and "@" not in lines[0] else ""
    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else "",
        "links": list(dict.fromkeys(links)),
        "skills": list(find_skills(resume_text)),
    }


# ---------------------------------------------------------------------------
# Tailoring
# ---------------------------------------------------------------------------

def _relevance(text: str, job_stems: set[str], job_skills: set[str]) -> int:
    """How strongly a piece of text relates to the job (higher = more relevant)."""
    skill_hits = len(set(find_skills(text)) & job_skills)
    word_hits = len({stem(t) for t in tokenize(text)} & job_stems)
    return skill_hits * 3 + word_hits


def tailor(profile: Profile, job_text: str) -> Resume:
    job_skills = set(find_skills(job_text))
    job_stems = {stem(t) for t in tokenize(job_text) if len(t) > 3}

    # Skills: group by category, job-relevant ones first, then the rest.
    category_of = {name: cat for cat, skills in SKILLS.items() for name in skills}
    grouped: dict[str, list[str]] = {}
    ordered = sorted(dict.fromkeys(profile.skills), key=lambda s: (s not in job_skills, s.lower()))
    for skill in ordered:
        grouped.setdefault(category_of.get(skill, "Other Skills"), []).append(skill)
    category_order = list(SKILLS) + ["Other Skills"]
    grouped = dict(sorted(
        grouped.items(),
        key=lambda kv: (-sum(s in job_skills for s in kv[1]), category_order.index(kv[0])),
    ))

    # Experience & projects: put the most job-relevant bullet points first.
    def sort_bullets(bullets: list[str]) -> list[str]:
        cleaned = [_tidy_bullet(b) for b in bullets if b.strip()]
        return sorted(cleaned, key=lambda b: -_relevance(b, job_stems, job_skills))

    experience = [
        Experience(e.title, e.company, e.start, e.end, e.location, sort_bullets(e.bullets))
        for e in profile.experience if e.title or e.company
    ]
    projects = sorted(
        [Project(p.name, p.tech, sort_bullets(p.bullets)) for p in profile.projects if p.name],
        key=lambda p: -_relevance(" ".join([p.tech, *p.bullets]), job_stems, job_skills),
    )

    title = profile.title or guess_job_title(job_text) or "Professional"
    summary = profile.summary.strip() or _write_summary(profile, title, job_skills)
    contact = [c for c in [profile.email, profile.phone, profile.location, *profile.links] if c]

    return Resume(
        name=profile.name.strip(),
        contact=contact,
        title=title,
        summary=summary,
        skills=grouped,
        experience=experience,
        education=[e for e in profile.education if e.degree or e.school],
        projects=projects,
        certifications=[c for c in profile.certifications if c.strip()],
    )


def total_years(experience: list[Experience]) -> float:
    return years_from_dates("\n".join(f"{e.start} - {e.end}" for e in experience if e.start))


def _write_summary(profile: Profile, title: str, job_skills: set[str]) -> str:
    soft = set(SKILLS["Soft Skills"])
    tech = [s for s in profile.skills if s in job_skills and s not in soft]
    tech += [s for s in profile.skills if s not in job_skills and s not in soft]
    soft_have = [s.lower() for s in profile.skills if s in soft]
    years = int(total_years(profile.experience))

    # Describe the person by their real most recent title (not the job's title).
    recent = next((e for e in profile.experience if e.title), None)
    who = recent.title if recent else title
    opening = f"{who} with {years}+ years of experience" if years >= 1 else f"Motivated {who}"
    parts = []
    if tech:
        parts.append(f"{opening} working with {_join(tech[:4])}.")
    else:
        parts.append(f"{opening}.")
    if len(tech) > 4:
        parts.append(f"Hands-on with {_join(tech[4:8])}.")
    if recent and recent.company:
        current = recent.end.strip().lower() in ("", "present", "current", "now", "till date", "today")
        parts.append(f"{'Currently' if current else 'Most recently'} {_article(recent.title)} "
                     f"{recent.title} at {recent.company}.")
    if soft_have:
        parts.append(f"Known for strong {_join(soft_have[:3])}.")
    return " ".join(parts)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def _tidy_bullet(text: str) -> str:
    text = re.sub(r"^[\s\-*•●▪◦–·]+", "", text).strip()
    # Capitalize the first letter, but leave words like "iOS" or "eBay" alone.
    if text and text[0].islower() and not (len(text) > 1 and text[1].isupper()):
        text = text[0].upper() + text[1:]
    return text


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _dates(start: str, end: str) -> str:
    return " - ".join(x for x in [start, end] if x)


def to_text(r: Resume) -> str:
    """Plain text version (also used to score the generated resume)."""
    out = [r.name, " | ".join(r.contact), r.title, "", "SUMMARY", r.summary, "", "SKILLS"]
    out += [f"{cat}: {', '.join(skills)}" for cat, skills in r.skills.items()]
    if r.experience:
        out += ["", "EXPERIENCE"]
        for e in r.experience:
            out.append(" | ".join(x for x in [f"{e.title}, {e.company}", e.location, _dates(e.start, e.end)] if x))
            out += [f"- {b}" for b in e.bullets]
            out.append("")
    if r.projects:
        out += ["", "PROJECTS"]
        for p in r.projects:
            out.append(p.name + (f" ({p.tech})" if p.tech else ""))
            out += [f"- {b}" for b in p.bullets]
    if r.education:
        out += ["", "EDUCATION"]
        for ed in r.education:
            out.append(" | ".join(x for x in [ed.degree, ed.school, ed.year] if x))
            if ed.details:
                out.append(ed.details)
    if r.certifications:
        out += ["", "CERTIFICATIONS"] + [f"- {c}" for c in r.certifications]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def to_markdown(r: Resume) -> str:
    md = [f"## {r.name}", " | ".join(r.contact), f"**{r.title}**", "", "#### Summary", r.summary, "", "#### Skills"]
    md += [f"- **{cat}:** {', '.join(s)}" for cat, s in r.skills.items()]
    if r.experience:
        md += ["", "#### Experience"]
        for e in r.experience:
            md.append(f"**{e.title}**, {e.company}" + (f" - {e.location}" if e.location else "")
                      + (f"  \n_{_dates(e.start, e.end)}_" if e.start or e.end else ""))
            md += [f"- {b}" for b in e.bullets] + [""]
    if r.projects:
        md += ["#### Projects"]
        for p in r.projects:
            md.append(f"**{p.name}**" + (f" _({p.tech})_" if p.tech else ""))
            md += [f"- {b}" for b in p.bullets] + [""]
    if r.education:
        md += ["#### Education"]
        md += [f"**{ed.degree}**, {ed.school}" + (f" ({ed.year})" if ed.year else "")
               + (f"  \n{ed.details}" if ed.details else "") for ed in r.education]
    if r.certifications:
        md += ["", "#### Certifications"] + [f"- {c}" for c in r.certifications]
    return "\n".join(md)


def to_docx(r: Resume) -> bytes:
    """Single-column Word file with standard headings - the format ATS parse best."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    for section in doc.sections:
        section.left_margin = section.right_margin = Pt(54)
        section.top_margin = section.bottom_margin = Pt(48)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = name.add_run(r.name)
    run.bold = True
    run.font.size = Pt(20)
    for line in (" | ".join(r.contact), r.title):
        p = doc.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def heading(text):
        doc.add_heading(text, level=2)

    def bullets(items):
        for b in items:
            doc.add_paragraph(b, style="List Bullet")

    def entry(bold_text, rest=""):
        p = doc.add_paragraph()
        p.add_run(bold_text).bold = True
        if rest:
            p.add_run(rest)

    heading("Summary")
    doc.add_paragraph(r.summary)
    heading("Skills")
    for cat, skills in r.skills.items():
        entry(f"{cat}: ", ", ".join(skills))
    if r.experience:
        heading("Experience")
        for e in r.experience:
            entry(f"{e.title}, {e.company}",
                  "".join(f" | {x}" for x in [e.location, _dates(e.start, e.end)] if x))
            bullets(e.bullets)
    if r.projects:
        heading("Projects")
        for p in r.projects:
            entry(p.name, f" ({p.tech})" if p.tech else "")
            bullets(p.bullets)
    if r.education:
        heading("Education")
        for ed in r.education:
            entry(ed.degree, "".join(f" | {x}" for x in [ed.school, ed.year] if x))
            if ed.details:
                doc.add_paragraph(ed.details)
    if r.certifications:
        heading("Certifications")
        bullets(r.certifications)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


_PDF_REPLACEMENTS = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                     "—": "-", "•": "-", "…": "...", " ": " ", "→": "->"}


def _latin1(text: str) -> str:
    for a, b in _PDF_REPLACEMENTS.items():
        text = text.replace(a, b)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def to_pdf(r: Resume) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()
    full = dict(w=0, new_x="LMARGIN", new_y="NEXT")

    def write(text, size=10.5, style="", align="L", h=5.5):
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(text=_latin1(text), h=h, align=align, **full)

    def heading(text):
        pdf.ln(3)
        write(text.upper(), size=12, style="B", h=6)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(1.5)

    def bullets(items):
        for b in items:
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font("Helvetica", "", 10.5)
            pdf.multi_cell(text=_latin1(f"- {b}"), h=5.5, w=pdf.w - pdf.l_margin - pdf.r_margin - 4,
                           new_x="LMARGIN", new_y="NEXT")

    write(r.name, size=20, style="B", align="C", h=9)
    write(" | ".join(r.contact), size=10, align="C")
    write(r.title, size=11, style="B", align="C")

    heading("Summary")
    write(r.summary)
    heading("Skills")
    for cat, skills in r.skills.items():
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(text=_latin1(f"**{cat}:** {', '.join(skills)}"), h=5.5, markdown=True, **full)
    if r.experience:
        heading("Experience")
        for e in r.experience:
            write(f"{e.title}, {e.company}", style="B")
            meta = " | ".join(x for x in [e.location, _dates(e.start, e.end)] if x)
            if meta:
                write(meta, size=9.5, style="I")
            bullets(e.bullets)
            pdf.ln(1.5)
    if r.projects:
        heading("Projects")
        for p in r.projects:
            write(p.name + (f" ({p.tech})" if p.tech else ""), style="B")
            bullets(p.bullets)
            pdf.ln(1.5)
    if r.education:
        heading("Education")
        for ed in r.education:
            write(ed.degree, style="B")
            write(" | ".join(x for x in [ed.school, ed.year] if x))
            if ed.details:
                write(ed.details, size=10)
    if r.certifications:
        heading("Certifications")
        bullets(r.certifications)
    return bytes(pdf.output())
