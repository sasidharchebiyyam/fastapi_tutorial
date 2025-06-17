from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
from pydantic import BaseModel
from langdetect import detect, DetectorFactory
from googletrans import Translator
from gtts import gTTS
import pyttsx3
import tempfile
import os
import PyPDF2
import re
import random
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

DetectorFactory.seed = 0  # Make language detection deterministic

app = FastAPI()
translator = Translator()

language_map = {
    "English": "en", "Hindi": "hi", "Spanish": "es", "French": "fr", "German": "de",
    "Italian": "it", "Chinese": "zh-cn", "Japanese": "ja", "Russian": "ru", "Arabic": "ar",
    "Bengali": "bn", "Tamil": "ta", "Telugu": "te", "Kannada": "kn", "Malayalam": "ml"
}

def extract_text_from_pdf(file) -> str:
    try:
        reader = PyPDF2.PdfReader(file)
        return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def summarize_text(text: str, num_sentences=3) -> str:
    if not text or len(text.strip()) < 50:
        return text.strip()
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        stemmer = Stemmer("english")
        summarizer = LexRankSummarizer(stemmer)
        summarizer.stop_words = get_stop_words("english")
        summary = summarizer(parser.document, num_sentences)
        return " ".join(str(sentence) for sentence in summary)
    except Exception as e:
        print(f"Error summarizing text: {e}")
        sentences = re.split(r'(?<=[.!?]) +', text)
        return " ".join(sentences[:num_sentences]) if sentences else text.strip()

def find_answer(text: str, question: str) -> str:
    if not text or not question:
        return "Sorry, I couldn't find an answer due to missing text or question."
    sentences = re.split(r'(?<=[.!?]) +', text)
    keywords = [w.lower() for w in question.split() if len(w) > 2]
    if not sentences or not keywords:
        return "Sorry, I couldn't find an answer."
    best = max(sentences, key=lambda s: sum(k in s.lower() for k in keywords), default="Sorry, I couldn't find an answer.")
    return best

def speak_text(text: str, lang: str, mode: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    try:
        if mode == "Online":
            tts = gTTS(text, lang=lang)
            tts.save(temp_file.name)
        else:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.save_to_file(text, temp_file.name)
            engine.runAndWait()
        return temp_file.name
    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
        raise

def generate_quiz_questions(text: str, num_questions=3) -> List[dict]:
    if not text or len(text.strip()) < 50:
        return []
    sentences = re.split(r'(?<=[.!?]) +', text)
    questions = []
    for sentence in sentences:
        words = [word for word in re.findall(r'\b\w+\b', sentence) if len(word) > 3]
        if words:
            chosen_word = random.choice(words)
            question_text = sentence.replace(chosen_word, "", 1)
            questions.append({"question": question_text, "answer": chosen_word})
        if len(questions) >= num_questions:
            break
    return questions

class TextInput(BaseModel):
    text: str
    question: Optional[str] = None
    language: str = "English"
    tts_mode: str = "Online"

@app.post("/process/")
async def process_text(input: TextInput):
    if not input.text or not input.text.strip():
        return JSONResponse(content={"error": "Input text cannot be empty."}, status_code=400)

    selected_lang_code = language_map.get(input.language, "en")
    
    try:
        detected_lang = detect(input.text)
    except Exception as e:
        print(f"Language detection failed: {e}. Defaulting to English.")
        detected_lang = "en"

    translated_text = input.text
    if detected_lang != "en":
        try:
            translated_text = translator.translate(input.text, dest="en").text
        except Exception as e:
            print(f"Translation to English failed: {e}. Proceeding with original text.")

    result = {"summary": "", "answer": "", "quiz": []}

    summary_en = summarize_text(translated_text)
    try:
        result["summary"] = translator.translate(summary_en, dest=selected_lang_code).text if selected_lang_code != "en" else summary_en
    except Exception as e:
        print(f"Translation of summary failed: {e}.")
        result["summary"] = summary_en

    if input.question:
        answer_en = find_answer(translated_text, input.question)
        try:
            result["answer"] = translator.translate(answer_en, dest=selected_lang_code).text if selected_lang_code != "en" else answer_en
        except Exception as e:
            print(f"Translation of answer failed: {e}.")
            result["answer"] = answer_en

    quiz = generate_quiz_questions(translated_text)
    translated_quiz = []
    for q in quiz:
        try:
            translated_question = translator.translate(q["question"], dest=selected_lang_code).text if selected_lang_code != "en" else q["question"]
            translated_answer = translator.translate(q["answer"], dest=selected_lang_code).text if selected_lang_code != "en" else q["answer"]
            translated_quiz.append({"question": translated_question, "answer": translated_answer})
        except Exception as e:
            print(f"Translation of quiz question/answer failed: {e}.")
            translated_quiz.append({"question": q["question"], "answer": q["answer"]})
    result["quiz"] = translated_quiz

    return JSONResponse(content=result)

@app.post("/speak/")
async def text_to_speech(text: str = Form(...), lang: str = Form(...), mode: str = Form(...)):
    if not text or not text.strip():
        return JSONResponse(content={"error": "Text for speech cannot be empty."}, status_code=400)
    
    selected_lang_code = language_map.get(lang, "en")
    file_path = None
    try:
        file_path = speak_text(text, selected_lang_code, mode)
        return FileResponse(file_path, media_type="audio/mpeg", filename="speech.mp3")
    except Exception as e:
        print(f"Error during text-to-speech endpoint: {e}")
        return JSONResponse(content={"error": f"Failed to generate speech: {e}"}, status_code=500)
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    content = ""
    try:
        if file.content_type == "application/pdf":
            content = extract_text_from_pdf(file.file)
        elif file.content_type == "text/plain":
            content = (await file.read()).decode("utf-8")
        else:
            return JSONResponse(content={"error": "Unsupported file type. Only PDF and plain text are supported."}, status_code=400)
    except Exception as e:
        print(f"Error processing uploaded file: {e}")
        return JSONResponse(content={"error": f"Failed to process file: {e}"}, status_code=500)

    if not content.strip():
        return JSONResponse(content={"error": "Could not extract any readable text from the file."}, status_code=400)

    return {"text": content}
