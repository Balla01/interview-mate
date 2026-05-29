import threading
from typing import Callable, Optional

import numpy as np

from ..config import SAMPLE_RATE, CHUNK_FRAMES


def _sd():
    import sounddevice as sd  # lazy — needs PortAudio at runtime, not import time
    return sd


class MicCapture:
    def __init__(self, callback: Callable[[bytes], None], device: Optional[int] = None):
        self._callback = callback
        self._device = device
        self._stream = None

    def start(self) -> None:
        sd = _sd()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_FRAMES,
            device=self._device,
            callback=self._sd_callback,
        )
        self._stream.start()

    def _sd_callback(self, indata, frames, time_info, status) -> None:
        self._callback(indata[:, 0].astype(np.int16).tobytes())

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @staticmethod
    def list_devices() -> list[dict]:
        try:
            sd = _sd()
            return [
                {"id": i, "name": dev["name"]}
                for i, dev in enumerate(sd.query_devices())
                if dev["max_input_channels"] > 0
            ]
        except Exception:
            return []


class SystemAudioCapture:
    """WASAPI loopback for Windows system audio (interviewer voice on headphones)."""

    def __init__(self, callback: Callable[[bytes], None]):
        self._callback = callback
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.available = self._check_available()

    @staticmethod
    def _check_available() -> bool:
        try:
            import pyaudiowpatch  # noqa: F401
            return True
        except ImportError:
            return False

    def start(self) -> bool:
        if not self.available:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _capture_loop(self) -> None:
        import pyaudiowpatch as pyaudio

        p = pyaudio.PyAudio()
        try:
            wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
            loopback = p.get_loopback_device_info_by_speakers_info(speakers)

            src_rate = int(loopback["defaultSampleRate"])
            channels = loopback["maxInputChannels"]
            chunk = int(src_rate * 500 / 1000)

            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=src_rate,
                input=True,
                input_device_index=loopback["index"],
                frames_per_buffer=chunk,
            )
            while self._running:
                raw = stream.read(chunk, exception_on_overflow=False)
                self._callback(self._to_mono_16k(raw, channels, src_rate))
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        finally:
            p.terminate()

    @staticmethod
    def _to_mono_16k(raw: bytes, channels: int, src_rate: int) -> bytes:
        arr = np.frombuffer(raw, dtype=np.int16)
        if channels > 1:
            arr = arr.reshape(-1, channels).mean(axis=1).astype(np.int16)
        if src_rate != SAMPLE_RATE:
            n = int(len(arr) * SAMPLE_RATE / src_rate)
            arr = np.interp(
                np.linspace(0, len(arr) - 1, n),
                np.arange(len(arr)),
                arr.astype(np.float32),
            ).astype(np.int16)
        return arr.tobytes()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
