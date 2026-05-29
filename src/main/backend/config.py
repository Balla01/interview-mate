import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

GROQ_API_KEY: str = os.getenv("groq_api", "")
DEEPGRAM_API_KEY: str = os.getenv("deep_gram_key", "")

SAMPLE_RATE: int = 16000
CHUNK_MS: int = 500
CHUNK_FRAMES: int = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 8000 frames

LLM_MODEL: str = "llama-3.1-8b-instant"
LLM_MAX_TOKENS: int = 1024
LLM_TEMPERATURE: float = 0.7
