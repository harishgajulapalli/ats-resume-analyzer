from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


def test_app_starts_without_errors():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert len(at.tabs) == 2


def test_analyze_with_pasted_text():
    samples = Path(__file__).parent.parent / "samples"
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio(key="analyze_mode").set_value("Paste text").run()
    at.text_area(key="analyze_text").input((samples / "resume.txt").read_text()).run()
    at.text_area(key="analyze_jd_text").input((samples / "job_description.txt").read_text()).run()
    at.button[0].click().run()
    assert not at.exception
    assert at.metric[0].label == "ATS Score"
    assert "Docker" in " ".join(m.value for m in at.markdown)


def test_build_resume_flow():
    samples = Path(__file__).parent.parent / "samples"
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_area(key="build_jd_text").input((samples / "job_description.txt").read_text()).run()
    at.radio(key="build_mode").set_value("Paste text").run()
    at.text_area(key="build_text").input((samples / "resume.txt").read_text()).run()

    # Name, email and skills were pre-filled from the pasted resume.
    assert any(t.value == "Jane Doe" for t in at.text_input)
    skills = next(m for m in at.multiselect if m.label == "Job skills you have")
    assert "Django" in skills.value

    at.text_input(key="b_exp_title_0").input("Software Engineer").run()
    at.text_input(key="b_exp_company_0").input("Example Corp").run()
    at.text_input(key="b_exp_start_0").input("Jan 2021").run()
    at.text_input(key="b_exp_end_0").input("Present").run()
    at.text_area(key="b_exp_bullets_0").input("Built REST APIs in Django\nWrote pytest suites").run()
    at.button(key="b_generate").click().run()

    assert not at.exception
    assert any(m.label == "ATS Score of new resume" for m in at.metric)
    assert "Jane Doe" in " ".join(m.value for m in at.markdown)
