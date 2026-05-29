from collections import deque


class ConversationContext:
    def __init__(self, max_questions: int = 5):
        self._questions: deque[str] = deque(maxlen=max_questions)
        self._answers: deque[str] = deque(maxlen=3)

    def add_interviewer(self, text: str) -> None:
        self._questions.append(text)

    def add_interviewee(self, text: str) -> None:
        self._answers.append(text)

    def format_for_llm(self, current_question: str) -> str:
        lines: list[str] = []

        prev = list(self._questions)
        if prev:
            lines.append("Previous interview questions for context:")
            for q in prev:
                lines.append(f"  Q: {q}")

        recent = list(self._answers)[-2:]
        if recent:
            lines.append("Recent candidate answers:")
            for a in recent:
                lines.append(f"  A: {a[:300]}")

        lines.append(f"\nCurrent interviewer question: {current_question}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._questions.clear()
        self._answers.clear()
