# InterviewMate

A real-time AI interview assistant that listens to a live job interview, transcribes both sides of the conversation, and streams suggested answers to the candidate — all with sub-second latency.

---

## How It Works — Complete Pipeline

### 1. Session Start

The candidate opens the frontend, optionally pastes their skill profile (e.g. "5 years Python backend, FastAPI, PostgreSQL, AWS"), and clicks **Start**.

The browser sends a `start_session` WebSocket message with `mode` and `domain`.

If a skill profile was provided, the backend makes a one-time LLM call (`domain.py`) to extract structured context:

```
• Interview domain
• Key technologies
• Domain terminology
• Answer tone
• Likely interview topics
```

This domain context is saved to `skill_profiles/` and injected into every answer prompt for the rest of the session.

---

### 2. Audio Capture (Browser-Side)

All audio capture happens in the browser — the backend never touches system audio directly.

| Mode | Audio Source |
|---|---|
| **one_way** (Online Call) | Mic via `getUserMedia` (interviewee) + system audio via `getDisplayMedia` (interviewer) |
| **two_way** (In-Person) | Mic only via `getUserMedia`; manual speaker toggle switches who is speaking |

The browser captures raw PCM at 16kHz, 16-bit, mono. Each chunk is prefixed with a **channel byte** before sending over WebSocket:

```
byte 0 = channel (0 = mic / interviewee, 1 = system audio / interviewer)
bytes 1..N = raw PCM
```

---

### 3. Speech-to-Text (Deepgram)

`session.py` routes each incoming PCM chunk to the correct `DeepgramStream` instance (`stt/deepgram.py`).

In **one_way** mode, two Deepgram WebSocket connections run in parallel:

```
mic stream   → speaker_label = "interviewee"
system stream → speaker_label = "interviewer"
```

In **two_way** mode, a single Deepgram stream is open. The active speaker (interviewer / interviewee) is toggled manually from the UI. Deepgram diarization is available but off by default.

Deepgram uses the `nova-3` model with:
- `interim_results = true` — partial transcripts sent as the speaker talks
- `smart_format = true` — punctuation and casing applied automatically

Each transcript event fires `_on_transcript_sync`, which dispatches a `transcript_update` WebSocket message to the frontend and routes the text into the pipeline.

---

### 4. Pipeline State Machine

The heart of the backend is an async state machine inside `InterviewSession` with three states:

```
COLLECTING ──trigger──▶ PROCESSING ──done──▶ COOLDOWN ──timer──▶ COLLECTING
```

#### COLLECTING

Only **interviewer** finals are buffered. Interviewee speech is logged to context but does not affect the pipeline.

Three triggers can fire from the collecting loop (checked every 300ms):

| Trigger | Condition | What happens |
|---|---|---|
| **speech_gap** | 2s of silence after last interviewer final | Run intent check, then process |
| **intent_check** | ≥5 words in buffer, every 3s | Ask LLM if question is clear, process only if `CLEAR` |
| **fallback** | 5s elapsed since first word in buffer | Skip intent check, process raw buffer regardless |

Any speech that arrives while in PROCESSING or COOLDOWN is held in the buffer and triggers the next cycle automatically.

#### PROCESSING — 3-Step Pipeline

**Step 1 — Intent Detection** (`llm/intent.py`)

A fast Groq call asks the LLM a single binary question:

```
CLEAR   → the question is answerable as-is
UNCLEAR → too incomplete or cut off; keep collecting
```

Skipped for the `fallback` trigger (answer regardless).

**Step 2 — Rephrase** (`llm/rephrase.py`)

The raw transcript buffer is cleaned into a single, complete, grammatically correct question.

The rephrase logic distinguishes two cases:

- **Self-contained**: "What is a binary search tree" → "What is a binary search tree and how does it work?" — past questions are ignored entirely.
- **Dependent** (contains pronouns like *it*, *them*, *the difference*, *those*): uses the last 5 answered questions to resolve the reference. Most recent = highest priority.

Domain context can also correct mis-transcribed domain terms (only when 100% confident).

The rephrased question is sent to the frontend as a `question_formed` event.

**Step 3 — Answer Streaming** (`llm/groq.py`, `llm/prompt.py`)

