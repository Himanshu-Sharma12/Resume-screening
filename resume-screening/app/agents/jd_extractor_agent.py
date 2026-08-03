import os
import json
import ollama
from app.prompts import EXTRACT_JD_DETAILS

OLLAMA_MODEL = "llama3.2"


def analyze_jd(text: str) -> str:
    """
    Function to analyze the extracted text from a job description using local Ollama.
    Returns structured JSON string of JD details.
    """
    prompt = EXTRACT_JD_DETAILS.format(jd_text=text)

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )

        result = response["message"]["content"].strip()
        print("Response from JD Extractor Agent:", result)
        return result

    except Exception as e:
        return json.dumps({"error": str(e)})