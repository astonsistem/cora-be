import uuid

from app.exceptions import BadRequestError
from app.models.visit_question import QuestionType, VisitQuestions
from app.schemas.voucher_qr_schema import QrAnswer


class AnswerSheet:
    RATING_RANGE = range(1, 6)

    def __init__(self, questions: list[VisitQuestions], answers: list[QrAnswer]):
        self.questions = questions
        self.given: dict[uuid.UUID, str] = {item.question_id: item.answer.strip() for item in answers}

    def build(self) -> list[dict]:
        return [self._entry(question) for question in self.questions if self._has_value(question)]

    def _has_value(self, question: VisitQuestions) -> bool:
        value = self.given.get(question.question_id, "")
        if value:
            return True
        if question.is_required:
            raise BadRequestError(f"Pertanyaan wajib diisi: {question.question}")
        return False

    def _entry(self, question: VisitQuestions) -> dict:
        value = self.given[question.question_id]
        self._validate(question, value)
        return {"question_id": str(question.question_id), "question": question.question, "answer": value}

    def _validate(self, question: VisitQuestions, value: str) -> None:
        if question.type == QuestionType.rating.value:
            if not value.isdigit() or int(value) not in self.RATING_RANGE:
                raise BadRequestError(f"Rating harus 1 sampai 5: {question.question}")
        elif question.type == QuestionType.choice.value and value not in question.answers:
            raise BadRequestError(f"Pilihan tidak valid: {question.question}")