`stream_tokens()` runs in a daemon thread (Groq's sync SDK) and feeds tokens into an `asyncio.Queue`. The main event loop drains the queue and sends each token to the browser as a `llm_suggestion_update` event.

The answer is structured as:

```
**Quick Answer:**
One confident 1-2 sentence answer the candidate can say right now.

**Detailed Answer:**
2-3 paragraphs with a concrete example relevant to the domain.

**Key Points:**
- Most important point
- Second important point
- Third important point
```

If domain context is present, answers use the candidate's actual tech stack and match the expected interview level.

#### COOLDOWN

After an answer is streamed, the pipeline waits 5 seconds before collecting again. This prevents a partial trailing sentence from the interviewer from immediately triggering a new cycle.

---

### 5. Conversation Context

`ConversationContext` (`context/manager.py`) maintains rolling windows using `deque` with bounded sizes:

| Buffer | Max size | Purpose |
|---|---|---|
| `_raw_interviewer` | 20 | All interviewer transcript chunks |
| `_interviewee` | 5 | Interviewee responses |
| `_answered_questions` | 5 | Rephrased questions that have been answered |

The answered questions list is what gets passed to `rephrase_question` for pronoun resolution, and what the answer prompt uses as conversation history.

---

### 6. WebSocket Protocol

```
Client → Server
  { type: "start_session", mode: "one_way"|"two_way", domain: "<skill text>" }
  { type: "stop_session" }
  { type: "switch_speaker" }
  <binary: channel_byte + PCM>

Server → Client
  { type: "session_started", mode }
  { type: "session_stopped" }
  { type: "speaker_switched", active: "interviewer"|"interviewee" }
  { type: "pipeline_status", stage: "collecting"|"detecting_intent"|"rephrasing"|"answering"|"cooldown" }
  { type: "domain_extracted", context }
  { type: "transcript_update", speaker, text, is_final }
  { type: "question_formed", question }
  { type: "llm_suggestion_update", text, done, reset }
  { type: "debug_log_saved", path }
```

---

### 7. Debug Logging

Every session is logged to `logs/session_<timestamp>.json`. The log includes:

- Full transcript (every Deepgram event, final and interim)
- One cycle entry per question processed, containing:
  - Trigger that fired
  - Raw buffer collected
  - Intent LLM call input/output and latency
  - Rephrase LLM call input/output and latency
  - Answer LLM call input/output and latency
- Domain extraction result (if skill profile was provided)

---

## Architecture

```
Browser (React + Tailwind)
│
│  WebSocket ws://backend/ws
│  ├─ binary: PCM audio chunks (channel-prefixed)
│  └─ JSON: control messages ↔ pipeline events + transcript + suggestions
│
FastAPI (main.py)
│
└─ InterviewSession (one per connection)
       │
       ├─ DeepgramStream × 1-2 (live STT, nova-3, 16kHz)
       ├─ ConversationContext (rolling context windows)
       ├─ SessionLogger (debug JSON)
       │
       └─ Async pipeline loop
              │
              ├─ [Groq] intent.py      — CLEAR / UNCLEAR (llama-3.1-8b-instant)
              ├─ [Groq] rephrase.py    — clean question + pronoun resolution
              ├─ [Groq] domain.py      — skill profile extraction (session start only)
              └─ [Groq] groq.py        — streaming answer (llama-3.1-8b-instant)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Deepgram API key
- Groq API key

### Environment

Copy `.env.example` to `.env` at the project root and fill in your keys:

```env
deep_gram_key=your_deepgram_api_key
groq_api=your_groq_api_key
```

### Backend

```bash
cd src/main/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd src/main/frontend
npm install
npm run dev
```

### One Command

```bash
./start.sh
```

---

## Deployment

| Service | Platform |
|---|---|
| Backend | [Railway](https://railway.app) (`railway.json`, `nixpacks.toml`) |
| Frontend | [Vercel](https://vercel.com) (`vercel.json`) |

Set the same environment variables in each platform's dashboard. The frontend's `VITE_WS_URL` should point to the Railway backend WebSocket URL.

---

## Configuration

All pipeline timing constants are in `src/main/backend/config.py`:

| Constant | Default | Description |
|---|---|---|
| `SPEECH_GAP_TRIGGER` | 2.0s | Silence duration to trigger intent + process |
| `INTENT_CHECK_INTERVAL` | 3.0s | Frequency of mid-speech intent checks |
| `FALLBACK_TIMEOUT` | 5.0s | Hard deadline to process even if intent is unclear |
| `COOLDOWN_DURATION` | 5.0s | Wait after each answer before collecting again |
| `MIN_WORDS_FOR_INTENT` | 5 | Minimum words before running intent check |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Groq model for all LLM calls |
| `SAMPLE_RATE` | 16000 Hz | PCM sample rate expected by Deepgram |
