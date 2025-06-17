from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from jinja2 import Template
from xhtml2pdf import pisa
import tempfile
import os
import json
import uuid

app = FastAPI()

html_template = """
<!DOCTYPE html>
<html>
<head>
<style>
body { font-family: Arial; font-size: 14px; margin: 20px; color: #000; }
h1 { font-size: 28px; margin-bottom: 8px; color: #2c3e50; }
h2 { font-size: 20px; margin-top: 22px; border-bottom: 1px solid #ccc; padding-bottom: 4px; color: #2c3e50; }
p, li { margin: 4px 0; }
.section { margin-bottom: 14px; }
ul { padding-left: 20px; margin: 0; }
</style>
</head>
<body>
<h1>{{ name }}</h1>
<p><strong>Email:</strong> {{ email }} | <strong>Phone:</strong> {{ phone }}</p>
<p><strong>LinkedIn:</strong> {{ linkedin }} | <strong>GitHub:</strong> {{ github }}</p>

<div class="section"><h2>Career Objective</h2><p>{{ objective }}</p></div>

<div class="section"><h2>Education</h2><ul>
{% for edu in education %}
<li><strong>{{ edu.degree }}</strong>, {{ edu.college }} ({{ edu.year }}) — CGPA: {{ edu.cgpa }}</li>
{% endfor %}
</ul></div>

<div class="section"><h2>Projects</h2><ul>
{% for proj in projects %}
<li><strong>{{ proj.title }}</strong> | <em>{{ proj.tech }}</em><br>{{ proj.desc }}</li>
{% endfor %}
</ul></div>

<div class="section"><h2>Technical Skills</h2><p>{{ skills }}</p></div>
<div class="section"><h2>Internships</h2><p>{{ internships.replace('\\n', '<br>') }}</p></div>
<div class="section"><h2>Certifications</h2><p>{{ certifications.replace('\\n', '<br>') }}</p></div>
<div class="section"><h2>Achievements</h2><p>{{ achievements.replace('\\n', '<br>') }}</p></div>
<div class="section"><h2>Workshops / Seminars</h2><p>{{ workshops.replace('\\n', '<br>') }}</p></div>
<div class="section"><h2>Extra-curricular / Leadership</h2><p>{{ extras.replace('\\n', '<br>') }}</p></div>
<div class="section"><h2>Languages Known</h2><p>{{ languages_known }}</p></div>
</body></html>
"""

@app.post("/generate-resume/")
async def generate_resume(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    linkedin: str = Form(...),
    github: str = Form(...),
    objective: str = Form(...),
    education: str = Form(...),
    projects: str = Form(...),
    skills: str = Form(...),
    achievements: str = Form(...),
    certifications: str = Form(...),
    internships: str = Form(...),
    workshops: str = Form(...),
    extras: str = Form(...),
    languages_known: str = Form(...)
):
    try:
        edu_data = json.loads(education)
        proj_data = json.loads(projects)
        html = Template(html_template).render(
            name=name, email=email, phone=phone, linkedin=linkedin, github=github,
            objective=objective, education=edu_data, projects=proj_data, skills=skills,
            achievements=achievements, certifications=certifications,
            internships=internships, workshops=workshops, extras=extras,
            languages_known=languages_known
        )
        os.makedirs("resumes", exist_ok=True)
        resume_id = str(uuid.uuid4())
        pdf_path = os.path.join("resumes", f"{resume_id}.pdf")
        with open(pdf_path, "w+b") as f:
            result = pisa.CreatePDF(html, dest=f)
        if result.err:
            return JSONResponse({"error": "Failed to generate PDF"}, status_code=500)
        return JSONResponse({"download_url": f"/download-resume/{resume_id}"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download-resume/{resume_id}")
async def download_resume(resume_id: str):
    path = os.path.join("resumes", f"{resume_id}.pdf")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/pdf", filename="Resume.pdf")
    return JSONResponse({"error": "File not found"}, status_code=404)
