import os
import json
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from whisper_handler import load_model, transcribe as whisper_transcribe
from claude_handler import build_system_prompt, chat as claude_chat

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
    html = (Path(__file__).parent / "static" / "index.html").read_text()
    html = html.replace("__DEBUG__", os.getenv("DEBUG", "false").lower())
    html = html.replace("__MAX_HINTS__", os.getenv("MAX_HINTS", "3"))
    return HTMLResponse(html)

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    text = whisper_transcribe(audio_bytes)
    return {"transcript": text}

class ChatRequest(BaseModel):
    messages: list[dict]
    mode: str
    problem: str
    max_hints: int
    hints_remaining: int

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    system_prompt = build_system_prompt(
        mode=req.mode,
        problem=req.problem,
        max_hints=req.max_hints,
        hints_remaining=req.hints_remaining,
    )
    return claude_chat(req.messages, system_prompt)

class TranscriptEntry(BaseModel):
    role: str
    content: str
    ts: str

class SessionEndRequest(BaseModel):
    mode: str
    problem: str
    duration_seconds: int
    hints_used: int
    max_hints: int
    transcript: list[TranscriptEntry]

@app.post("/session/end")
async def session_end(req: SessionEndRequest):
    timestamp = datetime.now()
    filename = INTERVIEWS_DIR / f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{req.mode}.json"
    data = {
        "timestamp": timestamp.isoformat(),
        "mode": req.mode,
        "problem": req.problem,
        "duration_seconds": req.duration_seconds,
        "hints_used": req.hints_used,
        "max_hints": req.max_hints,
        "transcript": [e.model_dump() for e in req.transcript],
    }
    try:
        filename.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[session/end] Failed to save transcript: {e}")
    return {"saved": str(filename)}
