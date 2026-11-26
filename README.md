# ATS Resume Analyzer

Check how well your resume matches a job, the way an Applicant Tracking System
(ATS) would, and build a resume tailored to that job.

## Features

| # | Feature | Where in code |
|---|---|---|
| 1 | Web app with **Analyze Resume** and **Build Resume** tabs | `app.py` |
| 2 | Reads resumes in **PDF, Word (.docx and old .doc), RTF, ODT, HTML, Markdown, TXT** | `src/ats_analyzer/parser.py` |
| 3 | Job description from a **link (URL)**, an uploaded file, or pasted text | `src/ats_analyzer/jd_fetcher.py` |
| 4 | **Matched vs missing** skills and keywords, experience and education checks, **score out of 100** with breakdown and suggestions | `src/ats_analyzer/scorer.py`, `skills.py`, `sections.py` |
| 5 | **Build a tailored resume** from the job description and download it as Word, PDF or text | `src/ats_analyzer/resume_builder.py` |

## Project structure
```
ats-resume-analyzer/
├── app.py                      # Web interface (Streamlit)
├── src/ats_analyzer/
│   ├── parser.py               # Step 2: read text from any document format
│   ├── jd_fetcher.py           # Step 3: get job description from a link
│   ├── skills.py               # ~150 skills with aliases (k8s = Kubernetes ...)
│   ├── sections.py             # find resume sections, dates, degrees
│   ├── keywords.py             # general keyword extraction
│   ├── scorer.py               # Step 4: compare resume vs job, score
│   └── resume_builder.py       # Step 5: tailor + export resume
├── tests/                      # automated tests (pytest)
├── samples/                    # sample resume and job description
├── static/                     # banner image + font (served as cacheable files)
├── .streamlit/config.toml      # theme and static file serving
└── requirements.txt            # Python libraries needed
```

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py            # opens the app in your browser
pytest                          # runs the tests
```

## How the score works
| Part | Weight | What it checks |
|---|---|---|
| Skills | 50% | Job's skills found in resume (nice-to-have skills count half) |
| Keywords | 15% | Other important words from the job description |
| Sections | 12% | Summary, Experience, Education, Skills headings |
| Experience | 10% | Years from your job dates vs years the job asks for |
| Contact & Length | 8% | Email, phone, 250-1000 words |
| Education | 5% | Your degree level vs the required one |

If the job doesn't mention a part (for example, no years of experience), that
part is skipped and the others are scaled up.

## Notes
- **Job links:** some sites (e.g. LinkedIn) block automatic access or need a login.
  If a link fails, copy the description and paste it as text.
- **Scanned PDFs** (images of text) can't be read; use a text-based PDF.
- **Old .doc files** are read directly; if LibreOffice is installed it is used for best results.
- **Resume builder never invents skills.** It only uses skills you confirm and
  experience you enter. It improves ordering, wording and keyword coverage.
