"""
scorer.py
Computes a relevance score for each resume against a job description using:
  1. Semantic similarity  (TF-IDF + cosine similarity)   -> weight 0.60
  2. Skill overlap        (extracted skills vs JD skills) -> weight 0.25
  3. Experience fit       (years vs JD requirement)       -> weight 0.15

See README.md "Scoring Method" for the reasoning behind these weights
and why TF-IDF was chosen over a transformer embedding model.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from parser import extract_skills, extract_years_experience

WEIGHTS = {
    "semantic": 0.60,
    "skills": 0.25,
    "experience": 0.15,
}

EXPLICIT_JD_YEARS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE
)


def semantic_similarity(jd_text: str, resume_text: str) -> float:
    """TF-IDF cosine similarity between JD and resume, scaled to [0, 1]."""
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([jd_text, resume_text])
    sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    return float(sim)


def skill_score(jd_skills: set, resume_skills: set) -> float:
    """Fraction of JD-required skills present in the resume."""
    if not jd_skills:
        return 1.0  # JD didn't specify skills explicitly -> don't penalize
    matched = jd_skills & resume_skills
    return len(matched) / len(jd_skills)


def experience_score(jd_years_required: float, resume_years: float) -> float:
    """
    1.0 if resume meets or exceeds the requirement.
    Linearly scaled down if below requirement.
    Neutral 1.0 if JD specifies no explicit requirement.
    """
    if not jd_years_required:
        return 1.0
    if resume_years >= jd_years_required:
        return 1.0
    return round(resume_years / jd_years_required, 2)


def extract_jd_years(jd_text: str):
    match = EXPLICIT_JD_YEARS_RE.search(jd_text)
    return float(match.group(1)) if match else None


def score_resume(jd_text: str, jd_skills: set, jd_years: float, resume: dict) -> dict:
    sem = semantic_similarity(jd_text, resume["raw_text"])
    sk = skill_score(jd_skills, resume["skills"])
    exp = experience_score(jd_years, resume["years_experience"])

    final = (
        WEIGHTS["semantic"] * sem
        + WEIGHTS["skills"] * sk
        + WEIGHTS["experience"] * exp
    )

    matched_skills = sorted(jd_skills & resume["skills"])
    missing_skills = sorted(jd_skills - resume["skills"])

    reasoning = (
        f"Semantic similarity: {sem:.2f} | "
        f"Skills matched: {len(matched_skills)}/{len(jd_skills)} "
        f"({', '.join(matched_skills) if matched_skills else 'none'}) | "
        f"Experience: {resume['years_experience']} yrs "
        f"(required: {jd_years if jd_years else 'not specified'})"
    )

    return {
        "filename": resume["filename"],
        "final_score": round(final, 4),
        "semantic_similarity": round(sem, 4),
        "skill_score": round(sk, 4),
        "experience_score": round(exp, 4),
        "years_experience": resume["years_experience"],
        "education": resume["education"],
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reasoning": reasoning,
    }


def rank_resumes(jd_text: str, resumes: list) -> list:
    jd_skills = extract_skills(jd_text)
    jd_years = extract_jd_years(jd_text)

    scored = [score_resume(jd_text, jd_skills, jd_years, r) for r in resumes]
    scored.sort(key=lambda x: x["final_score"], reverse=True)

    for i, entry in enumerate(scored, start=1):
        entry["rank"] = i

    return scored
