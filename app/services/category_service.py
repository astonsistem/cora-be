import uuid

from sqlalchemy import false, func, select

from app.core.soft_delete import SoftDeleteServiceMixin
from app.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.category import Category
from app.models.companies import Companies
from app.models.users import Users
from app.services.base_service import CrudService


class CategoryService(SoftDeleteServiceMixin, CrudService[Category]):
    model = Category
    label = "Category"
    search_column = "name"

    def get_all_for(
        self, current_user: Users, company_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
    ) -> list[Category]:
        query = self._scoped(current_user, self._active(), company_id).order_by(Category.name)
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def get_for_or_404(self, current_user: Users, category_id: uuid.UUID) -> Category:
        query = self._scoped(current_user, self._active()).where(Category.category_id == category_id)
        category = self.db.scalar(query)
        if category is None:
            raise NotFoundError(f"{self.label} not found")
        return category

    def get_deleted_for(
        self,
        current_user: Users,
        company_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        q: str | None = None,
    ) -> list[Category]:
        query = self._scoped(current_user, self._trashed(q), company_id).order_by(Category.deleted_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(min(max(limit, 1), 200))))

    def count_deleted_for(self, current_user: Users, company_id: uuid.UUID | None = None, q: str | None = None) -> int:
        subquery = self._scoped(current_user, self._trashed(q), company_id).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def get_deleted_for_or_404(self, current_user: Users, category_id: uuid.UUID) -> Category:
        query = self._scoped(current_user, self._trashed()).where(Category.category_id == category_id)
        category = self.db.scalar(query)
        if category is None:
            raise NotFoundError(f"{self.label} yang dihapus tidak ditemukan")
        return category

    def create_as(self, current_user: Users, data) -> Category:
        company_id = self._resolve_company(current_user, data.company_id)
        with self._transaction(BadRequestError(self.invalid_reference_message)):
            category = Category(company_id=company_id, **data.model_dump(exclude={"company_id"}))
            self.db.add(category)
            self.db.commit()
        self.db.refresh(category)
        return category

    def _resolve_company(self, current_user: Users, company_id: uuid.UUID | None) -> uuid.UUID:
        if current_user.is_superadmin:
            if company_id is None:
                raise BadRequestError("company_id wajib diisi")
            if self.db.get(Companies, company_id) is None:
                raise BadRequestError("Company tidak ditemukan")
            return company_id
        if current_user.company_id is None:
            raise ForbiddenError("Akun Anda belum terhubung ke company")
        if company_id is not None and company_id != current_user.company_id:
            raise ForbiddenError("Category hanya dapat dikelola untuk company Anda")
        return current_user.company_id

    @staticmethod
    def _scoped(current_user: Users, query, company_id: uuid.UUID | None = None):
        if current_user.is_superadmin:
            return query.where(Category.company_id == company_id) if company_id else query
        if current_user.company_id is None:
            return query.where(false())
        return query.where(Category.company_id == current_user.company_id)
