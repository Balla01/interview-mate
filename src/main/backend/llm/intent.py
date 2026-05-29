from groq import Groq
from ..config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """You are evaluating whether a spoken interview question is clear enough to answer.

Reply with exactly one word:
  CLEAR   — the question is understandable and answerable as-is
  UNCLEAR — the question is too incomplete, cut off, or ambiguous to answer

Nothing else. No explanation. No punctuation. Just CLEAR or UNCLEAR."""


def detect_intent(transcript: str) -> bool:
    """
    Returns True  → CLEAR   (question is answerable)
    Returns False → UNCLEAR (too incomplete, keep collecting)
    """
    if len(transcript.split()) < 5:
        return False
    try:
        resp = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": f"Question: {transcript}"},
            ],
            temperature=0.0,
            max_completion_tokens=5,
            stream=False,
        )
        result = resp.choices[0].message.content.strip().upper()
        return result == "CLEAR"
    except Exception:
        return False
