"""
screen_resumes.py
CLI entrypoint for the Resume Screening Agent.

Usage:
    python screen_resumes.py --jd sample_data/jd.txt \
                              --resumes sample_data/resumes \
                              --output sample_output/results

This will:
  1. Load the Job Description.
  2. Parse every resume in the given folder (PDF / DOCX / TXT).
  3. Score each resume against the JD (semantic similarity + skills + experience).
  4. Print a ranked shortlist to the console.
  5. Write results to <output>.csv and <output>.json
"""

import argparse
import csv
import json
import os
import sys

from parser import parse_resume
from scorer import rank_resumes


def load_jd(jd_path: str) -> str:
    with open(jd_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def collect_resume_paths(resumes_dir: str) -> list:
    paths = []
    for root, _, filenames in os.walk(resumes_dir):
        for fname in sorted(filenames):
            if fname.startswith("."):
                continue
            paths.append(os.path.join(root, fname))
    return paths


def write_csv(results: list, path: str):
    fieldnames = [
        "rank", "filename", "final_score", "semantic_similarity",
        "skill_score", "experience_score", "years_experience",
        "education", "matched_skills", "missing_skills", "reasoning",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            row = row.copy()
            row["matched_skills"] = "; ".join(row["matched_skills"])
            row["missing_skills"] = "; ".join(row["missing_skills"])
            writer.writerow(row)


def write_json(results: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def print_shortlist(results: list):
    print("\n" + "=" * 70)
    print("RESUME SCREENING — RANKED SHORTLIST")
    print("=" * 70)
    for r in results:
        print(f"\n#{r['rank']}  {r['filename']}   Score: {r['final_score']:.3f}")
        print(f"    {r['reasoning']}")
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="AI Resume Screening Agent")
    parser.add_argument("--jd", required=True, help="Path to job description text file")
    parser.add_argument("--resumes", required=True, help="Path to folder of resumes")
    parser.add_argument("--output", default="results", help="Output file prefix (no extension)")
    args = parser.parse_args()

    if not os.path.isfile(args.jd):
        sys.exit(f"Job description file not found: {args.jd}")
    if not os.path.isdir(args.resumes):
        sys.exit(f"Resumes folder not found: {args.resumes}")

    jd_text = load_jd(args.jd)
    resume_paths = collect_resume_paths(args.resumes)

    if not resume_paths:
        sys.exit(f"No resume files found in {args.resumes}")

    print(f"Loaded JD from {args.jd}")
    print(f"Found {len(resume_paths)} resumes in {args.resumes}")

    resumes = []
    for path in resume_paths:
        try:
            resumes.append(parse_resume(path))
        except Exception as e:
            print(f"  [WARN] Failed to parse {path}: {e}", file=sys.stderr)

    if not resumes:
        sys.exit(f"Could not parse any resume files in {args.resumes}")

    results = rank_resumes(jd_text, resumes)

    print_shortlist(results)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    csv_path = f"{args.output}.csv"
    json_path = f"{args.output}.json"
    write_csv(results, csv_path)
    write_json(results, json_path)

    print(f"\nSaved ranked results to:\n  {csv_path}\n  {json_path}")


if __name__ == "__main__":
    main()
