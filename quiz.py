import streamlit as st
import requests
from PyPDF2 import PdfReader
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyCnj11mh1dUriQecj2tEehLSIE8vJZ3xeQ"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw8zsQ0XRBve9DNkmvQIUKA3P7xbitMCG8MnpQgEQn5Kt37laPKWLtHQGVNg6wLB7E1hA/exec"

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def generate_quiz_questions(text, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        f"Generate 10 unique multiple-choice questions (4 options each) from this text. "
        f"STRICTLY output ONLY a valid JSON array. Example: "
        f"[{{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": \"A\"}}, ...] "
        f"Do not add explanations, comments, or extra text.\n\n"
        f"Content:\n{text[:2000]}"
    )
    return response.text

def extract_json(text):
    match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    else:
        raise ValueError("No valid JSON array found in Gemini output.")

st.title("📄 Auto PDF → Unique Google Form Quiz Generator")

uploaded_pdf = st.file_uploader("Upload your PDF", type="pdf")

if uploaded_pdf and st.button("Generate My Unique Quiz"):
    st.info("Extracting text from PDF...")
    text = extract_text_from_pdf(uploaded_pdf)

    st.info("Generating quiz and creating Google Form...")
    try:
        quiz_raw = generate_quiz_questions(text, GEMINI_API_KEY)
        cleaned_json = extract_json(quiz_raw)
        quiz_data = json.loads(cleaned_json)

        payload = {
            "title": "Auto-Generated Quiz",
            "questions": quiz_data
        }

        response = requests.post(WEB_APP_URL, json=payload)
        if response.status_code == 200:
            form_url = response.text.strip()
            st.success(f"✅ Your Google Form is ready! [Click here to open it]({form_url})")
            st.info("Take the quiz, your score will be shown immediately after submission!")
        else:
            st.error(f"❌ Form creation failed: {response.status_code} {response.text}")

    except Exception as e:
        st.error(f"❌ Error: {e}")
