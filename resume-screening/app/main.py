"""
FastAPI backend for the Agentic Resume Screening App.

Endpoints:
  POST /screening/  — accepts a resume PDF + job description text,
                      runs 3 AI agents, returns evaluation as JSON.
"""

from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from app.parsepdf import parse_pdf
from app.agents.resume_extractor_agent import analyze_resume
from app.agents.jd_extractor_agent import analyze_jd
from app.agents.candidate_evaluation_agent import evaluate_candidate
import json

app = FastAPI()


@app.post("/screening/")
async def upload_resume(resume: UploadFile, jd_text: str = Form(...)):
    """
    Endpoint to screen a resume against a job description.

    Parameters:
        resume   — uploaded PDF file
        jd_text  — job description pasted as plain text from the UI
    """
    print("Received resume file:", resume.filename)
    print("Job description length:", len(jd_text), "characters")

    # Step 1: Extract text from uploaded resume PDF
    resume_text = parse_pdf(resume.file)

    # Step 2: Use AI agent to extract structured candidate details
    candidate_details = analyze_resume(resume_text)

    # Step 3: Use AI agent to extract structured JD requirements
    # (jd_text comes directly from the Streamlit UI text area now —
    #  no more hardcoded PDF file needed)
    jd_details = analyze_jd(jd_text)

    # Step 4: Evaluate candidate against JD
    evaluation = evaluate_candidate(candidate_details, jd_details)
    print("Evaluation result:", evaluation)

    # Step 5: Safely parse and return JSON
    if isinstance(evaluation, str):
        try:
            result_json = json.loads(evaluation)
        except json.JSONDecodeError:
            result_json = {"error": "Invalid JSON format in evaluation output"}
    else:
        result_json = evaluation

    return JSONResponse(content=result_json)
