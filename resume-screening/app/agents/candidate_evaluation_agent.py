import os
import json
import re
import ollama
from app.prompts import CANDIDATE_EVALUATION

# Model must be pulled locally first, e.g.: `ollama pull llama3.2`
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def _safe_json_parse(raw_text: str) -> dict:
    """
    Robustly extract a JSON object from the model's response,
    even if it's wrapped in markdown code fences or extra text.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "candidate_status": "None",
        "feedback": "Model returned unstructured text.",
        "skills_matched": 0
    }


def evaluate_candidate(candidate_details: str, jd: str) -> dict:
    """
    Function to evaluate the candidate against the job description using a
    local, free, open-source LLM via Ollama (no API key, no rate limits,
    fully offline). Ensures the model returns structured JSON for Streamlit
    display.
    """
    prompt = f"""
    {CANDIDATE_EVALUATION.format(resume_json=candidate_details, jd_json=jd)}

    Return the result strictly in JSON format, with no extra text and no
    markdown code fences:
    {{
      "candidate_status": "<Selected/Rejected>",
      "feedback": "<Short summary>",
      "skills_matched": <percentage as a number>
    }}
    """

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )

        result_text = response["message"]["content"].strip()
        print("Response from Ollama:", result_text)

        result_json = _safe_json_parse(result_text)
        return result_json

    except Exception as e:
        return {"error": str(e)}
