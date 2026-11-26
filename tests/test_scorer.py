import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ats_analyzer import analyze  # noqa: E402
from ats_analyzer.sections import education_levels, split_sections, years_from_dates  # noqa: E402
from ats_analyzer.skills import find_skills  # noqa: E402

SAMPLES = Path(__file__).parent.parent / "samples"


def load(name):
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_sample_resume_matches_and_misses():
    result = analyze(load("resume.txt"), load("job_description.txt"))
    assert 0 <= result.score <= 100
    assert {"Python", "Django", "PostgreSQL", "CI/CD"} <= set(result.matched_skills)
    assert {"FastAPI", "AWS", "Docker"} <= set(result.missing_skills)
    assert result.required_years == 3
    assert result.resume_years >= 3


def test_empty_resume_scores_low():
    result = analyze("", "Python developer with Django and AWS experience")
    assert result.score < 20
    assert "Python" in result.missing_skills


def test_strong_resume_beats_weak_resume():
    job = load("job_description.txt")
    strong = load("resume.txt") + "\nAlso: FastAPI, AWS, Docker, Kubernetes"
    weak = "John\njohn@example.com\nSkills\nExcel, Communication"
    assert analyze(strong, job).score > analyze(weak, job).score + 20


def test_aliases_match():
    found = find_skills("Built services on k8s with Postgres and JS, deployed via GitHub Actions")
    assert {"Kubernetes", "PostgreSQL", "JavaScript", "GitHub Actions"} <= set(found)


def test_no_false_positives():
    found = find_skills("I will go to the store. JavaScript only. Rest well.")
    assert "Go" not in found
    assert "Java" not in found
    assert "REST APIs" not in found


def test_preferred_skills_marked():
    job = "Requirements:\n- Python and Django\nNice to have:\n- Kubernetes\n- Terraform"
    result = analyze("Python", job)
    required = {s.name: s.required for s in result.skills}
    assert required["Python"] and required["Django"]
    assert not required["Kubernetes"] and not required["Terraform"]


def test_years_from_dates_merges_overlaps():
    text = "Jan 2020 - Dec 2021\nJun 2021 - Dec 2022"
    assert years_from_dates(text) == 3.0
    assert years_from_dates("2022 - Present", today=date(2024, 1, 1)) == 2.0


def test_sections_and_education():
    sections = split_sections("Jane\nSUMMARY\nHi\nWork Experience:\nDev\nEducation\nB.Tech CSE")
    assert {"summary", "experience", "education"} <= set(sections)
    assert max(education_levels("M.Tech in CS"))[1] == "Master's"
