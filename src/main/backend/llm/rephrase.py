from groq import Groq
from ..config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """You are a question clarifier for a live interview assistant.

Your only job: take the raw transcribed question and output a single clean, complete, standalone question sentence.

════════════════════════════════════════════════
STRICT RULES
════════════════════════════════════════════════

RULE 1 — Preserve the topic exactly.
  The topic in the raw question MUST appear in your output.
  Never replace or swap the topic with anything from past questions.

  ✗ WRONG: raw="Can you tell me about quantization"  →  output="Fine-tuning of LLMs."
  ✓ RIGHT: raw="Can you tell me about quantization"  →  output="Can you explain what quantization is?"

RULE 2 — Detect if the question is self-contained or dependent.

  SELF-CONTAINED: the question has a clear, complete topic on its own.
    → Do NOT use past questions. Just clean up grammar and make it a proper sentence.

    Examples:
      raw="What is a binary search tree"
      output="What is a binary search tree and how does it work?"

      raw="Can you explain load balancing"
      output="Can you explain what load balancing is and why it is used?"

      raw="Tell me about caching strategies"
      output="Can you describe common caching strategies and their trade-offs?"

  DEPENDENT: the question contains a pronoun or reference with no clear target.
    Trigger words: it, them, they, that, this, the same, the previous, the difference, those, these
    → Use past questions to resolve the reference. Most recent past question = highest priority.

    Examples:
      past=[..., "stack", "queue"]  (queue is most recent)
      raw="What is the difference between them?"
      output="What is the difference between a stack and a queue?"

      past=[..., "lazy loading"]  (most recent)
      raw="Where would you use it?"
      output="Where would you use lazy loading in a real application?"

      past=[..., "REST APIs", "GraphQL"]  (GraphQL is most recent)
      raw="When should you prefer one over the other?"
      output="When should you prefer GraphQL over REST APIs?"

RULE 3 — Output must always be a proper question sentence.
  Never output just a topic phrase or fragment.
  ✗ WRONG: "Fine-tuning of LLMs."
  ✗ WRONG: "Quantization."
  ✓ RIGHT: "Can you explain what quantization is and how it differs from fine-tuning?"

RULE 4 — Do NOT correct spelling or terminology. Output exactly what the speaker meant.

RULE 5 — Output only the final question. No explanation, no prefix, no quotes.

════════════════════════════════════════════════
PAST QUESTIONS WEIGHTING (when needed for DEPENDENT questions only)
════════════════════════════════════════════════
  Q[most recent]     → resolve first
  Q[second recent]   → use if most recent does not resolve the reference
  Q[older]           → only if both above fail
  Ignore past questions entirely for SELF-CONTAINED questions."""


_DEPENDENCY_WORDS = {
    "it", "its", "them", "they", "their", "that", "this",
    "those", "these", "same", "previous", "earlier", "before",
    "difference", "similar", "comparison", "both", "either",
    "one", "other", "another", "latter", "former",
}


def _is_dependent(text: str) -> bool:
    """True if the question contains pronouns/references that need past context."""
    words = set(text.lower().split())
    return bool(words & _DEPENDENCY_WORDS)


def rephrase_question(
    buffer: str,
    past_questions: list[str],
    domain_context: str = "",
) -> str:
    """
    Synchronous — run via loop.run_in_executor.
    Returns rephrased complete question. Falls back to raw buffer on error.
    """
    dependent = _is_dependent(buffer)

    # Only send past questions when the question actually needs them
    if dependent and past_questions:
        past_lines = []
        n = len(past_questions)
        for i, q in enumerate(past_questions):
            if i == n - 1:
                tag = "[MOST RECENT — highest priority]"
            elif i == n - 2:
                tag = "[second most recent]"
            else:
                tag = "[older]"
            past_lines.append(f"  {tag} {q}")
        past_block = "PAST QUESTIONS:\n" + "\n".join(past_lines)
    else:
        past_block = "PAST QUESTIONS: none (question is self-contained — do not use any past context)"

    user_msg = f"RAW QUESTION: {buffer}\n\n{past_block}"

    try:
        resp = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.0,
            max_completion_tokens=120,
            stream=False,
        )
        result = resp.choices[0].message.content.strip()
        # Safety: if output looks like a fragment (no verb, very short), fall back
        if result and len(result.split()) >= 4:
            return result
        return buffer
    except Exception:
        return buffer
