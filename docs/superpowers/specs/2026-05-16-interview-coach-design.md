# Interview Coach — Design Spec
**Date:** 2026-05-16
**Status:** Approved

---

## Overview

A personal, locally-hosted AI interview coach for Staff Software Engineer prep. The user speaks; Whisper transcribes locally; Claude responds as a collaborative interviewer in text. Supports both algorithm/coding and system design interview formats with a Monaco code editor and persistent session transcripts.

---

## Goals

- Practice the full Staff-level interview process (clarify → design → implement → test → complexity → NFRs) with a consistent AI coach
- Voice-first input so practice feels closer to a real interview than typing
- Claude acts as a collaborative interviewer: enforces process, offers hints on request (up to a configurable max), and gives structured feedback when asked to evaluate an approach
- Sessions saved to disk for later review

---

## Non-Goals (MVP)

- Multi-user support
- Built-in problem bank
- Code execution / running tests
- TTS (Claude responds in text only)
- Authentication

---

## Architecture

```
Browser (localhost:8000)
│
├── Top Bar       → Mode toggle (Algo / System Design), problem input, hint max config, Start button
├── Left Panel    → Claude interviewer responses (scrollable), hint counter
├── Right Panel   → Monaco code editor (Algo) or freeform notes textarea (System Design)
└── Bottom Bar    → Recording indicator, dev-mode HITL transcript preview, End Interview button

FastAPI Backend
├── GET  /              → serves static/index.html
├── POST /transcribe    → receives audio blob → Whisper → returns transcript text
├── POST /chat          → conversation history + user message → Claude API → returns response
└── POST /session/end   → receives full session → writes JSON to interviews/
```

### Audio Flow (per utterance)

1. User presses **Start Interview** → browser `MediaRecorder` begins continuous capture
2. `AudioContext` + `AnalyserNode` monitors volume; silence > 1.5s triggers chunk boundary
3. Audio chunk POSTed to `/transcribe` → Whisper processes locally → text returned
4. **Dev mode** (`DEBUG=true`): HITL popup shown in bottom bar — user confirms/edits transcript before it is sent to Claude
5. **Normal mode**: transcript auto-accepted, POSTed to `/chat` immediately
6. Claude response displayed in left panel
7. User presses **End Interview** → `POST /session/end` saves transcript JSON to disk

---

## Components

### `whisper_handler.py`
- Loads Whisper model once at startup (`WHISPER_MODEL` from `.env`, default `base`)
- Exposes `transcribe(audio_bytes) -> str`
- Model size options: `tiny` (~1s), `base` (~2s, default), `small` (~4s)

### `claude_handler.py`
- Builds system prompt dynamically from: interview mode, problem statement, hints remaining
- Maintains no state — conversation history passed in from frontend on each call
- `/chat` returns `{ "content": "...", "hint_used": bool }` — backend detects if Claude prefixed response with `[HINT]` (see system prompt), strips the tag, sets the flag. Frontend uses `hint_used` to decrement its counter reliably.
- System prompt template:

```
You are a collaborative Staff Engineer interviewer. Your role is to guide the candidate through
this process: clarify → design → implement → test → complexity → NFRs.

Rules:
- Do not give away solutions. Push back when steps are skipped.
- You may offer up to {max_hints} hints if the candidate explicitly asks. You have {remaining} remaining.
  Never offer hints unprompted.
- When giving a hint, begin your response with the exact token [HINT] on its own line, then your hint text.
- When the candidate presents an approach and asks for feedback, give structured insight:
  what is strong, what is missing, what tradeoffs to consider. Do not give the full solution.
- Interview type: {mode}. 
  - Algo: enforce Big-O analysis and edge case coverage.
  - System Design: emphasize capacity planning, component tradeoffs, and failure modes.

Problem: {problem_statement}
```

### `main.py`
- FastAPI app with 4 routes (see Architecture)
- Loads Whisper model at startup
- Creates `interviews/` directory at startup if it doesn't exist
- Reads `ANTHROPIC_API_KEY`, `WHISPER_MODEL`, `DEBUG`, `MAX_HINTS` from `.env`

### `static/index.html`
- Single-file frontend: HTML + CSS + JS
- Monaco Editor loaded via CDN
- Conversation history held in JS array, sent with each `/chat` request
- Hint count tracked in JS, decremented on each hint response, included in every `/chat` payload
- Mode toggle swaps right panel between Monaco editor and plain textarea

---

## Data Persistence

Transcripts saved to `interviews/` on session end:

```json
{
  "timestamp": "2026-05-16T14:32:00",
  "mode": "algo",
  "problem": "Given an array of integers...",
  "duration_seconds": 1823,
  "hints_used": 1,
  "max_hints": 3,
  "transcript": [
    { "role": "assistant", "content": "Before writing any code...", "ts": "14:32:05" },
    { "role": "user", "content": "Can the array contain negatives?", "ts": "14:32:38" }
  ]
}
```

Filename format: `interviews/YYYY-MM-DD_HH-MM-SS_<mode>.json`

---

## Dev Mode vs Normal Mode

Controlled by `DEBUG=true/false` in `.env`. Not toggleable from the UI.

| Behavior | Dev Mode | Normal Mode |
|---|---|---|
| Transcript confirmation | HITL popup in bottom bar | Auto-accepted |
| Garbled/empty transcript | Shown for correction | Silently skipped |

---

## Error Handling

| Failure | Behavior |
|---|---|
| Whisper transcription fails | Toast error in UI; recording continues |
| Whisper returns empty text | Dev: shown in HITL. Prod: silently skipped |
| Claude API error / timeout | Inline message in interviewer panel; 1 auto-retry |
| `/session/end` write fails | Logged to server console; does not block UI |

---

## File Structure

```
interview-coach/
├── main.py
├── whisper_handler.py
├── claude_handler.py
├── requirements.txt
├── .env
├── static/
│   └── index.html
├── interviews/            # auto-created at first session end
├── mockup.html            # UI mockup (brainstorming artifact)
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-16-interview-coach-design.md
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required |
| `WHISPER_MODEL` | `base` | Whisper model size: tiny / base / small |
| `DEBUG` | `false` | Enables HITL transcript confirmation |
| `MAX_HINTS` | `3` | Default max hints per session (overridable in UI) |

---

## Dependencies

```
fastapi
uvicorn
openai-whisper
anthropic
python-multipart
torch
```
