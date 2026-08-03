import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="Resume Screening App", page_icon="📄", layout="wide")
st.title("📄 Resume Screening App")

# ── Layout: two columns ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Upload a Resume (PDF)", type="pdf")
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")

with col2:
    jd_text = st.text_area(
        "Paste Job Description here",
        height=200,
        placeholder="e.g. We are looking for a Python developer with 3+ years experience in FastAPI, PostgreSQL..."
    )

# ── Process button ────────────────────────────────────────────────────────────
if st.button("🔍 Process Resume", type="primary"):
    if not uploaded_file:
        st.error("Please upload a resume PDF.")
    elif not jd_text.strip():
        st.error("Please paste a job description.")
    else:
        with st.spinner("Analysing resume with AI... this may take 30-60 seconds."):
            try:
                response = requests.post(
                    "http://localhost:8000/screening/",
                    files={"resume": uploaded_file},
                    data={"jd_text": jd_text},
                    timeout=120,
                )

                if response.status_code == 200:
                    data = response.json()

                    # ── Results display ───────────────────────────────────────
                    st.success("Resume processed successfully!")
                    st.divider()

                    r1, r2, r3 = st.columns(3)

                    status = data.get("candidate_status", "N/A")
                    with r1:
                        color = "🟢" if status == "Selected" else "🔴"
                        st.metric("Candidate Status", f"{color} {status}")

                    with r2:
                        skills = data.get("skills_matched", data.get("skill_match_percentage", "N/A"))
                        st.metric("Skills Matched", f"{skills}%")

                    with r3:
                        st.metric("Resume", uploaded_file.name)

                    st.markdown("**Feedback:**")
                    feedback = data.get("feedback", data.get("reason", "No feedback provided."))
                    st.info(feedback)

                    # ── Save result to session state for CSV export ───────────
                    if "results" not in st.session_state:
                        st.session_state.results = []

                    st.session_state.results.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Resume": uploaded_file.name,
                        "Candidate Status": status,
                        "Skills Matched (%)": skills,
                        "Feedback": feedback,
                        "Job Description (snippet)": jd_text[:100] + "...",
                    })

                else:
                    st.error(f"Error processing resume: {response.text}")

            except requests.exceptions.Timeout:
                st.error("Request timed out. The model is taking too long — try again.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure FastAPI is running on port 8000.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

# ── Results history + CSV export ─────────────────────────────────────────────
if "results" in st.session_state and st.session_state.results:
    st.divider()
    st.subheader("📊 Screening History")

    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Results as CSV",
        data=csv,
        file_name=f"resume_screening_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    if st.button("🗑️ Clear History"):
        st.session_state.results = []
        st.rerun()
