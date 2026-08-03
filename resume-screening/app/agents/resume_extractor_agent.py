import os
import json
import re
import ollama
from app.prompts import EXTRACT_CANDIDATE_DETAILS
import logging

logging.basicConfig(level=logging.INFO)

OLLAMA_MODEL = "llama3.2"


def analyze_resume(text: str) -> str:
    """
    Function to analyze the extracted text from a resume using local Ollama.
    Returns structured JSON string of candidate details.
    """
    prompt = EXTRACT_CANDIDATE_DETAILS.format(resume_text=text)

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )

        result = response["message"]["content"].strip()
        print("Response from Resume Extractor Agent:", result)
        logging.info("Resume analysis completed")
        return result

    except Exception as e:
        logging.error(f"Resume extraction failed: {e}")
        return json.dumps({"error": str(e)})
