import json
from datetime import datetime
from pathlib import Path

from groq import Groq
from ..config import GROQ_API_KEY

_SKILL_DIR = Path(__file__).parent.parent.parent.parent.parent / "skill_profiles"

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """You are preparing interview coaching context from a candidate's skill/background description.

Extract and structure the following as concise bullet points:

• Interview domain  (e.g. Backend Engineering, ML/AI, Data Science, DevOps)
• Key technologies  (list the specific tools, frameworks, languages mentioned)
• Domain terminology  (terms the interviewer is likely to use; correct spellings matter)
• Answer tone  (e.g. system-design depth, theoretical + practical, hands-on examples)
• Likely interview topics  (based on the skills mentioned)

Be specific and actionable. This output is used to:
  1. Make answer suggestions domain-relevant
  2. Correct mis-transcribed domain terms during rephrasing (only when 100% confident)

Output only the bullet points. No headers, no intro sentence."""


def extract_domain_context(raw_skill_text: str) -> str:
    """
    One-time LLM call when the session starts with a Skill input.
    Saves the result to skill_profiles/<timestamp>.json.
    Returns structured domain context string used in rephrase + answer prompts.
    """
    if not raw_skill_text.strip():
        return ""
    try:
        resp = _client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": raw_skill_text},
            ],
            temperature=0.2,
            max_completion_tokens=300,
            stream=False,
        )
        context = resp.choices[0].message.content.strip()
        _save_skill_profile(raw_skill_text, context)
        return context
    except Exception:
        return ""


def _save_skill_profile(raw: str, extracted: str) -> None:
    try:
        _SKILL_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = _SKILL_DIR / f"skill_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "saved_at":  datetime.now().isoformat(),
                "raw_input": raw,
                "extracted": extracted,
            }, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # never crash the session over a log write
