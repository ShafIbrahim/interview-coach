# Interview Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally-hosted AI interview coach with voice input (local Whisper STT), a collaborative Claude interviewer, and a Monaco code editor — runnable at `localhost:8000`.

**Architecture:** FastAPI backend serves a single-page frontend. Audio is continuously recorded in the browser via MediaRecorder; silence detection splits it into utterances that are POSTed to `/transcribe` (local Whisper). Transcripts flow to `/chat` (Claude API). Conversation history lives in browser state. Sessions are saved as JSON on end.

**Tech Stack:** Python 3.11+, FastAPI, openai-whisper, anthropic SDK, Monaco Editor (CDN), Vanilla JS

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, all 4 routes, startup (Whisper load, dir creation) |
| `whisper_handler.py` | Whisper model singleton, `transcribe(bytes) -> str` |
| `claude_handler.py` | System prompt builder, `chat(messages, prompt) -> {content, hint_used}` |
| `static/index.html` | Full frontend — layout, CSS, all JS |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
| `.gitignore` | Exclude `.env`, `interviews/`, `__pycache__` |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `static/index.html` (empty shell)
- Create: `main.py` (skeleton)

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
openai-whisper
anthropic>=0.25.0
python-multipart>=0.0.9
python-dotenv>=1.0.0
torch
```

- [ ] **Step 2: Create `.env.example`**

```
ANTHROPIC_API_KEY=your_key_here
WHISPER_MODEL=base
DEBUG=false
MAX_HINTS=3
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
interviews/
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 4: Create empty `static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Interview Coach</title>
</head>
<body>
  <p>Coming soon</p>
</body>
</html>
```

- [ ] **Step 5: Create `main.py` skeleton**

```python
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
INTERVIEWS_DIR = Path("interviews")

@app.on_event("startup")
async def startup():
    INTERVIEWS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")
```

- [ ] **Step 6: Install dependencies**

```bash
cd /Users/shafieenibrahim/Documents/Projects/interview-coach
pip install -r requirements.txt
```

Expected: All packages install without error. Whisper and torch may take a few minutes.

- [ ] **Step 7: Copy `.env.example` to `.env` and fill in your key**

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY to your real key
```

- [ ] **Step 8: Verify server starts**

```bash
uvicorn main:app --reload
```

Expected: Server running at `http://127.0.0.1:8000`. Visit it — you see "Coming soon".

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .env.example .gitignore static/index.html main.py
git commit -m "feat: project scaffolding and FastAPI skeleton"
```

---

## Task 2: Whisper Handler + `/transcribe` Route

**Files:**
- Create: `whisper_handler.py`
- Modify: `main.py` — add `/transcribe` route

- [ ] **Step 1: Create `whisper_handler.py`**

```python
import os
import tempfile
import whisper

_model = None

def load_model(model_name: str = "base") -> None:
    global _model
    _model = whisper.load_model(model_name)

