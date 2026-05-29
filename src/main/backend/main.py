import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import DEEPGRAM_API_KEY, GROQ_API_KEY, LLM_MODEL
from .session import InterviewSession

app = FastAPI(title="InterviewMate API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/info")
def info():
    """API capabilities and configuration summary."""
    return {
        "version": "1.0.0",
        "llm_model": LLM_MODEL,
        "deepgram_key_set": bool(DEEPGRAM_API_KEY),
        "groq_key_set": bool(GROQ_API_KEY),
        "modes": ["one_way (Online Call)", "two_way (In-Person Call)"],
        "audio_source": "browser (getUserMedia / getDisplayMedia)",
        "websocket": "ws://localhost:8000/ws",
        "events": {
            "client_sends": ["start_session", "stop_session", "<binary PCM>"],
            "server_sends": ["session_started", "session_stopped", "transcript_update", "llm_suggestion_update"],
        },
    }


@app.get("/devices")
def list_devices():
    """
    Audio devices visible to the server process.
    NOTE: Audio capture is browser-side — this is for diagnostic use only.
    In WSL the list will be empty; run on native Windows Python to see devices.
    """
    try:
        import sounddevice as sd
        mics = [
            {"id": i, "name": d["name"]}
            for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0
        ]
    except Exception as exc:
        mics = []
    return {
        "note": "Audio capture is handled by the browser, not the server.",
        "server_visible_mics": mics,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    session = InterviewSession(websocket, loop)

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            # Text → JSON control messages
            if message.get("text"):
                data = json.loads(message["text"])
                msg_type = data.get("type")
                if msg_type == "start_session":
                    await session.start(data)
                elif msg_type == "stop_session":
                    await session.stop()
                elif msg_type == "switch_speaker":
                    new_active = session.switch_speaker()
                    await session._send({"type": "speaker_switched", "active": new_active})

            # Bytes → raw PCM audio from browser
            elif message.get("bytes"):
                await session.handle_audio(message["bytes"])

    except WebSocketDisconnect:
        await session.stop()
    except Exception:
        await session.stop()
