from collections import deque


class ConversationContext:
    def __init__(self):
        self._raw_interviewer:    deque[str] = deque(maxlen=20)
        self._interviewee:        deque[str] = deque(maxlen=5)
        self._answered_questions: deque[str] = deque(maxlen=5)  # last 5 answered

    def add_interviewer(self, text: str) -> None:
        self._raw_interviewer.append(text)

    def add_interviewee(self, text: str) -> None:
        self._interviewee.append(text)

    def add_answered(self, question: str) -> None:
        self._answered_questions.append(question)

    def get_past_questions(self) -> list[str]:
        """Returns last 5 answered questions, oldest first."""
        return list(self._answered_questions)

    def format_for_answer(self, question: str, domain_context: str = "") -> str:
        lines: list[str] = []

        if domain_context:
            lines.append(f"Candidate domain/skill context:\n{domain_context}\n")

        lines.append(f"Question to answer: {question}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._raw_interviewer.clear()
        self._interviewee.clear()
        self._answered_questions.clear()
