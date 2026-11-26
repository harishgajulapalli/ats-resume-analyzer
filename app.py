"""Web app: upload a resume, paste a job description, get an ATS score.

Run with:  streamlit run app.py
"""

import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from ats_analyzer import analyze  # noqa: E402
from ats_analyzer.parser import extract_text  # noqa: E402

st.set_page_config(page_title="ATS Resume Analyzer", page_icon="📄")
st.title("📄 ATS Resume Analyzer")
st.write("Upload your resume and paste a job description to see how well they match.")

uploaded = st.file_uploader("Resume", type=["pdf", "docx", "txt"])
job_text = st.text_area("Job description", height=250)

if st.button("Analyze", type="primary"):
    if not uploaded or not job_text.strip():
        st.warning("Please upload a resume and paste a job description.")
        st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix) as tmp:
        tmp.write(uploaded.getvalue())
    resume_text = extract_text(tmp.name)

    result = analyze(resume_text, job_text)

    st.metric("ATS Score", f"{result.score} / 100")
    st.progress(result.score / 100)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Matched keywords")
        st.write(", ".join(result.matched_keywords) or "None")
    with col2:
        st.subheader("❌ Missing keywords")
        st.write(", ".join(result.missing_keywords) or "None")

    st.subheader("💡 Suggestions")
    for tip in result.suggestions:
        st.write(f"- {tip}")