def transcribe(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = _model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: Add startup model load and `/transcribe` route to `main.py`**

Replace the existing `startup` function and add the import + route:

```python
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from whisper_handler import load_model, transcribe as whisper_transcribe

app = FastAPI()
INTERVIEWS_DIR = Path("interviews")

@app.on_event("startup")
async def startup():
    INTERVIEWS_DIR.mkdir(exist_ok=True)
    load_model(os.getenv("WHISPER_MODEL", "base"))

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    text = whisper_transcribe(audio_bytes)
    return {"transcript": text}
```

- [ ] **Step 3: Verify `/transcribe` works**

Restart the server, then test with a real audio file (record 5 seconds of yourself saying "hello world"):

```bash
uvicorn main:app --reload
# In another terminal:
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@/path/to/test.webm" \
  | python3 -m json.tool
```

Expected: `{"transcript": "Hello world."}` (or similar)

- [ ] **Step 4: Commit**

```bash
git add whisper_handler.py main.py
git commit -m "feat: add Whisper STT handler and /transcribe route"
```

---

## Task 3: Claude Handler + `/chat` Route

**Files:**
- Create: `claude_handler.py`
- Modify: `main.py` — add `/chat` route

- [ ] **Step 1: Create `claude_handler.py`**

```python
import os
from anthropic import Anthropic

_client = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

SYSTEM_PROMPT_TEMPLATE = """\
You are a collaborative Staff Engineer interviewer. Your role is to guide the candidate \
through this process: clarify → design → implement → test → complexity → NFRs.

Rules:
- Do not give away solutions. Push back when steps are skipped.
- You may offer up to {max_hints} hints if the candidate explicitly asks. \
You have {remaining} remaining. Never offer hints unprompted.
- When giving a hint, begin your response with the exact token [HINT] on its own line, \
then your hint text. No other response should start with [HINT].
- When the candidate presents an approach and asks for feedback, give structured insight: \
what is strong, what is missing, what tradeoffs to consider. Do not give the full solution.
- Interview type: {mode}.
  - Algo: enforce Big-O analysis and edge case coverage.
  - System Design: emphasize capacity planning, component tradeoffs, and failure modes.

Problem: {problem_statement}"""

def build_system_prompt(
    mode: str, problem: str, max_hints: int, hints_remaining: int
) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        mode=mode,
        problem_statement=problem,
        max_hints=max_hints,
        remaining=hints_remaining,
    )

def chat(messages: list[dict], system_prompt: str) -> dict:
    response = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    content = response.content[0].text.strip()
    hint_used = content.startswith("[HINT]")
    if hint_used:
        content = content[len("[HINT]"):].lstrip("\n").strip()
    return {"content": content, "hint_used": hint_used}
```

- [ ] **Step 2: Add `/chat` route to `main.py`**

Add after the `/transcribe` route:

```python
from pydantic import BaseModel
from claude_handler import build_system_prompt, chat as claude_chat

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
```

- [ ] **Step 3: Verify `/chat` works**

With the server running:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I want to solve Two Sum"}],
    "mode": "algo",
    "problem": "Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.",
    "max_hints": 3,
    "hints_remaining": 3
  }' | python3 -m json.tool
```

Expected: JSON with `"content"` (Claude's interviewer response) and `"hint_used": false`.

- [ ] **Step 4: Commit**

```bash
git add claude_handler.py main.py
git commit -m "feat: add Claude handler and /chat route with hint detection"
```

---

## Task 4: Session Persistence + `/session/end` Route

**Files:**
- Modify: `main.py` — add `/session/end` route

- [ ] **Step 1: Add `/session/end` route to `main.py`**

Add after the `/chat` route:

```python
import json
from datetime import datetime

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
```

- [ ] **Step 2: Verify `/session/end` saves a file**

```bash
curl -X POST http://localhost:8000/session/end \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "algo",
    "problem": "Two Sum",
    "duration_seconds": 300,
    "hints_used": 1,
    "max_hints": 3,
    "transcript": [
      {"role": "assistant", "content": "What clarifying questions do you have?", "ts": "10:00:01"},
      {"role": "user", "content": "Can the array be empty?", "ts": "10:00:45"}
    ]
  }' | python3 -m json.tool
