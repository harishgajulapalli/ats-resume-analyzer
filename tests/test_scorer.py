import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ats_analyzer import analyze  # noqa: E402

SAMPLES = Path(__file__).parent.parent / "samples"


def test_sample_resume_scores_well():
    resume = (SAMPLES / "resume.txt").read_text(encoding="utf-8")
    job = (SAMPLES / "job_description.txt").read_text(encoding="utf-8")
    result = analyze(resume, job)
    assert 0 <= result.score <= 100
    assert "python" in result.matched_keywords


def test_empty_resume_scores_low():
    result = analyze("", "Python developer with Django and AWS experience")
    assert result.score < 20
    assert "python" in result.missing_keywords
