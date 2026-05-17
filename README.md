# Interview Coach

A local voice-driven interview practice tool that acts as a Staff Engineer interviewer. Speak your answers aloud — the app transcribes your speech with Whisper, sends it to Claude, and responds as a structured technical interviewer.

## What it does

- **Two interview modes** — Algo (Big-O analysis, edge cases) and System Design (capacity planning, component tradeoffs, failure modes)
- **Voice input** — records via browser microphone, auto-submits after 1.5s of silence
- **Claude as interviewer** — enforces a structured flow (clarify → design → implement → test → complexity → NFRs), pushes back when steps are skipped, never gives away solutions
- **Hint system** — configurable hint budget; Claude only gives hints when explicitly asked
- **Session transcripts** — saved as JSON to the `interviews/` directory when you end a session
- **Dev/HITL mode** — optionally review and edit transcriptions before they're sent to Claude

## Setup

**Requirements:** Python 3.10+, [ffmpeg](https://ffmpeg.org/download.html)

```bash
git clone https://github.com/ShafIbrahim/interview-coach
cd interview-coach
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your Anthropic API key
```

**.env options:**

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key. |
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |
| `MAX_HINTS` | `3` | Hint budget per session |
| `DEBUG` | `false` | Enables HITL mode — review/edit each transcription before it's sent |

## Running

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000), paste in a problem statement, choose a mode, and click **Start Interview**.

## Project structure

```
main.py              FastAPI app — /transcribe, /chat, /session/end endpoints
whisper_handler.py   Whisper model loading and transcription
claude_handler.py    Claude API client and system prompt builder
static/index.html    Single-page frontend (recording, silence detection, UI)
interviews/          Auto-saved session transcripts (JSON)
```