```

Expected: `{"saved": "interviews/2026-05-16_10-00-00_algo.json"}`. Verify the file exists:

```bash
ls interviews/
cat interviews/*.json
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add session persistence and /session/end route"
```

---

## Task 5: Frontend — Base Layout + CSS

**Files:**
- Modify: `static/index.html` — full dark theme layout with all panels

- [ ] **Step 1: Replace `static/index.html` with the full layout shell**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Interview Coach</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    /* TOP BAR */
    .topbar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      background: #1a1d27;
      border-bottom: 1px solid #2d3148;
      flex-shrink: 0;
    }
    .mode-toggle { display: flex; background: #0f1117; border-radius: 6px; padding: 3px; gap: 3px; }
    .mode-btn {
      padding: 5px 14px; border-radius: 4px; border: none;
      font-size: 12px; font-weight: 600; cursor: pointer;
      background: transparent; color: #94a3b8; transition: all 0.15s;
    }
    .mode-btn.active { background: #6366f1; color: #fff; }
    .problem-input {
      flex: 1; background: #0f1117; border: 1px solid #2d3148;
      border-radius: 6px; padding: 6px 12px; color: #e2e8f0;
      font-size: 13px; outline: none;
    }
    .problem-input:focus { border-color: #6366f1; }
    .problem-input::placeholder { color: #4a5568; }
    .hint-config { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #94a3b8; white-space: nowrap; }
    .hint-config select {
      background: #0f1117; border: 1px solid #2d3148;
      color: #e2e8f0; border-radius: 4px; padding: 4px 6px; font-size: 12px;
    }
    .debug-badge {
      font-size: 10px; background: #f59e0b22; color: #f59e0b;
      border: 1px solid #f59e0b44; border-radius: 4px; padding: 3px 7px;
      font-weight: 600; display: none;
    }
    .debug-badge.visible { display: block; }
    .start-btn {
      padding: 7px 18px; background: #22c55e; color: #fff;
      border: none; border-radius: 6px; font-size: 13px;
      font-weight: 600; cursor: pointer; white-space: nowrap;
    }
    .start-btn:disabled { background: #374151; color: #6b7280; cursor: not-allowed; }
    /* PANELS */
    .panels { display: flex; flex: 1; overflow: hidden; }
    .left-panel { width: 42%; display: flex; flex-direction: column; border-right: 1px solid #2d3148; }
    .right-panel { flex: 1; display: flex; flex-direction: column; }
    .panel-header {
      padding: 10px 16px; background: #1a1d27; border-bottom: 1px solid #2d3148;
      font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
      text-transform: uppercase; color: #6366f1;
      display: flex; align-items: center; justify-content: space-between;
    }
    .hint-counter {
      font-size: 11px; font-weight: 600; color: #f59e0b;
      background: #f59e0b18; border: 1px solid #f59e0b33;
      border-radius: 4px; padding: 2px 8px;
    }
    /* TRANSCRIPT */
    .transcript { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
    .msg { display: flex; flex-direction: column; gap: 4px; max-width: 92%; }
    .msg.claude { align-self: flex-start; }
    .msg.user { align-self: flex-end; }
    .msg-label { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
    .msg.claude .msg-label { color: #6366f1; }
    .msg.user .msg-label { color: #22c55e; text-align: right; }
    .msg-bubble { padding: 10px 13px; border-radius: 10px; font-size: 13px; line-height: 1.55; }
    .msg.claude .msg-bubble { background: #1e2235; border: 1px solid #2d3148; border-top-left-radius: 2px; }
    .msg.user .msg-bubble { background: #1e3a2f; border: 1px solid #22c55e33; border-top-right-radius: 2px; }
    .hint-pill {
      display: inline-block; font-size: 10px; background: #f59e0b22;
      color: #f59e0b; border: 1px solid #f59e0b44;
      border-radius: 10px; padding: 1px 8px; margin-bottom: 4px;
    }
    /* RIGHT PANEL */
    .lang-select {
      background: #0f1117; border: none; border-left: 1px solid #2d3148;
      color: #94a3b8; font-size: 11px; padding: 2px 8px; cursor: pointer;
    }
    #monaco-container { flex: 1; }
    #notes-area {
      flex: 1; background: #0d1117; padding: 16px;
      font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px;
      line-height: 1.6; color: #e2e8f0; border: none; outline: none;
      resize: none; display: none;
    }
    /* BOTTOM BAR */
    .bottombar {
      display: flex; align-items: center; gap: 12px; padding: 10px 16px;
      background: #1a1d27; border-top: 1px solid #2d3148; flex-shrink: 0;
    }
    .rec-indicator { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: #4a5568; }
    .rec-indicator.active { color: #ef4444; }
    .rec-dot { width: 10px; height: 10px; border-radius: 50%; background: #4a5568; }
    .rec-indicator.active .rec-dot { background: #ef4444; animation: pulse 1.2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    .hitl-bar {
      flex: 1; background: #0f1117; border: 1px solid #f59e0b44;
      border-radius: 6px; padding: 6px 12px; font-size: 12px;
      display: none; align-items: center; gap: 8px;
    }
    .hitl-bar.visible { display: flex; }
    .hitl-label { color: #f59e0b; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap; }
    .hitl-text { flex: 1; background: transparent; border: none; color: #e2e8f0; font-size: 12px; outline: none; }
    .confirm-btn { padding: 4px 12px; background: #6366f1; color: #fff; border: none; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; }
    .end-btn {
      padding: 7px 18px; background: #ef444422; color: #ef4444;
      border: 1px solid #ef444444; border-radius: 6px; font-size: 13px;
      font-weight: 600; cursor: pointer; white-space: nowrap;
    }
    .end-btn:disabled { opacity: 0.3; cursor: not-allowed; }
    .end-btn:not(:disabled):hover { background: #ef4444; color: #fff; }
    /* TOAST */
    .toast {
      position: fixed; bottom: 70px; left: 50%; transform: translateX(-50%);
      background: #ef4444; color: #fff; padding: 8px 18px; border-radius: 6px;
      font-size: 13px; font-weight: 600; display: none; z-index: 100;
    }
    .toast.visible { display: block; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2d3148; border-radius: 2px; }
  </style>
</head>
<body>

<div class="topbar">
  <div class="mode-toggle">
    <button class="mode-btn active" data-mode="algo">Algo</button>
    <button class="mode-btn" data-mode="system_design">System Design</button>
  </div>
  <input class="problem-input" id="problem-input" placeholder="Paste problem statement here before starting…" />
  <div class="hint-config">
    Max hints:
    <select id="max-hints-select">
      <option value="3">3</option>
      <option value="2">2</option>
      <option value="5">5</option>
      <option value="0">0 (none)</option>
    </select>
  </div>
  <span class="debug-badge" id="debug-badge">DEBUG</span>
  <button class="start-btn" id="start-btn">▶ Start Interview</button>
</div>

<div class="panels">
  <div class="left-panel">
    <div class="panel-header">
      Interviewer
      <span class="hint-counter" id="hint-counter">0 / 3 hints used</span>
    </div>
    <div class="transcript" id="transcript"></div>
  </div>
  <div class="right-panel">
    <div class="panel-header" id="right-panel-header">
      Code Editor
      <select class="lang-select" id="lang-select">
        <option value="python">Python</option>
        <option value="java">Java</option>
        <option value="javascript">JavaScript</option>
        <option value="cpp">C++</option>
      </select>
    </div>
    <div id="monaco-container"></div>
    <textarea id="notes-area" placeholder="Use this space for system design notes, diagrams (ASCII), component lists…"></textarea>
  </div>
</div>

<div class="bottombar">
  <div class="rec-indicator" id="rec-indicator">
    <div class="rec-dot"></div>
    <span id="rec-label">Idle</span>
  </div>
  <div class="hitl-bar" id="hitl-bar">
    <span class="hitl-label">Transcript</span>
    <input class="hitl-text" id="hitl-text" type="text" />
    <button class="confirm-btn" id="confirm-btn">✓ Confirm</button>
  </div>
  <button class="end-btn" id="end-btn" disabled>■ End Interview</button>
</div>

<div class="toast" id="toast"></div>

<!-- JS added in subsequent tasks -->
<script>
  const DEBUG_MODE = false; // overridden by server in next task
</script>
</body>
</html>
```

- [ ] **Step 2: Verify layout renders**

With the server running, visit `http://localhost:8000`. You should see the dark theme layout with all panels — top bar, split panels, bottom bar.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add frontend base layout and CSS"
```

---

## Task 6: Frontend — Mode Toggle + Monaco Editor

**Files:**
- Modify: `static/index.html` — add Monaco CDN + mode/editor JS

- [ ] **Step 1: Add Monaco CDN and mode toggle JS**

Add before the closing `</body>` tag, replacing the existing `<script>` block:

```html
<!-- Monaco Editor -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js"></script>

<script>
// ── CONFIG (injected from server meta tag in Task 7; hardcoded for now) ──
const DEBUG_MODE = document.querySelector('meta[name="debug"]')?.content === 'true';
const SERVER_MAX_HINTS = parseInt(document.querySelector('meta[name="max-hints"]')?.content || '3');
if (DEBUG_MODE) document.getElementById('debug-badge').classList.add('visible');

// ── STATE ──
let currentMode = 'algo';
let monacoEditor = null;
let sessionActive = false;
let hintsUsed = 0;
let maxHints = SERVER_MAX_HINTS;
let conversationHistory = [];
let sessionStartTime = null;
let transcriptLog = [];

// ── MONACO INIT ──
require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
require(['vs/editor/editor.main'], function () {
  monacoEditor = monaco.editor.create(document.getElementById('monaco-container'), {
    value: '# Write your solution here\n',
    language: 'python',
    theme: 'vs-dark',
    fontSize: 13,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: true,
  });
});

// ── MODE TOGGLE ──
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (sessionActive) return; // lock during interview
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentMode = btn.dataset.mode;
    updateRightPanel();
  });
});

function updateRightPanel() {
  const header = document.getElementById('right-panel-header');
  const langSelect = document.getElementById('lang-select');
  const monacoEl = document.getElementById('monaco-container');
  const notesEl = document.getElementById('notes-area');

  if (currentMode === 'algo') {
    header.childNodes[0].textContent = 'Code Editor ';
    langSelect.style.display = '';
    monacoEl.style.display = 'block';
    notesEl.style.display = 'none';
  } else {
    header.childNodes[0].textContent = 'Notes ';
    langSelect.style.display = 'none';
    monacoEl.style.display = 'none';
    notesEl.style.display = 'block';
  }
}

// ── LANGUAGE TOGGLE ──
document.getElementById('lang-select').addEventListener('change', (e) => {
  if (!monacoEditor) return;
  monaco.editor.setModelLanguage(monacoEditor.getModel(), e.target.value);
});

// ── HINT COUNTER DISPLAY ──
function updateHintCounter() {
  maxHints = parseInt(document.getElementById('max-hints-select').value);
  document.getElementById('hint-counter').textContent = `${hintsUsed} / ${maxHints} hints used`;
}
document.getElementById('max-hints-select').addEventListener('change', updateHintCounter);
updateHintCounter();

// ── TOAST ──
function showToast(msg, duration = 3000) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('visible');
  setTimeout(() => el.classList.remove('visible'), duration);
}
</script>
```

- [ ] **Step 2: Verify Monaco loads**

Visit `http://localhost:8000`. The right panel should show a dark Monaco editor with Python syntax. The mode toggle (Algo / System Design) should swap between the editor and the notes textarea.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add Monaco editor and mode toggle"
```

---

## Task 7: Frontend — Server Config Injection

**Files:**
- Modify: `main.py` — serve HTML with injected meta tags for DEBUG and MAX_HINTS
- Modify: `static/index.html` — add meta tags in `<head>`

The frontend needs to know `DEBUG` and `MAX_HINTS` from the server's `.env` without hardcoding them.

- [ ] **Step 1: Add meta tags to `<head>` in `static/index.html`**

Add after the `<title>` line:

```html
<meta name="debug" content="__DEBUG__" />
<meta name="max-hints" content="__MAX_HINTS__" />
```

- [ ] **Step 2: Replace the `index()` route in `main.py` to inject values**

```python
@app.get("/")
async def index():
    html = Path("static/index.html").read_text()
    html = html.replace("__DEBUG__", os.getenv("DEBUG", "false").lower())
    html = html.replace("__MAX_HINTS__", os.getenv("MAX_HINTS", "3"))
    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)
```

Also remove the `app.mount("/static", ...)` line and replace with a route that still serves static assets — or keep the mount for other assets and just override `/`. Keep the `StaticFiles` mount as-is for future assets; the `/` override works because FastAPI matches explicit routes before mounts.

- [ ] **Step 3: Verify injection works**

Restart server with `DEBUG=true` in `.env`. Open browser DevTools → Elements → find `<meta name="debug" content="true">`. The DEBUG badge in the top bar should appear.

- [ ] **Step 4: Commit**

```bash
git add static/index.html main.py
git commit -m "feat: inject server config (DEBUG, MAX_HINTS) into frontend via meta tags"
```

---

## Task 8: Frontend — Audio Recording + Silence Detection

**Files:**
- Modify: `static/index.html` — add audio pipeline JS

- [ ] **Step 1: Add audio recording JS**

Add inside the `<script>` block, after the toast function:

```javascript
// ── AUDIO STATE ──
let mediaRecorder = null;
let audioChunks = [];
let audioContext = null;
let analyser = null;
let silenceStart = null;
let silenceDetectionId = null;
let stream = null;

const SILENCE_THRESHOLD = 0.015; // RMS amplitude threshold
const SILENCE_DURATION_MS = 1500;

// ── START RECORDING ──
async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showToast('Microphone access denied');
    throw err;
  }

  audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);

  mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) audioChunks.push(e.data);
  };
  mediaRecorder.start(100); // collect chunks every 100ms

  silenceDetectionId = requestAnimationFrame(detectSilence);
}

// ── SILENCE DETECTION LOOP ──
function detectSilence() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(data);

  let sum = 0;
  for (let i = 0; i < data.length; i++) {
    const v = (data[i] - 128) / 128;
    sum += v * v;
  }
  const rms = Math.sqrt(sum / data.length);
  const now = Date.now();

  if (rms < SILENCE_THRESHOLD) {
    if (!silenceStart) {
      silenceStart = now;
    } else if (now - silenceStart >= SILENCE_DURATION_MS && audioChunks.length > 0) {
      processChunk();
      silenceStart = null;
    }
  } else {
    silenceStart = null;
  }

  silenceDetectionId = requestAnimationFrame(detectSilence);
}

// ── PROCESS AUDIO CHUNK ──
async function processChunk() {
  if (audioChunks.length === 0) return;
  const blob = new Blob(audioChunks, { type: 'audio/webm' });
  audioChunks = [];

  const formData = new FormData();
  formData.append('audio', blob, 'audio.webm');

  let transcript;
  try {
    const res = await fetch('/transcribe', { method: 'POST', body: formData });
    const data = await res.json();
    transcript = data.transcript;
  } catch (err) {
    showToast('Transcription failed — continuing');
    return;
  }

  // Dev mode: show even empty transcript so user can correct; prod: skip empty
  if (!transcript && !DEBUG_MODE) return;

  if (DEBUG_MODE) {
    showHITL(transcript || '');
  } else {
    await sendToClaudeWrapper(transcript);
  }
}

// ── STOP RECORDING ──
function stopRecording() {
  if (silenceDetectionId) cancelAnimationFrame(silenceDetectionId);
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  if (audioContext) audioContext.close();
  if (stream) stream.getTracks().forEach(t => t.stop());
  mediaRecorder = null;
  audioContext = null;
  analyser = null;
  stream = null;
}
```

- [ ] **Step 2: Verify no JS errors**

Open browser DevTools console, reload the page. No errors should appear. The audio functions are defined but not yet called.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add audio recording and silence detection pipeline"
```

---

## Task 9: Frontend — HITL, Claude Chat, and Transcript Display

**Files:**
- Modify: `static/index.html` — add HITL, sendToClaudeWrapper, appendMessage JS

- [ ] **Step 1: Add transcript display, HITL, and Claude chat JS**

Add inside the `<script>` block, after the stopRecording function:

```javascript
// ── APPEND MESSAGE TO LEFT PANEL ──
function appendMessage(role, content, isHint = false) {
  const el = document.createElement('div');
  el.className = `msg ${role === 'assistant' ? 'claude' : 'user'}`;

  const label = document.createElement('span');
  label.className = 'msg-label';
  label.textContent = role === 'assistant' ? 'Claude' : 'You';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (isHint) {
    const pill = document.createElement('span');
    pill.className = 'hint-pill';
    pill.textContent = `Hint ${hintsUsed} / ${maxHints}`;
    bubble.appendChild(pill);
    bubble.appendChild(document.createElement('br'));
  }

  bubble.appendChild(document.createTextNode(content));
  el.appendChild(label);
  el.appendChild(bubble);

  const transcript = document.getElementById('transcript');
  transcript.appendChild(el);
  transcript.scrollTop = transcript.scrollHeight;

  // Log to session transcript
  const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
  transcriptLog.push({ role: role === 'assistant' ? 'assistant' : 'user', content, ts });
}

// ── SEND TO CLAUDE ──
async function sendToClaudeWrapper(userText) {
  if (!userText.trim()) return;

  appendMessage('user', userText);
  conversationHistory.push({ role: 'user', content: userText });

  let result;
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: conversationHistory,
        mode: currentMode,
        problem: document.getElementById('problem-input').value,
        max_hints: maxHints,
        hints_remaining: maxHints - hintsUsed,
      }),
    });
    result = await res.json();
  } catch (err) {
    showToast('Claude API error — retrying…');
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: conversationHistory,
          mode: currentMode,
          problem: document.getElementById('problem-input').value,
          max_hints: maxHints,
          hints_remaining: maxHints - hintsUsed,
        }),
      });
      result = await res.json();
    } catch {
      const errMsg = 'Connection issue. Please try again.';
      appendMessage('assistant', errMsg);
      conversationHistory.push({ role: 'assistant', content: errMsg });
      return;
    }
  }

  if (result.hint_used) {
    hintsUsed++;
    updateHintCounter();
  }

  appendMessage('assistant', result.content, result.hint_used);
  conversationHistory.push({ role: 'assistant', content: result.content });
}

// ── DEV MODE HITL ──
let pendingHITLResolve = null;

function showHITL(transcript) {
  const bar = document.getElementById('hitl-bar');
  const input = document.getElementById('hitl-text');
  bar.classList.add('visible');
  input.value = transcript;
  input.focus();

  // Resolve when confirmed
  pendingHITLResolve = async (confirmedText) => {
    bar.classList.remove('visible');
    await sendToClaudeWrapper(confirmedText);
  };
}

document.getElementById('confirm-btn').addEventListener('click', () => {
  if (pendingHITLResolve) {
    const text = document.getElementById('hitl-text').value;
    pendingHITLResolve(text);
    pendingHITLResolve = null;
  }
});

document.getElementById('hitl-text').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && pendingHITLResolve) {
    pendingHITLResolve(e.target.value);
    pendingHITLResolve = null;
  }
});
```

- [ ] **Step 2: Verify Claude chat works manually**

In the browser console, test the chat function directly:

```javascript
sendToClaudeWrapper("Can the array be empty?")
```

Expected: Your message appears in the left panel as a user bubble, then Claude's interviewer response appears below it.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add transcript display, HITL dev mode, and Claude chat integration"
```

---

## Task 10: Frontend — Start/End Interview Session Management

**Files:**
- Modify: `static/index.html` — wire up Start and End buttons

- [ ] **Step 1: Add session management JS**

Add inside the `<script>` block, after the HITL section:

```javascript
// ── START INTERVIEW ──
document.getElementById('start-btn').addEventListener('click', async () => {
  const problem = document.getElementById('problem-input').value.trim();
  if (!problem) {
    showToast('Please paste a problem statement first');
    return;
  }

  // Reset session state
  sessionActive = true;
  hintsUsed = 0;
  maxHints = parseInt(document.getElementById('max-hints-select').value);
  conversationHistory = [];
  transcriptLog = [];
  sessionStartTime = Date.now();
  document.getElementById('transcript').innerHTML = '';
  updateHintCounter();

  // Lock UI
  document.getElementById('start-btn').disabled = true;
  document.getElementById('end-btn').disabled = false;
  document.getElementById('problem-input').disabled = true;
  document.querySelectorAll('.mode-btn').forEach(b => b.disabled = true);
  document.getElementById('max-hints-select').disabled = true;

  // Update recording indicator
  const rec = document.getElementById('rec-indicator');
  rec.classList.add('active');
  document.getElementById('rec-label').textContent = 'Recording';

  // Start recording
  try {
    await startRecording();
  } catch {
    // startRecording shows toast on mic deny
    resetSessionUI();
    return;
  }

  // Send opening message from Claude
  const openingMsg = currentMode === 'algo'
    ? `I'll be your interviewer today. Here's your problem:\n\n${problem}\n\nBefore writing any code — what clarifying questions do you have?`
    : `I'll be your interviewer today. Here's your system design problem:\n\n${problem}\n\nLet's start with the requirements. What clarifying questions do you have?`;

  appendMessage('assistant', openingMsg);
  conversationHistory.push({ role: 'assistant', content: openingMsg });
});

// ── END INTERVIEW ──
document.getElementById('end-btn').addEventListener('click', async () => {
  stopRecording();
  sessionActive = false;

  const durationSeconds = Math.floor((Date.now() - sessionStartTime) / 1000);

  // Save session to disk (fire and forget)
  fetch('/session/end', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mode: currentMode,
      problem: document.getElementById('problem-input').value,
      duration_seconds: durationSeconds,
      hints_used: hintsUsed,
      max_hints: maxHints,
      transcript: transcriptLog,
    }),
  }).catch(err => console.error('Failed to save session:', err));

  showToast(`Interview ended. Duration: ${Math.floor(durationSeconds / 60)}m ${durationSeconds % 60}s. Transcript saved.`, 5000);
  resetSessionUI();
});

function resetSessionUI() {
  sessionActive = false;
  document.getElementById('start-btn').disabled = false;
  document.getElementById('end-btn').disabled = true;
  document.getElementById('problem-input').disabled = false;
  document.querySelectorAll('.mode-btn').forEach(b => b.disabled = false);
  document.getElementById('max-hints-select').disabled = false;
  document.getElementById('rec-indicator').classList.remove('active');
  document.getElementById('rec-label').textContent = 'Idle';
  document.getElementById('hitl-bar').classList.remove('visible');
}
```

- [ ] **Step 2: Full end-to-end smoke test**

1. Start the server: `uvicorn main:app --reload`
2. Open `http://localhost:8000`
3. Select "Algo" mode
4. Paste: `Given an array of integers nums and an integer target, return the indices of the two numbers that add up to target.`
5. Click **▶ Start Interview** — Claude's opening message should appear in the left panel
6. Speak: "Can the array be empty?" — after 1.5s silence, it should transcribe and Claude should respond
7. Click **■ End Interview**
8. Check `interviews/` directory: `ls interviews/ && cat interviews/*.json`

Expected: JSON file with full transcript.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: wire up start/end interview session management"
```

---

## Task 11: Final Polish + `.env` Guard

**Files:**
- Modify: `main.py` — startup validation
- Modify: `static/index.html` — minor UX fixes

- [ ] **Step 1: Add startup validation in `main.py`**

Add at the top of the `startup()` function, before `INTERVIEWS_DIR.mkdir(...)`:

```python
@app.on_event("startup")
async def startup():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")
    INTERVIEWS_DIR.mkdir(exist_ok=True)
    load_model(os.getenv("WHISPER_MODEL", "base"))
    print(f"[startup] Whisper model: {os.getenv('WHISPER_MODEL', 'base')}")
    print(f"[startup] Debug mode: {os.getenv('DEBUG', 'false')}")
    print(f"[startup] Max hints default: {os.getenv('MAX_HINTS', '3')}")
    print("[startup] Ready at http://localhost:8000")
```

- [ ] **Step 2: Verify startup logs**

```bash
uvicorn main:app --reload
```

Expected output:
```
[startup] Whisper model: base
[startup] Debug mode: false
[startup] Max hints default: 3
[startup] Ready at http://localhost:8000
```

- [ ] **Step 3: Final commit**

```bash
git add main.py static/index.html
git commit -m "feat: add startup validation and config logging"
```

---

## Running the App

```bash
cd /Users/shafieenibrahim/Documents/Projects/interview-coach
uvicorn main:app --reload
# Open http://localhost:8000
```

To enable dev mode (HITL transcript confirmation):

```bash
# In .env:
DEBUG=true
```
