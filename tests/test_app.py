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
