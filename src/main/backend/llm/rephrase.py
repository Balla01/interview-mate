from groq import Groq
from ..config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """You are a technical interview coach helping clarify interview questions.

You receive:
  - RAW QUESTION: the exact words spoken by the interviewer (speech transcript, may have errors)
  - PAST QUESTIONS: previous questions in this interview, listed oldest → most recent
    (most recent = highest priority for resolving references)
  - DOMAIN CONTEXT (optional): candidate's skill/domain background

Your job — produce ONE clean, self-contained interview question:

STEP 1 — Decide if the raw question is self-contained:
  - Self-contained: "What is dependency injection?" → rephrase as-is, ignore past questions
  - Dependent: "What is the difference between them?" / "Where have you used it?" →
    resolve the reference using past questions (most recent first)

STEP 2 — Apply domain correction (ONLY if domain context is provided):
  - If a word looks like a mis-transcription of a known domain term and you are 100% confident
    of the correction → fix it (e.g. "MCB" → "MCP" if domain is AI tooling)
  - If you are not 100% confident → leave the word unchanged

STEP 3 — Output only the rephrased question. No explanation, no prefix, no quotes."""


def rephrase_question(
    buffer: str,
    past_questions: list[str],
    domain_context: str = "",
) -> str:
    """
    Synchronous — run via loop.run_in_executor.
    Returns rephrased question. Falls back to raw buffer on error.
    """
    # Build recency-weighted past questions block
    if past_questions:
        past_block = "PAST QUESTIONS (oldest → most recent, most recent = highest priority):\n"
        for i, q in enumerate(past_questions, 1):
            weight = "highest priority" if i == len(past_questions) else (
                "high priority" if i == len(past_questions) - 1 else "lower priority"
            )
            past_block += f"  {i}. [{weight}] {q}\n"
    else:
        past_block = "PAST QUESTIONS: none\n"

    domain_block = (
        f"\nDOMAIN CONTEXT:\n{domain_context}\n"
        if domain_context
        else "\nDOMAIN CONTEXT: not provided\n"
    )

    user_msg = f"RAW QUESTION: {buffer}\n\n{past_block}{domain_block}"

    try:
        resp = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
            max_completion_tokens=120,
            stream=False,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return buffer  # graceful fallback
