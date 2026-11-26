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
from ats_analyzer.resume_builder import (  # noqa: E402
    Education,
    Experience,
    Profile,
    Project,
    guess_job_title,
    prefill_from_resume,
    tailor,
    to_docx,
    to_markdown,
    to_pdf,
    to_text,
)
from ats_analyzer.skills import find_skills  # noqa: E402

st.set_page_config(page_title="ATS Resume Analyzer", page_icon="📄", layout="wide")

BANNER = Path(__file__).parent / "assets" / "banner.png"


@st.cache_data
def _banner_base64(modified: float) -> str:  # `modified` refreshes the cache when the image changes
    import base64

    return base64.b64encode(BANNER.read_bytes()).decode()


def apply_background() -> None:
    """Show the banner image at the top of the page, continue its dark-to-blue
    gradient behind the rest of the app, and put the content on a readable card."""
    image = _banner_base64(BANNER.stat().st_mtime) if BANNER.exists() else ""
    banner_css = f'url("data:image/png;base64,{image}") top center / 100% auto no-repeat,' if image else ""
    st.markdown(
        f"""
        <style>
        /* Starts with the banner's bottom-edge blue so there is no visible seam. */
        .stApp {{
            background: linear-gradient(180deg, #206fa7 0, #206fa7 40vw, #0f3a5c 100%);
        }}
        /* Banner fills the width of the main area (right of the sidebar) and
           scrolls with the page. */
        .stApp [data-testid="stMain"] {{
            background: {banner_css} transparent;
            background-attachment: local;
            container-type: inline-size;
        }}
        /* Push content below the banner (banner height = 413/1166 of its width). */
        .stApp [data-testid="stMainBlockContainer"] {{
            margin: calc(35.4cqw - 2.5rem) 1.5rem 2rem;
            width: auto;
            background: rgba(255, 255, 255, 0.94);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35);
            padding: 2rem 2.5rem;
        }}
        .stApp header[data-testid="stHeader"] {{ background: transparent; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        show_results(analyze(resume_text, job_text))


def _chips(items: list[str], color: str) -> str:
    return " ".join(f":{color}-background[{i}]" for i in items) if items else "_None_"


def show_results(result) -> None:
    st.divider()
    if result.score >= 75:
        verdict, color = "Strong match - good chance of passing ATS filters", "green"
    elif result.score >= 50:
        verdict, color = "Moderate match - improve the items below", "orange"
    else:
        verdict, color = "Weak match - resume needs tailoring for this job", "red"

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("ATS Score", f"{result.score} / 100")
        st.markdown(f":{color}[**{verdict}**]")
    with c2:
        st.markdown("**Score breakdown**")
        for part in result.parts:
            st.progress(part.score / 100, text=f"{part.name} ({part.weight}%): {part.score}/100 - {part.detail}")

    st.subheader("Skills")
    req = [s for s in result.skills if s.required]
    pref = [s for s in result.skills if not s.required]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**✅ Matched skills**")
        st.markdown("Required: " + _chips([s.name for s in req if s.found], "green"))
        st.markdown("Nice-to-have: " + _chips([s.name for s in pref if s.found], "green"))
    with c2:
        st.markdown("**❌ Missing skills**")
        st.markdown("Required: " + _chips([s.name for s in req if not s.found], "red"))
        st.markdown("Nice-to-have: " + _chips([s.name for s in pref if not s.found], "orange"))
    if result.extra_skills:
        st.caption("Other skills on your resume (not asked for in this job): " + ", ".join(result.extra_skills))

    st.subheader("Keywords")
    c1, c2 = st.columns(2)
    c1.markdown("**✅ Matched:** " + _chips(result.matched_keywords, "green"))
    c2.markdown("**❌ Missing:** " + _chips(result.missing_keywords, "red"))

    with st.expander("Full skill-by-skill table"):
        st.dataframe(
            [{"Skill": s.name, "Category": s.category,
              "Importance": "Required" if s.required else "Nice-to-have",
              "In resume": "✅" if s.found else "❌"} for s in result.skills],
            hide_index=True, width="stretch",
        )

    st.subheader("💡 Suggestions")
    if not result.suggestions:
        st.success("Your resume covers this job well. Nice work!")
    for tip in result.suggestions:
        st.markdown(f"- {tip}")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _csv(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def build_tab() -> None:
    st.header("Build a resume from a job description")
    st.caption(
        "Fill in your real details. The tool tailors wording, order and emphasis to the job "
        "and only includes skills you confirm you have."
    )

    st.subheader("1. Job description")
    job_text = job_input("build")

    st.subheader("2. Your current resume (optional)")
    with st.expander("Upload your existing resume to pre-fill name, contact and skills"):
        old_resume = resume_input("build")
    pre = prefill_from_resume(old_resume) if old_resume.strip() else {}
    pk = str(abs(hash(old_resume)) % 10**8)  # new keys when a new resume is uploaded

    if not job_text.strip():
        st.info("Add a job description above to start building.")
        return

    # ---- personal details ----
    st.subheader("3. Your details")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Full name *", value=pre.get("name", ""), key=f"b_name_{pk}")
    email = c2.text_input("Email *", value=pre.get("email", ""), key=f"b_email_{pk}")
    phone = c3.text_input("Phone *", value=pre.get("phone", ""), key=f"b_phone_{pk}")
    c1, c2, c3 = st.columns(3)
    location = c1.text_input("Location", placeholder="City, Country", key="b_location")
    links = c2.text_input("Links (comma separated)", value=", ".join(pre.get("links", [])),
                          placeholder="linkedin.com/in/you, github.com/you", key=f"b_links_{pk}")
    title = c3.text_input("Target job title", value=guess_job_title(job_text), key="b_title")

    # ---- skills ----
    st.subheader("4. Skills")
    job_skills = find_skills(job_text)
    have = set(pre.get("skills", []))
    st.write("These skills are in the job description. **Keep only the ones you really have:**")
    chosen = st.multiselect(
        "Job skills you have", options=sorted(job_skills),
        default=sorted(s for s in job_skills if s in have), key=f"b_skills_{pk}",
    )
    other = st.text_input(
        "Other skills you have (comma separated)",
        value=", ".join(sorted(have - set(job_skills))), key=f"b_other_{pk}",
    )
    skills = chosen + [s for s in _csv(other) if s not in chosen]

    # ---- experience ----
    st.subheader("5. Experience")
    n_exp = st.number_input("Number of jobs / internships", 0, 8, 1, key="b_n_exp")
    experience = []
    for i in range(int(n_exp)):
        with st.expander(f"Job {i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            job_title = c1.text_input("Job title", key=f"b_exp_title_{i}")
            company = c2.text_input("Company", key=f"b_exp_company_{i}")
            c1, c2, c3 = st.columns(3)
            start = c1.text_input("Start (e.g. Jan 2022)", key=f"b_exp_start_{i}")
            end = c2.text_input("End (e.g. Present)", key=f"b_exp_end_{i}")
            loc = c3.text_input("Location", key=f"b_exp_loc_{i}")
            bullets = st.text_area(
                "What you did - one point per line. Start with an action verb and add numbers "
                "(e.g. 'Built REST APIs in Django serving 1M requests/day')",
                key=f"b_exp_bullets_{i}", height=120,
            )
            experience.append(Experience(job_title, company, start, end, loc, _lines(bullets)))

    # ---- projects ----
    st.subheader("6. Projects")
    n_proj = st.number_input("Number of projects", 0, 6, 0, key="b_n_proj")
    projects = []
    for i in range(int(n_proj)):
        with st.expander(f"Project {i + 1}", expanded=True):
            c1, c2 = st.columns(2)
            pname = c1.text_input("Project name", key=f"b_proj_name_{i}")
            tech = c2.text_input("Technologies used", key=f"b_proj_tech_{i}")
            pbul = st.text_area("Description - one point per line", key=f"b_proj_bullets_{i}", height=90)
            projects.append(Project(pname, tech, _lines(pbul)))

    # ---- education & certifications ----
    st.subheader("7. Education & certifications")
    n_edu = st.number_input("Number of degrees", 0, 4, 1, key="b_n_edu")
    education = []
    for i in range(int(n_edu)):
        c1, c2, c3 = st.columns([2, 2, 1])
        degree = c1.text_input("Degree", placeholder="B.Tech in Computer Science", key=f"b_edu_degree_{i}")
        school = c2.text_input("College / University", key=f"b_edu_school_{i}")
        year = c3.text_input("Year", key=f"b_edu_year_{i}")
        education.append(Education(degree, school, year))
    certs = st.text_area("Certifications - one per line (optional)", key="b_certs", height=80)

    st.subheader("8. Summary")
    summary = st.text_area("Write your own summary, or leave empty to auto-generate one", key="b_summary")

    # Honest tip: skills claimed but never shown in any bullet point.
    all_bullets = " ".join(b for e in experience for b in e.bullets) + " " + \
        " ".join(b for p in projects for b in [p.tech, *p.bullets])
    unshown = [s for s in chosen if s not in find_skills(all_bullets)]
    if chosen and unshown and all_bullets.strip():
        st.info("Tip: ATS and recruiters trust skills more when a bullet point shows where you used them. "
                "Consider mentioning: " + ", ".join(unshown))

    if st.button("✨ Generate tailored resume", type="primary", key="b_generate"):
        missing = [label for label, v in [("Full name", name), ("Email", email), ("Phone", phone)] if not v.strip()]
        if missing:
            st.warning("Please fill in: " + ", ".join(missing))
            return
        profile = Profile(
            name=name, email=email, phone=phone, location=location, links=_csv(links), title=title,
            summary=summary, skills=skills, experience=experience, education=education,
            projects=projects, certifications=_lines(certs),
        )
        st.session_state["built_resume"] = tailor(profile, job_text)
        st.session_state["built_for_job"] = job_text

    resume = st.session_state.get("built_resume")
    if resume and st.session_state.get("built_for_job") == job_text:
        show_built_resume(resume, job_text)


def show_built_resume(resume, job_text: str) -> None:
    st.divider()
    st.subheader("Your tailored resume")
    result = analyze(to_text(resume), job_text)
    c1, c2 = st.columns([1, 3])
    c1.metric("ATS Score of new resume", f"{result.score} / 100")
    if result.missing_skills:
        c2.markdown("Job skills still missing (add only if true): " + _chips(result.missing_skills, "red"))

    safe_name = "".join(ch for ch in resume.name if ch.isalnum()) or "resume"
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Download Word (.docx)", to_docx(resume), f"{safe_name}_Resume.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    c2.download_button("⬇️ Download PDF", to_pdf(resume), f"{safe_name}_Resume.pdf", "application/pdf")
    c3.download_button("⬇️ Download text (.txt)", to_text(resume), f"{safe_name}_Resume.txt", "text/plain")

    with st.container(border=True):
        st.markdown(to_markdown(resume))


def main() -> None:
    apply_background()
    sidebar()
    tab_analyze, tab_build = st.tabs(["🔍 Analyze Resume", "🛠️ Build Resume"])
    with tab_analyze:
        analyze_tab()
    with tab_build:
        build_tab()


main()
