# ATS Resume Analyzer

Checks how well a resume matches a job description, the way an
Applicant Tracking System (ATS) would, and suggests improvements.

## Features
- Upload a resume as PDF, DOCX or TXT
- Keyword match against the job description
- Section check (Summary, Experience, Education, Skills, Projects)
- Contact info and length checks
- Score out of 100 with suggestions

## Project structure
```
ats-resume-analyzer/
├── app.py                  # Web interface (Streamlit)
├── src/ats_analyzer/
│   ├── parser.py           # Reads text from PDF/DOCX/TXT
│   ├── keywords.py         # Extracts keywords from text
│   └── scorer.py           # Computes score + suggestions
├── tests/test_scorer.py    # Automated tests
├── samples/                # Sample resume and job description
├── requirements.txt        # Python libraries needed
└── .gitignore              # Files Git should ignore
```

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py          # opens the app in your browser
pytest                        # runs the tests
```

## How the score works
| Part | Weight |
|---|---|
| Job keywords found in resume | 70% |
| Standard sections present | 20% |
| Email, phone, length 300-1000 words | 10% |
