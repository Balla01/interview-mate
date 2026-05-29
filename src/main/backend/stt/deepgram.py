import asyncio
import threading
from typing import Callable, Optional

from deepgram import DeepgramClient
from deepgram.core.events import EventType

from ..config import DEEPGRAM_API_KEY, SAMPLE_RATE


class DeepgramStream:
    """Wraps a Deepgram live-transcription WebSocket for one audio source."""

    def __init__(
        self,
        speaker_label: str,
        on_transcript: Callable[[str, str, bool], None],
        loop: asyncio.AbstractEventLoop,
        diarize: bool = False,
    ):
        self._label = speaker_label
        self._on_transcript = on_transcript  # (speaker, text, is_final)
        self._loop = loop
        self._diarize = diarize
        self._client = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        self._conn = None
        self._conn_cm = None

    def open(self) -> None:
        kwargs = dict(
            model="nova-3",
            encoding="linear16",
            sample_rate=SAMPLE_RATE,
            language="en",
            interim_results="true",
            smart_format="true",
        )
        if self._diarize:
            kwargs["diarize"] = "true"

        self._conn_cm = self._client.listen.v1.connect(**kwargs)
        self._conn = self._conn_cm.__enter__()
        self._conn.on(EventType.MESSAGE, self._on_message)
        threading.Thread(target=self._conn.start_listening, daemon=True).start()

    def _on_message(self, msg) -> None:
        try:
            if self._diarize:
                self._handle_diarized(msg)
            else:
                text = msg.channel.alternatives[0].transcript
                if text:
                    self._emit(self._label, text, bool(getattr(msg, "is_final", False)))
        except Exception:
            pass

    def _handle_diarized(self, msg) -> None:
        words = getattr(msg.channel.alternatives[0], "words", None) or []
        is_final = bool(getattr(msg, "is_final", False))
        if not words:
            return

        current_speaker: Optional[int] = None
        current_words: list[str] = []

        for w in words:
            spk = getattr(w, "speaker", 0)
            word_text = getattr(w, "punctuated_word", None) or getattr(w, "word", "")
            if current_speaker is None:
                current_speaker = spk
            if spk == current_speaker:
                current_words.append(word_text)
            else:
                self._emit(f"speaker_{current_speaker}", " ".join(current_words), is_final)
                current_speaker = spk
                current_words = [word_text]

        if current_words:
            self._emit(f"speaker_{current_speaker}", " ".join(current_words), is_final)

    def _emit(self, speaker: str, text: str, is_final: bool) -> None:
        self._loop.call_soon_threadsafe(self._on_transcript, speaker, text, is_final)

    def send(self, pcm_bytes: bytes) -> None:
        if self._conn:
            try:
                self._conn.send_media(pcm_bytes)
            except Exception:
                pass

    def close(self) -> None:
        if self._conn_cm:
            try:
                self._conn_cm.__exit__(None, None, None)
            except Exception:
                pass
        self._conn = None
        self._conn_cm = None
