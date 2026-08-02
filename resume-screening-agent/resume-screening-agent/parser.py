"""
parser.py
Extracts raw text from resumes and pulls out structured signals:
skills, years of experience, and education.
"""

import os
import re
import zipfile
from datetime import datetime
from xml.etree import ElementTree

from pypdf import PdfReader
import docx


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

TEXT_EXTENSIONS = {".txt", ".md", ".rtf", ".csv", ".log"}


def _read_text_with_fallback(filepath: str) -> str:
    with open(filepath, "rb") as f:
        raw = f.read()

    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw.decode("utf-8", errors="ignore")


def _extract_text_from_xml(xml_text: str) -> str:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return ""

    text = " ".join(piece.strip() for piece in root.itertext())
    return re.sub(r"\s+", " ", text).strip()


def _extract_zip_text(filepath: str) -> str:
    with zipfile.ZipFile(filepath) as archive:
        for candidate in ("word/document.xml", "content.xml"):
            if candidate in archive.namelist():
                with archive.open(candidate) as xml_file:
                    xml_text = xml_file.read().decode("utf-8", errors="ignore")
                extracted = _extract_text_from_xml(xml_text)
                if extracted:
                    return extracted
    return ""


def _extract_rtf_text(filepath: str) -> str:
    text = _read_text_with_fallback(filepath)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+(?:-?\d+)? ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_text(filepath: str) -> str:
    """Dispatch to the best available extractor based on file type."""
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".pdf":
            return _extract_pdf(filepath)
        if ext == ".docx":
            return _extract_docx(filepath)
        if ext == ".odt":
            return _extract_zip_text(filepath)
        if ext == ".rtf":
            return _extract_rtf_text(filepath)
        if ext in TEXT_EXTENSIONS:
            return _extract_txt(filepath)

        if zipfile.is_zipfile(filepath):
            return _extract_zip_text(filepath)

        try:
            with open(filepath, "rb") as f:
                header = f.read(8)
            if header.startswith(b"%PDF-"):
                return _extract_pdf(filepath)
        except OSError:
            pass

        return _extract_txt(filepath)
    except Exception:
        # Best-effort fallback so a single bad resume does not break a batch run.
        try:
            if zipfile.is_zipfile(filepath):
                return _extract_zip_text(filepath)
        except OSError:
            pass

        try:
            return _extract_txt(filepath)
        except Exception:
            return ""


def _extract_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or "")
    return "\n".join(text)


def _extract_docx(filepath: str) -> str:
    try:
        document = docx.Document(filepath)
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:
        return _extract_zip_text(filepath)


def _extract_txt(filepath: str) -> str:
    return _read_text_with_fallback(filepath)


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

EXPLICIT_YEARS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE
)

DATE_RANGE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|(?:19|20)\d{2})"
    r"\s*(?:-|–|to)\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|(?:19|20)\d{2}|present|current)",
    re.IGNORECASE,
)


def _parse_year(fragment: str):
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
        start_raw = match.group(1)
        end_raw = match.group(2)
        if not start_raw or not end_raw:
            continue

        start_year = _parse_year(start_raw)
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
