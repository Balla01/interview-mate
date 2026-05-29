"""
Session debug logger.

Saves a timestamped JSON file to <project_root>/logs/ when a session ends.
File name: session_YYYY-MM-DD_HH-MM-SS.json
"""

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"


class SessionLogger:
    def __init__(self):
        now = datetime.now()
        self._session_id = now.strftime("%Y-%m-%d_%H-%M-%S")
        self._doc: dict = {
            "session_id":  self._session_id,
            "started_at":  now.isoformat(),
            "ended_at":    None,
            "mode":        None,
            "transcript":  [],          # every Deepgram event
            "cycles":      [],          # one entry per interviewer question processed
        }
        self._current_cycle: Optional[dict] = None

    # ── Session-level ──────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        self._doc["mode"] = mode

    def log_transcript(self, speaker: str, text: str, is_final: bool) -> None:
        self._doc["transcript"].append({
            "ts":       datetime.now().isoformat(),
            "speaker":  speaker,
            "text":     text,
            "is_final": is_final,
        })

    # ── Cycle-level (one per Q&A round) ───────────────────────────────

    def start_cycle(self, trigger: str, buffer: str) -> None:
        """Call when a trigger fires and we begin processing a question."""
        self._current_cycle = {
            "cycle":              len(self._doc["cycles"]) + 1,
            "started_at":         datetime.now().isoformat(),
            "trigger":            trigger,           # "speech_gap" | "intent_check" | "fallback"
            "buffer_collected":   buffer,
            "buffer_word_count":  len(buffer.split()),
            "llm_calls": {
                "intent":   None,   # filled by log_intent()
                "rephrase": None,   # filled by log_rephrase()
                "answer":   None,   # filled by log_answer()
            },
            "ended_at": None,
        }

    def end_cycle(self) -> None:
        if self._current_cycle:
            self._current_cycle["ended_at"] = datetime.now().isoformat()
            self._doc["cycles"].append(self._current_cycle)
            self._current_cycle = None

    # ── LLM call helpers ───────────────────────────────────────────────

    def log_intent(self, buffer: str, is_clear: bool, duration_ms: int) -> None:
        self._set_llm("intent", {
            "input":       {"buffer": buffer},
            "output":      "CLEAR" if is_clear else "UNCLEAR",
            "duration_ms": duration_ms,
        })

    def log_rephrase(
        self,
        buffer: str,
        past_questions: list[str],
        domain_context: str,
        output: str,
        duration_ms: int,
    ) -> None:
        self._set_llm("rephrase", {
            "input": {
                "raw_buffer":     buffer,
                "past_questions": past_questions,
                "domain_context": domain_context or None,
            },
            "output":      output,
            "duration_ms": duration_ms,
        })

    def log_domain(self, raw_input: str, output: str, duration_ms: int) -> None:
        """Logged at session level, not cycle level."""
        self._doc["domain_extraction"] = {
            "called_at":   datetime.now().isoformat(),
            "input":       raw_input,
            "output":      output,
            "duration_ms": duration_ms,
        }

    def log_answer(self, question: str, context_str: str, output: str, duration_ms: int) -> None:
        self._set_llm("answer", {
            "input": {
                "question":    question,
                "context_str": context_str,
            },
            "output":      output,           # full streamed answer text
            "duration_ms": duration_ms,
        })

    def _set_llm(self, stage: str, data: dict) -> None:
        if self._current_cycle:
            self._current_cycle["llm_calls"][stage] = {
                "called_at": datetime.now().isoformat(),
                **data,
            }

    # ── Timing context manager ─────────────────────────────────────────

    @staticmethod
    @contextmanager
    def timer():
        """Usage:  with SessionLogger.timer() as t: ...; ms = t()"""
        start = time.perf_counter()
        result = []
        yield lambda: result[0]
        result.append(int((time.perf_counter() - start) * 1000))

    # ── Save ───────────────────────────────────────────────────────────

    def save(self) -> str:
        self._doc["ended_at"] = datetime.now().isoformat()
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = _LOG_DIR / f"session_{self._session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._doc, f, indent=2, ensure_ascii=False)
        return str(path)
