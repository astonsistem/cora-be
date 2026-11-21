import uuid

from sqlalchemy.orm import Session

from app.exceptions import BadRequestError
from app.models.category import Category


class CategoryGuard:
    def __init__(self, db: Session):
        self.db = db

    def ensure_in_company(self, category_id: uuid.UUID | None, company_id: uuid.UUID | None) -> None:
        if category_id is None:
            return
        category = self.db.get(Category, category_id)
        if category is None:
            raise BadRequestError("Category tidak ditemukan")
        if category.company_id != company_id:
            raise BadRequestError("Category bukan milik company ini")
