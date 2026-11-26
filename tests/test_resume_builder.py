import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ats_analyzer import analyze  # noqa: E402
from ats_analyzer.parser import extract_text_from_bytes  # noqa: E402
from ats_analyzer.resume_builder import (  # noqa: E402
    Education,
    Experience,
    Profile,
    Project,
    guess_job_title,
    prefill_from_resume,
    tailor,
    to_docx,
    to_pdf,
    to_text,
)

SAMPLES = Path(__file__).parent.parent / "samples"
JOB = (SAMPLES / "job_description.txt").read_text(encoding="utf-8")


def make_profile(**overrides) -> Profile:
    data = dict(
        name="Jane Doe",
        email="jane@example.com",
        phone="+1 555 123 4567",
        skills=["Python", "Django", "Docker", "AWS", "Excel", "Communication"],
        experience=[Experience(
            "Software Engineer", "Example Corp", "Jan 2021", "Present",
            bullets=["organized team lunches", "- built REST APIs in Django deployed with Docker on AWS"],
        )],
        education=[Education("B.Tech Computer Science", "Example University", "2020")],
        projects=[
            Project("Photo app", "Swift", ["iOS photo filters"]),
            Project("API toolkit", "Python, FastAPI", ["Python library for building REST APIs"]),
        ],
    )
    data.update(overrides)
    return Profile(**data)


def test_guess_job_title():
    assert guess_job_title(JOB) == "Backend Python Developer"


def test_prefill_from_resume():
    data = prefill_from_resume((SAMPLES / "resume.txt").read_text(encoding="utf-8"))
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane.doe@example.com"
    assert "Django" in data["skills"]


def test_tailor_orders_by_relevance():
    r = tailor(make_profile(), JOB)
    assert r.title == "Backend Python Developer"
    assert r.experience[0].bullets[0].startswith("Built REST APIs")  # relevant first, dash removed
    assert r.projects[0].name == "API toolkit"
    first_category = next(iter(r.skills))
    assert first_category in ("Programming Languages", "Frameworks & Libraries", "Cloud & DevOps")
    assert "Excel" in r.skills["Data & AI"]  # non-job skills kept, but later


def test_summary_is_generated_and_honest():
    r = tailor(make_profile(), JOB)
    assert "years of experience" in r.summary
    assert "Python" in r.summary
    assert "Kubernetes" not in r.summary  # never adds skills the user didn't confirm


def test_user_summary_is_kept():
    assert tailor(make_profile(summary="My own words."), JOB).summary == "My own words."


def test_generated_resume_scores_better_than_bare_input():
    r = tailor(make_profile(), JOB)
    bare = "Jane Doe\nSoftware Engineer\nbuilt REST APIs"
    assert analyze(to_text(r), JOB).score > analyze(bare, JOB).score


def test_docx_and_pdf_are_readable_by_ats_parser():
    r = tailor(make_profile(), JOB)
    for data, name in [(to_docx(r), "out.docx"), (to_pdf(r), "out.pdf")]:
        text = extract_text_from_bytes(data, name)
        assert "Jane Doe" in text
        assert "Example Corp" in text
        assert "Django" in text


def test_summary_uses_real_title_and_keeps_brand_casing():
    r = tailor(make_profile(), JOB)
    assert r.summary.startswith("Software Engineer with")
    assert "Currently a Software Engineer at Example Corp." in r.summary
    assert r.title == "Backend Python Developer"  # headline still matches the job
    photo = next(p for p in r.projects if p.name == "Photo app")
    assert photo.bullets[0] == "iOS photo filters"
