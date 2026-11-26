"""ATS Resume Analyzer - web application.

Run with:  streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from ats_analyzer import analyze  # noqa: E402
from ats_analyzer.jd_fetcher import JobFetchError, fetch_job_description  # noqa: E402
from ats_analyzer.parser import (  # noqa: E402
    SUPPORTED_EXTENSIONS,
    DocumentError,
    extract_text_from_bytes,
)

st.set_page_config(page_title="ATS Resume Analyzer", page_icon="📄", layout="wide")


def resume_input(key: str) -> str:
    """Let the user upload a resume file (any supported format) or paste text."""
    mode = st.radio("Resume source", ["Upload file", "Paste text"], horizontal=True, key=f"{key}_mode")
    if mode == "Paste text":
        return st.text_area("Resume text", height=250, key=f"{key}_text")

    uploaded = st.file_uploader(
        "Upload resume (" + ", ".join(SUPPORTED_EXTENSIONS) + ")",
        type=SUPPORTED_EXTENSIONS,
        key=f"{key}_file",
    )
    if not uploaded:
        return ""
    try:
        text = extract_text_from_bytes(uploaded.getvalue(), uploaded.name)
    except DocumentError as exc:
        st.error(str(exc))
        return ""
    with st.expander(f"Text read from {uploaded.name} ({len(text.split())} words)"):
        st.text(text)
    return text


@st.cache_data(show_spinner="Fetching job description...", ttl=3600)
def _fetch_jd(url: str) -> str:
    return fetch_job_description(url)


def job_input(key: str) -> str:
    """Let the user give the job description as a link, a file, or pasted text."""
    mode = st.radio(
        "Job description source", ["Paste text", "Job link (URL)", "Upload file"],
        horizontal=True, key=f"{key}_jd_mode",
    )
    if mode == "Paste text":
        return st.text_area("Job description", height=250, key=f"{key}_jd_text")

    if mode == "Job link (URL)":
        url = st.text_input("Job posting link", placeholder="https://...", key=f"{key}_jd_url")
        if not url:
            return ""
        try:
            text = _fetch_jd(url)
        except JobFetchError as exc:
            st.error(str(exc))
            return ""
    else:
        uploaded = st.file_uploader("Upload job description", type=SUPPORTED_EXTENSIONS, key=f"{key}_jd_file")
        if not uploaded:
            return ""
        try:
            text = extract_text_from_bytes(uploaded.getvalue(), uploaded.name)
        except DocumentError as exc:
            st.error(str(exc))
            return ""

    # Show the fetched text in an editable box so the user can trim it.
    st.success(f"Job description loaded ({len(text.split())} words). You can edit it below.")
    return st.text_area("Job description (editable)", value=text, height=250, key=f"{key}_jd_loaded_{hash(text)}")


def sidebar() -> None:
    with st.sidebar:
        st.title("📄 ATS Resume Analyzer")
        st.write(
            "Applicant Tracking Systems (ATS) filter resumes by keywords before a "
            "human reads them. This tool shows how your resume looks to an ATS."
        )
        st.markdown(
            "**How to use**\n"
            "1. Add your resume\n"
            "2. Add the job description\n"
            "3. Click **Analyze**\n"
            "4. Or build a tailored resume in the *Build Resume* tab"
        )


def analyze_tab() -> None:
    st.header("Analyze your resume")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Your resume")
        resume_text = resume_input("analyze")
    with col2:
        st.subheader("2. Job description")
        job_text = job_input("analyze")

    if st.button("Analyze", type="primary"):
        if not resume_text.strip() or not job_text.strip():
            st.warning("Please provide both a resume and a job description.")
            return
        result = analyze(resume_text, job_text)
        st.metric("ATS Score", f"{result.score} / 100")
        st.progress(result.score / 100)
        st.write("**Matched:**", ", ".join(result.matched_keywords) or "None")
        st.write("**Missing:**", ", ".join(result.missing_keywords) or "None")
        for tip in result.suggestions:
            st.write(f"- {tip}")


def build_tab() -> None:
    st.header("Build a resume from a job description")
    st.info("Coming in Step 5.")


def main() -> None:
    sidebar()
    tab_analyze, tab_build = st.tabs(["🔍 Analyze Resume", "🛠️ Build Resume"])
    with tab_analyze:
        analyze_tab()
    with tab_build:
        build_tab()


main()
