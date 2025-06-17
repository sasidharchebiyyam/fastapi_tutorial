from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import face_recognition
from PIL import Image
import io
from zipfile import ZipFile

app = FastAPI()

@app.post("/extract-faces/")
async def extract_faces(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported.")
    
    image_data = await file.read()
    image = face_recognition.load_image_file(io.BytesIO(image_data))
    face_locations = face_recognition.face_locations(image)

    if not face_locations:
        raise HTTPException(status_code=404, detail="No faces found in the image.")

    pil_image = Image.fromarray(image)
    zip_buffer = io.BytesIO()

    with ZipFile(zip_buffer, "a") as zip_file:
        for i, (top, right, bottom, left) in enumerate(face_locations):
            face_image = pil_image.crop((left, top, right, bottom))
            face_bytes = io.BytesIO()
            face_image.save(face_bytes, format="JPEG")
            zip_file.writestr(f"face_{i+1}.jpg", face_bytes.getvalue())

    zip_buffer.seek(0)
    return StreamingResponse(zip_buffer, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=faces.zip"})
