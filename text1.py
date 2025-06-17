from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from langdetect import detect
from googletrans import Translator
from gtts import gTTS
import tempfile
import os
import PyPDF2
import re
import random

app = FastAPI()
translator = Translator()

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join(page.extract_text() or "" for page in reader.pages)

def summarize_text(text, num_sentences=5):
    sentences = re.split(r'(?<=[.!?]) +', text)
    top = sorted(sentences, key=len, reverse=True)
    return " ".join(top[:num_sentences])

def find_answer(text, question):
    sentences = re.split(r'(?<=[.!?]) +', text)
    keywords = [w.lower() for w in question.split() if len(w) > 2]
    return max(sentences, key=lambda s: sum(k in s.lower() for k in keywords), default="Sorry")

def generate_quiz(text, count=5):
    sentences = re.split(r'(?<=[.!?]) +', text)
    questions = []
    for sentence in sentences:
        words = [w for w in re.findall(r'\b\w+\b', sentence) if len(w) > 3]
        if words:
            word = random.choice(words)
            questions.append((sentence.replace(word, "_", 1), word))
        if len(questions) >= count:
            break
    return questions

def speak(text, lang):
    tts = gTTS(text, lang=lang)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(temp.name)
    return temp.name

@app.post("/analyze/")
async def analyze(
    question: str = Form(None),
    summarize: bool = Form(False),
    quiz: bool = Form(False),
    lang: str = Form("en"),
    text: str = Form(""),
    file: UploadFile = None
):
    if file:
        content = await file.read()
        if file.filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                text = extract_text_from_pdf(f)
        else:
            text = content.decode("utf-8")

    detected = detect(text)
    if detected != "en":
        text = translator.translate(text, dest="en").text

    result = {}

    if question:
        ans = find_answer(text, question)
        result["answer"] = translator.translate(ans, dest=lang).text if lang != "en" else ans

    if summarize:
        summ = summarize_text(text)
        result["summary"] = translator.translate(summ, dest=lang).text if lang != "en" else summ

    if quiz:
        raw_qs = generate_quiz(text)
        translated = [(translator.translate(q, dest=lang).text, translator.translate(a, dest=lang).text) if lang != "en" else (q, a) for q, a in raw_qs]
        result["quiz"] = [{"question": q, "answer": a} for q, a in translated]

    return JSONResponse(content=result)

@app.post("/speak/")
async def tts_api(text: str = Form(...), lang: str = Form("en")):
    audio_file = speak(text, lang)
    return FileResponse(audio_file, media_type="audio/mpeg", filename="speech.mp3")
