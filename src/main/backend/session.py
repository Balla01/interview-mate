import asyncio
import threading
from typing import Optional

from fastapi import WebSocket

from .context.manager import ConversationContext
from .llm.groq import stream_tokens
from .stt.deepgram import DeepgramStream

class InterviewSession:
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self._ws = websocket
        self._loop = loop
        self._context = ConversationContext()
        self._mode = "one_way"
        self._running = False

        # Deepgram streams
        self._mic_stream: Optional[DeepgramStream] = None
        self._sys_stream: Optional[DeepgramStream] = None

        # LLM suggestion task
        self._llm_task: Optional[asyncio.Task] = None

        # Two-way: user manually toggles who is speaking
        self._active_speaker: str = "interviewer"

    def switch_speaker(self) -> str:
        self._active_speaker = (
            "interviewee" if self._active_speaker == "interviewer" else "interviewer"
        )
        return self._active_speaker

    def _normalize_speaker(self, label: str) -> str:
        return label if label in ("interviewer", "interviewee") else "interviewee"

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def start(self, config: dict) -> None:
        self._mode = config.get("mode", "one_way")
        self._context.clear()
        self._running = True
        self._open_streams()
        await self._send({"type": "session_started", "mode": self._mode})

    async def stop(self) -> None:
        self._running = False
        if self._llm_task and not self._llm_task.done():
            self._llm_task.cancel()
        if self._mic_stream:
            self._mic_stream.close()
        if self._sys_stream:
            self._sys_stream.close()
        self._mic_stream = self._sys_stream = None
        await self._send({"type": "session_stopped"})

    # ------------------------------------------------------------------
    # Deepgram stream setup
    # ------------------------------------------------------------------

    def _open_streams(self) -> None:
        if self._mode == "two_way":
            # Single stream — audio always flows, label comes from _active_speaker at transcript time
            self._mic_stream = DeepgramStream(
                speaker_label="__dynamic__",
                on_transcript=self._on_transcript_sync,
                loop=self._loop,
            )
            self._mic_stream.open()
        else:
            # One-way: separate streams for mic (interviewee) and system audio (interviewer)
            self._mic_stream = DeepgramStream(
                speaker_label="interviewee",
                on_transcript=self._on_transcript_sync,
                loop=self._loop,
            )
            self._mic_stream.open()

            self._sys_stream = DeepgramStream(
                speaker_label="interviewer",
                on_transcript=self._on_transcript_sync,
                loop=self._loop,
            )
            self._sys_stream.open()

    # ------------------------------------------------------------------
    # Audio ingestion — called for every binary WebSocket message
    # Binary format: byte[0] = channel (0=mic, 1=system), byte[1:] = PCM Int16
    # ------------------------------------------------------------------

    async def handle_audio(self, data: bytes) -> None:
        """Binary WebSocket message: byte[0]=channel, byte[1:]=PCM Int16."""
        if not self._running or len(data) < 2:
            return
        channel = data[0]
        pcm = data[1:]

        if self._mode == "two_way":
            # Single stream always receives audio — no idle/timeout risk
            if channel == 0 and self._mic_stream:
                self._mic_stream.send(pcm)
        else:
            if channel == 0 and self._mic_stream:
                self._mic_stream.send(pcm)
            elif channel == 1 and self._sys_stream:
                self._sys_stream.send(pcm)

    # ------------------------------------------------------------------
    # Transcript handling
    # ------------------------------------------------------------------

    def _on_transcript_sync(self, speaker: str, text: str, is_final: bool) -> None:
        # Two-way: single stream, label overridden by whoever is currently active
        effective = self._active_speaker if self._mode == "two_way" else speaker
        asyncio.run_coroutine_threadsafe(
            self._handle_transcript(effective, text, is_final),
            self._loop,
        )

    async def _handle_transcript(self, speaker: str, text: str, is_final: bool) -> None:
        normalized = self._normalize_speaker(speaker)
        await self._send({
            "type": "transcript_update",
            "speaker": normalized,       # "interviewer" | "interviewee" — for display
            "speaker_id": speaker,       # "speaker_0" | "speaker_1" — for role assignment
            "text": text,
            "is_final": is_final,
        })

        if is_final:
            if normalized == "interviewer":
                self._context.add_interviewer(text)
                await self._trigger_llm(text)
            else:
                self._context.add_interviewee(text)
        else:
            if normalized == "interviewer" and (
                text.strip().endswith("?") or len(text.split()) >= 10
            ):
                await self._trigger_llm(text, is_partial=True)

    # ------------------------------------------------------------------
    # LLM suggestion streaming
    # ------------------------------------------------------------------

    async def _trigger_llm(self, question: str, is_partial: bool = False) -> None:
        if self._llm_task and not self._llm_task.done():
            self._llm_task.cancel()
            try:
                await self._llm_task
            except (asyncio.CancelledError, Exception):
                pass
        self._llm_task = asyncio.create_task(self._run_llm(question, is_partial))

    async def _run_llm(self, question: str, is_partial: bool = False) -> None:
        context_str = self._context.format_for_llm(question)
        await self._send({
            "type": "llm_suggestion_update",
            "text": "", "done": False, "reset": True, "is_partial": is_partial,
        })

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        def producer() -> None:
            try:
                for token in stream_tokens(context_str):
                    self._loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as exc:
                self._loop.call_soon_threadsafe(queue.put_nowait, f"\n\n[Error: {exc}]")
            finally:
                self._loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=producer, daemon=True).start()

        try:
            while True:
                token = await queue.get()
                if token is None:
                    break
                await self._send({"type": "llm_suggestion_update", "text": token, "done": False, "reset": False})
        except asyncio.CancelledError:
            return

        await self._send({"type": "llm_suggestion_update", "text": "", "done": True, "reset": False})

    async def _send(self, data: dict) -> None:
        try:
            await self._ws.send_json(data)
        except Exception:
            pass
