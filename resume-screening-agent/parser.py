"""
parser.py
Extracts raw text from resumes (PDF / DOCX / TXT) and pulls out
structured signals: skills, years of experience, education.
"""

import os
import re
from datetime import datetime

from pypdf import PdfReader
import docx


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(filepath: str) -> str:
    """Dispatch to the right extractor based on file extension."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return _extract_pdf(filepath)
    elif ext == ".docx":
        return _extract_docx(filepath)
    elif ext in (".txt", ".md"):
        return _extract_txt(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext} ({filepath})")


def _extract_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def _extract_docx(filepath: str) -> str:
    document = docx.Document(filepath)
    return "\n".join(p.text for p in document.paragraphs)


def _extract_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Skill extraction
# ---------------------------------------------------------------------------

# A general tech/business skills taxonomy. In production this would be
# swapped for a maintained skills database (e.g. ESCO, LinkUp, or a
# JD-derived dynamic list) — see README tradeoffs.
SKILLS_TAXONOMY = [
    "python", "java", "c++", "c#", "javascript", "typescript", "sql", "r",
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch",
    "keras", "matplotlib", "seaborn", "power bi", "tableau", "excel",
    "machine learning", "deep learning", "nlp", "computer vision",
    "data analysis", "data visualization", "eda", "statistics",
    "data cleaning", "feature engineering", "etl", "airflow", "spark",
    "hadoop", "aws", "azure", "gcp", "docker", "kubernetes", "git",
    "html", "css", "react", "node.js", "django", "flask", "streamlit",
    "mysql", "postgresql", "mongodb", "rest api", "api integration",
    "a/b testing", "regression", "classification", "clustering",
    "random forest", "xgboost", "gradient boosting", "time series",
]


def extract_skills(text: str) -> set:
    """Case-insensitive whole-phrase matching against the taxonomy."""
    text_lower = text.lower()
    found = set()
    for skill in SKILLS_TAXONOMY:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.add(skill)
    return found


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------

MONTH_RE = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})"
YEAR_ONLY_RE = r"\b(19|20)\d{2}\b"

EXPLICIT_YEARS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE
)

DATE_RANGE_RE = re.compile(
    rf"({MONTH_RE}|\b(19|20)\d{{2}}\b)\s*(?:-|–|to)\s*"
    rf"({MONTH_RE}|\b(19|20)\d{{2}}\b|present|current)",
    re.IGNORECASE,
)


def _parse_year(fragment: str) -> int:
    match = re.search(r"(19|20)\d{2}", fragment)
    return int(match.group(0)) if match else None


def extract_years_experience(text: str) -> float:
    """
    Two strategies, in order of preference:
    1. An explicit "X years of experience" statement.
    2. Summed duration of date ranges found in a Work Experience section.
    Falls back to 0 if neither is found (e.g. a fresher resume).
    """
    explicit = EXPLICIT_YEARS_RE.findall(text)
    if explicit:
        return max(float(x) for x in explicit)

    total_months = 0
    now_year = datetime.now().year
    for match in DATE_RANGE_RE.finditer(text):
        start_year = _parse_year(match.group(1))
        end_raw = match.group(3)
        end_year = now_year if re.search(r"present|current", end_raw, re.I) else _parse_year(end_raw)
        if start_year and end_year and end_year >= start_year:
            total_months += (end_year - start_year) * 12

    return round(total_months / 12, 1)


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------

DEGREE_PATTERNS = [
    r"ph\.?d", r"m\.?tech", r"b\.?tech", r"m\.?sc", r"b\.?sc", r"mba",
    r"bachelor(?:'s)?(?:\s+of\s+\w+)?", r"master(?:'s)?(?:\s+of\s+\w+)?",
    r"b\.?e\.?\b", r"m\.?e\.?\b",
]
DEGREE_RE = re.compile("|".join(DEGREE_PATTERNS), re.IGNORECASE)


def extract_education(text: str) -> str:
    match = DEGREE_RE.search(text)
    if not match:
        return "Not specified"
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


# ---------------------------------------------------------------------------
# Convenience: parse one resume fully
# ---------------------------------------------------------------------------

def parse_resume(filepath: str) -> dict:
    text = extract_text(filepath)
    return {
        "filename": os.path.basename(filepath),
        "raw_text": text,
        "skills": extract_skills(text),
        "years_experience": extract_years_experience(text),
        "education": extract_education(text),
    }
