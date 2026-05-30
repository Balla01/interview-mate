import asyncio
import time
import threading
from enum import Enum
from typing import Optional

from fastapi import WebSocket

from .config import (
    COOLDOWN_DURATION,
    FALLBACK_TIMEOUT,
    INTENT_CHECK_INTERVAL,
    MIN_WORDS_FOR_INTENT,
    SPEECH_GAP_TRIGGER,
)
from .context.manager import ConversationContext
from .debug_logger import SessionLogger
from .llm.domain import extract_domain_context
from .llm.groq import stream_tokens
from .llm.intent import detect_intent
from .llm.rephrase import rephrase_question
from .stt.deepgram import DeepgramStream


class _State(Enum):
    COLLECTING = "collecting"
    PROCESSING = "processing"
    COOLDOWN   = "cooldown"


class InterviewSession:
    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self._ws     = websocket
        self._loop   = loop
        self._context = ConversationContext()
        self._mode   = "one_way"
        self._running = False

        self._mic_stream: Optional[DeepgramStream] = None
        self._sys_stream: Optional[DeepgramStream] = None

        self._active_speaker: str = "interviewer"

        # Debug logger (created fresh on each start)
        self._log: Optional[SessionLogger] = None

        # Domain/skill context (set once at session start)
        self._domain_context: str = ""

        # Pipeline
        self._state               = _State.COLLECTING
        self._interviewer_buffer  = ""
        self._buffer_start_at: float = 0.0   # when buffer first got content
        self._last_final_at:   float = 0.0   # time of last interviewer final transcript
        self._last_intent_at:  float = 0.0   # time of last intent check

        self._pipeline_task: Optional[asyncio.Task] = None

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def switch_speaker(self) -> str:
        self._active_speaker = (
            "interviewee" if self._active_speaker == "interviewer" else "interviewer"
        )
        return self._active_speaker

    async def start(self, config: dict) -> None:
        self._mode = config.get("mode", "one_way")
        self._context.clear()
        self._running = True
        self._domain_context = ""
        self._log = SessionLogger()
        self._log.set_mode(self._mode)

        # Extract domain context if user provided skill info
        raw_domain = config.get("domain", "").strip()
        if raw_domain:
            await self._send({"type": "pipeline_status", "stage": "extracting_domain"})
            t0 = time.perf_counter()
            self._domain_context = await self._loop.run_in_executor(
                None, extract_domain_context, raw_domain
            )
            ms = int((time.perf_counter() - t0) * 1000)
            if self._log:
                self._log.log_domain(raw_domain, self._domain_context, ms)
            await self._send({
                "type": "domain_extracted",
                "context": self._domain_context,
            })

        self._reset_collection(clear_buffer=True)
        self._open_streams()
        self._pipeline_task = asyncio.create_task(self._run_pipeline())
        await self._send({"type": "session_started", "mode": self._mode})

    async def stop(self) -> None:
        self._running = False
        if self._pipeline_task and not self._pipeline_task.done():
            self._pipeline_task.cancel()
        if self._mic_stream:
            self._mic_stream.close()
        if self._sys_stream:
            self._sys_stream.close()
        self._mic_stream = self._sys_stream = None
        if self._log:
            path = self._log.save()
            await self._send({"type": "debug_log_saved", "path": path})
        await self._send({"type": "session_stopped"})

    async def handle_audio(self, data: bytes) -> None:
        if not self._running or len(data) < 2:
            return
        channel, pcm = data[0], data[1:]
        if self._mode == "two_way":
            if channel == 0 and self._mic_stream:
                self._mic_stream.send(pcm)
        else:
            if channel == 0 and self._mic_stream:
                self._mic_stream.send(pcm)
            elif channel == 1 and self._sys_stream:
                self._sys_stream.send(pcm)

    # ──────────────────────────────────────────────────────────────────
    # Deepgram stream setup
    # ──────────────────────────────────────────────────────────────────

    def _open_streams(self) -> None:
        if self._mode == "two_way":
            self._mic_stream = DeepgramStream(
                speaker_label="__dynamic__",
                on_transcript=self._on_transcript_sync,
                loop=self._loop,
            )
            self._mic_stream.open()
        else:
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

    # ──────────────────────────────────────────────────────────────────
    # Transcript ingestion
    # ──────────────────────────────────────────────────────────────────

    def _normalize(self, label: str) -> str:
        return label if label in ("interviewer", "interviewee") else "interviewee"

    def _on_transcript_sync(self, speaker: str, text: str, is_final: bool) -> None:
        effective = self._active_speaker if self._mode == "two_way" else speaker
        asyncio.run_coroutine_threadsafe(
            self._handle_transcript(self._normalize(effective), text, is_final),
            self._loop,
        )

    async def _handle_transcript(self, speaker: str, text: str, is_final: bool) -> None:
        if self._log:
            self._log.log_transcript(speaker, text, is_final)
        await self._send({
            "type": "transcript_update",
            "speaker": speaker,
            "text": text,
            "is_final": is_final,
        })

        if not is_final:
            return

        if speaker == "interviewer":
            self._context.add_interviewer(text)
            # Always buffer regardless of pipeline state —
            # speech during PROCESSING/COOLDOWN is kept so it triggers on next cycle
            now = self._loop.time()
            if not self._buffer_start_at:
                self._buffer_start_at = now
            self._interviewer_buffer = (
                self._interviewer_buffer + " " + text
            ).strip()
            self._last_final_at = now
        else:
            self._context.add_interviewee(text)

    # ──────────────────────────────────────────────────────────────────
    # Pipeline state machine
    # ──────────────────────────────────────────────────────────────────

    def _reset_collection(self, clear_buffer: bool = False) -> None:
        if clear_buffer:
            # Full reset — used on session start only
            self._interviewer_buffer = ""
            self._buffer_start_at    = 0.0
            self._last_final_at      = 0.0
        else:
            # After cooldown — keep any speech that arrived during processing/cooldown
            # Only reset the intent check timer
            if not self._interviewer_buffer:
                self._buffer_start_at = 0.0
                self._last_final_at   = 0.0
        self._last_intent_at = 0.0
        self._state          = _State.COLLECTING

    async def _run_pipeline(self) -> None:
        await self._send({"type": "pipeline_status", "stage": "collecting"})
        while self._running:
            try:
                if self._state == _State.COLLECTING:
                    await self._collecting_tick()

                elif self._state == _State.COOLDOWN:
                    await self._send({"type": "pipeline_status", "stage": "cooldown",
                                      "seconds": int(COOLDOWN_DURATION)})
                    await asyncio.sleep(COOLDOWN_DURATION)
                    self._reset_collection()
                    await self._send({"type": "pipeline_status", "stage": "collecting"})

                else:  # PROCESSING — driven by _do_process
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.5)

    async def _collecting_tick(self) -> None:
        buffer = self._interviewer_buffer.strip()

        # Nothing collected yet — just wait
        if not buffer:
            await asyncio.sleep(0.3)
            return

        words = buffer.split()
        now   = self._loop.time()

        # ── Trigger 1: speech gap (any buffer size, 2s silence) ───
        if self._last_final_at and (now - self._last_final_at) >= SPEECH_GAP_TRIGGER:
            await self._intent_then_process("speech_gap")
            return

        # ── Trigger 2: intent check (≥5 words, every 3s) ──────────
        if len(words) >= MIN_WORDS_FOR_INTENT:
            since_intent = (now - self._last_intent_at) if self._last_intent_at else INTENT_CHECK_INTERVAL + 1
            if since_intent >= INTENT_CHECK_INTERVAL:
                self._last_intent_at = now
                is_clear, buf, ms = await self._run_detect_intent("intent_check")
                if is_clear:
                    await self._do_process("intent_check", is_clear, buf, ms)
                    return

        # ── Trigger 3: fallback (any buffer size, 5s elapsed) ─────
        if self._buffer_start_at and (now - self._buffer_start_at) >= FALLBACK_TIMEOUT:
            await self._do_process("fallback", is_clear=False)
            return

        await asyncio.sleep(0.3)

    async def _intent_then_process(self, trigger: str) -> None:
        is_clear, buf, ms = await self._run_detect_intent(trigger)
        await self._do_process(trigger, is_clear, buf, ms)

    async def _run_detect_intent(self, trigger: str) -> tuple[bool, str, int]:
        """Returns (is_clear, buffer_used, duration_ms) — logging deferred to _do_process."""
        buf = self._interviewer_buffer
        await self._send({"type": "pipeline_status", "stage": "detecting_intent"})
        t0 = time.perf_counter()
        is_clear = await self._loop.run_in_executor(None, detect_intent, buf)
        ms = int((time.perf_counter() - t0) * 1000)
        return is_clear, buf, ms

    async def _do_process(
        self,
        trigger: str,
        is_clear: bool,
        intent_buf: str = "",
        intent_ms: int = 0,
    ) -> None:
        self._state = _State.PROCESSING
        buffer = self._interviewer_buffer.strip()

        # Clear buffer immediately — new speech during processing accumulates fresh
        self._interviewer_buffer = ""
        self._buffer_start_at    = 0.0
        self._last_final_at      = 0.0
        self._last_intent_at     = 0.0

        if self._log:
            self._log.start_cycle(trigger, buffer)
            if trigger != "fallback":
                self._log.log_intent(intent_buf or buffer, is_clear, intent_ms)

        # ── Step 1: Rephrase raw buffer using context + domain ─────
        await self._send({"type": "pipeline_status", "stage": "rephrasing"})
        past = self._context.get_past_questions()

        t0 = time.perf_counter()
        question = await self._loop.run_in_executor(
            None, rephrase_question, buffer, past, self._domain_context
        )
        ms = int((time.perf_counter() - t0) * 1000)

        if self._log:
            self._log.log_rephrase(buffer, past, self._domain_context, question, ms)

        if not question:
            if self._log:
                self._log.end_cycle()
            self._state = _State.COLLECTING
            return

        await self._send({"type": "question_formed", "question": question})

        # ── Step 2: Stream answer ──────────────────────────────────
        await self._send({"type": "pipeline_status", "stage": "answering"})
        context_str = self._context.format_for_answer(question, self._domain_context)

        await self._send({
            "type": "llm_suggestion_update",
            "text": "", "done": False, "reset": True,
        })

        q: asyncio.Queue[Optional[str]] = asyncio.Queue()
        answer_tokens: list[str] = []
        t0 = time.perf_counter()

        def _produce() -> None:
            try:
                for token in stream_tokens(context_str, has_domain=bool(self._domain_context)):
                    self._loop.call_soon_threadsafe(q.put_nowait, token)
            except Exception as exc:
                self._loop.call_soon_threadsafe(q.put_nowait, f"\n\n[Error: {exc}]")
            finally:
                self._loop.call_soon_threadsafe(q.put_nowait, None)

        threading.Thread(target=_produce, daemon=True).start()

        try:
            while True:
                token = await q.get()
                if token is None:
                    break
                answer_tokens.append(token)
                await self._send({
                    "type": "llm_suggestion_update",
                    "text": token, "done": False, "reset": False,
                })
        except asyncio.CancelledError:
            if self._log:
                self._log.end_cycle()
            return

        answer_ms = int((time.perf_counter() - t0) * 1000)
        full_answer = "".join(answer_tokens)

        if self._log:
            self._log.log_answer(question, context_str, full_answer, answer_ms)
            self._log.end_cycle()

        await self._send({
            "type": "llm_suggestion_update",
            "text": "", "done": True, "reset": False,
        })

        self._context.add_answered(question)
        self._state = _State.COOLDOWN

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    async def _send(self, data: dict) -> None:
        try:
            await self._ws.send_json(data)
        except Exception:
            pass
