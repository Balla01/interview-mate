from groq import Groq
from ..config import GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
from .prompt import build_messages

_client = Groq(api_key=GROQ_API_KEY)


def stream_tokens(context_str: str):
    """Synchronous generator — run in a thread, not the event loop."""
    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=build_messages(context_str),
        temperature=LLM_TEMPERATURE,
        max_completion_tokens=LLM_MAX_TOKENS,
        top_p=1,
        stream=True,
    )
    for chunk in completion:
        token = chunk.choices[0].delta.content
        if token:
            yield token
