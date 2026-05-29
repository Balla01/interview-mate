import webrtcvad

FRAME_MS = 30  # webrtcvad supports 10, 20, or 30 ms frames
SAMPLE_RATE = 16000
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480 samples per frame
FRAME_BYTES = FRAME_SAMPLES * 2  # int16 = 2 bytes/sample


class VADFilter:
    def __init__(self, aggressiveness: int = 2, silence_frames: int = 15):
        self._vad = webrtcvad.Vad(aggressiveness)
        self._silence_threshold = silence_frames
        self._silence_count = 0
        self._speech_active = False

    def process_frame(self, pcm_bytes: bytes) -> dict:
        """
        pcm_bytes must be exactly FRAME_BYTES long at SAMPLE_RATE.
        Returns {"is_speech": bool, "speech_ended": bool}
        speech_ended fires once when a speech segment finishes.
        """
        try:
            is_speech = self._vad.is_speech(pcm_bytes, SAMPLE_RATE)
        except Exception:
            is_speech = False

        speech_ended = False
        if is_speech:
            self._speech_active = True
            self._silence_count = 0
        elif self._speech_active:
            self._silence_count += 1
            if self._silence_count >= self._silence_threshold:
                speech_ended = True
                self._speech_active = False
                self._silence_count = 0

        return {"is_speech": is_speech, "speech_ended": speech_ended}

    def reset(self) -> None:
        self._silence_count = 0
        self._speech_active = False
