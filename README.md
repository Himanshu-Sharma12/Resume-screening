# Resume Screening Agent

An AI agent that ranks a folder of resumes against a job description and outputs
a scored, ordered shortlist with human-readable reasoning for each score.

Built for the 24-hour AI Agent Challenge — **Category 1: HR & Recruitment**.

---

## What it does

```
Job Description + Folder of Resumes (PDF/DOCX/TXT)
                    │
                    ▼
        Parse resumes → extract skills,
        years of experience, education
                    │
                    ▼
   Score each resume against the JD using:
   - Semantic similarity (TF-IDF + cosine)
   - Skill overlap
   - Experience fit
                    │
                    ▼
     Ranked shortlist (console + CSV + JSON)
     with a plain-English reason per candidate
```

No LLM API key is required — the scoring pipeline is fully self-contained
(see "Why TF-IDF instead of an LLM/embedding API" below).

---

## Setup

**Requirements:** Python 3.9+

```bash
git clone <your-repo-url>
cd resume-screening-agent
pip install -r requirements.txt
```

No API keys needed for the default pipeline.

---

## Usage

Run against the included sample data:

```bash
python screen_resumes.py --jd sample_data/jd.txt --resumes sample_data/resumes --output sample_output/results
```

This will:
1. Print a ranked shortlist to the console
2. Write `sample_output/results.csv`
3. Write `sample_output/results.json`

**Run it on your own data:**

```bash
python screen_resumes.py --jd path/to/jd.txt --resumes path/to/resumes_folder --output path/to/output
```

Supported resume formats: `.pdf`, `.docx`, `.txt`, `.md`. The `resumes` folder can
contain any mix of these — the agent auto-detects the format per file.

---

## Sample Output

Console output for the included demo (10 resumes vs. a Junior Data Scientist JD):

```
#1  resume_01_priya.pdf   Score: 0.578
    Semantic similarity: 0.54 | Skills matched: 15/24 (...) | Experience: 2.0 yrs (required: 3.0)

#2  resume_02_arjun.docx   Score: 0.501
    Semantic similarity: 0.34 | Skills matched: 14/24 (...) | Experience: 3.0 yrs (required: 3.0)

...

#10 resume_08_vikram.txt   Score: 0.138
    Semantic similarity: 0.16 | Skills matched: 4/24 (...) | Experience: 0.0 yrs (required: 3.0)
```

Full ranked results with matched/missing skills per candidate: see
`sample_output/results.csv` and `sample_output/results.json`.

---

## Scoring Method

Each resume gets a **final score in [0, 1]**, a weighted combination of three signals:

| Signal | Weight | What it measures |
|---|---|---|
| Semantic similarity | 0.60 | Overall topical overlap between resume and JD (TF-IDF + cosine similarity) |
| Skill overlap | 0.25 | Fraction of JD-required skills explicitly found in the resume |
| Experience fit | 0.15 | Resume's years of experience relative to the JD's stated requirement |

**Why these weights?** Semantic similarity is weighted highest because it captures
context that keyword matching misses (e.g. a resume that discusses "predictive
modeling for retention" without using the literal word "churn" still reads as
relevant). Skill overlap is weighted second because for technical roles, hard
skill presence is a strong, low-noise signal reviewers actually check first.
Experience is weighted lowest deliberately — years alone are a weak proxy for
fit (see tradeoffs below), so it acts as a tie-breaker rather than a dominant
factor.

**Why TF-IDF instead of an LLM or a sentence-embedding model?**
Given the 24-hour constraint and a sandboxed build environment without access to
external model-hosting APIs (Hugging Face, OpenAI, etc. were not reachable),
TF-IDF + cosine similarity was chosen because it:
- Requires no API key and no internet access at runtime — fully reproducible
  for a reviewer running this cold.
- Is fast and deterministic (no rate limits, no variance run-to-run).
- Is genuinely competitive for this task: resumes and JDs are keyword-dense
  documents, and TF-IDF has long been a strong classical baseline for
  document-similarity ranking of this kind.

The architecture is intentionally modular — `scorer.py`'s `semantic_similarity()`
function is a drop-in swap point. In a production setting with API access, this
would be replaced with sentence embeddings (e.g. `text-embedding-3-small` or a
local `sentence-transformers` model) for better handling of paraphrasing and
synonyms, and an LLM call could be added as a final re-ranking / reasoning pass
on the top-N candidates.

---

## Design Tradeoffs & What I'd Improve With More Time

- **Skill taxonomy is a static list** (`SKILLS_TAXONOMY` in `parser.py`), not
  derived dynamically from the JD. It works well for tech/data roles but would
  miss skills for other domains. With more time, I'd extract candidate skill
  phrases from the JD itself (via noun-phrase extraction or an LLM call) instead
  of relying on a hardcoded taxonomy.
- **Experience-years scoring can be gamed by irrelevant seniority.** In the demo
  run, an HR Manager with 7 years of experience and zero relevant skills still
  outranked a Mechanical Engineering fresher with some Python exposure — because
  she got full credit on the experience dimension despite having 0/24 matched
  skills. This is a genuine limitation of scoring "years" as a standalone signal
  disconnected from *relevant* years. A better version would gate the experience
  score behind a minimum skill-overlap threshold, or extract years *specifically
  from roles that mention matched skills*, rather than total career years.
  I left this uncorrected on purpose so the tradeoff would surface in the demo
  rather than being hidden.
- **Date-range experience extraction is approximate.** It computes whole-year
  differences from year mentions in text; it doesn't handle every date format
  (e.g. "Since 2021" without an end year is currently skipped) and doesn't
  discount overlapping/concurrent roles. Explicit "X years of experience"
  statements are used preferentially when present, which mitigates this in most
  real resumes.
- **JD years-required parsing takes the first number in a range** (e.g. "1-3
  years" → interprets as 3). A more robust version would parse full ranges and
  score against the *minimum* acceptable value, not just whichever number the
  regex captures first.
- **No handling of resume formatting edge cases** like multi-column PDF layouts,
  scanned/image-based PDFs (would need OCR), or tables — `pypdf` extracts text
  in reading order, which can garble heavily designed resume templates.
- **Single-language support.** All matching assumes English-language resumes
  and JDs.
- **What I'd add first with another day:** an LLM-based re-ranking pass on the
  top 5-10 candidates from the TF-IDF stage, prompted to write a 1-2 sentence
  hiring-manager-style justification per candidate — combining the speed/
  reproducibility of the classical method with the nuance of an LLM, without
  paying LLM costs/latency on every resume in a large batch.

---

## Project Structure

```
resume-screening-agent/
├── screen_resumes.py       # CLI entrypoint
├── parser.py                # Resume text extraction + skill/experience/education parsing
├── scorer.py                 # TF-IDF similarity + weighted scoring + ranking
├── requirements.txt
├── README.md
├── sample_data/
│   ├── jd.txt                       # Sample Job Description (Junior Data Scientist)
│   └── resumes/                     # 10 sample resumes (mix of .pdf, .docx, .txt)
└── sample_output/
    ├── results.csv
    └── results.json
```

---

## Testing

The included 10 sample resumes were deliberately chosen to stress-test the
ranking logic — they span: strong-fit junior candidates, an overqualified
senior data scientist, an adjacent software engineer, and clearly irrelevant
profiles (HR, marketing, mechanical engineering) — to confirm the agent
produces a sensible, defensible ordering rather than just running without
errors. Re-run the command in "Usage" above to reproduce these results exactly
(TF-IDF is deterministic, so output will be identical on every run).
