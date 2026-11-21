import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError
from app.models.companies import Companies
from app.models.users import Users
from app.models.visit_question import QuestionType, VisitQuestions
from app.schemas.voucher_qr_schema import VisitQuestionItem
from app.services.company_scope import CompanyScope


class VisitQuestionService:
    MIN_CHOICES = 2

    def __init__(self, db: Session, current_user: Users):
        self.db = db
        self.scope = CompanyScope(current_user)

    def _resolve_company(self, company_id: uuid.UUID | None) -> uuid.UUID:
        if self.scope.restricted:
            return self.scope.company_id
        if company_id is None:
            raise BadRequestError("company_id wajib diisi")
        if self.db.get(Companies, company_id) is None:
            raise BadRequestError("Company tidak ditemukan")
        return company_id

    def _clean_answers(self, item: VisitQuestionItem) -> list[str]:
        if item.type != QuestionType.choice:
            return []
        options = [option.strip() for option in item.answers if option.strip()]
        if len(options) < self.MIN_CHOICES:
            raise BadRequestError(f"Pertanyaan pilihan '{item.question}' minimal punya 2 opsi")
        return options

    def get_for_company(self, company_id: uuid.UUID | None) -> list[VisitQuestions]:
        resolved = self._resolve_company(company_id)
        query = (
            select(VisitQuestions)
            .where(VisitQuestions.company_id == resolved)
            .order_by(VisitQuestions.sort_order, VisitQuestions.created_at)
        )
        return list(self.db.scalars(query))

    def replace_all(self, company_id: uuid.UUID | None, items: list[VisitQuestionItem]) -> list[VisitQuestions]:
        resolved = self._resolve_company(company_id)
        rows = [
            VisitQuestions(
                company_id=resolved,
                question=item.question.strip(),
                type=item.type.value,
                answers=self._clean_answers(item),
                is_required=item.is_required,
                sort_order=index,
            )
            for index, item in enumerate(items)
        ]
        try:
            self.db.execute(delete(VisitQuestions).where(VisitQuestions.company_id == resolved))
            self.db.add_all(rows)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_for_company(resolved)
