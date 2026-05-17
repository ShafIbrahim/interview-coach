import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from whisper_handler import load_model, transcribe as whisper_transcribe

INTERVIEWS_DIR = Path(__file__).parent / "interviews"

@asynccontextmanager
async def lifespan(app: FastAPI):
    INTERVIEWS_DIR.mkdir(exist_ok=True)
    load_model(os.getenv("WHISPER_MODEL", "base"))
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    text = whisper_transcribe(audio_bytes)
    return {"transcript": text}
