from sqlalchemy import false, func, select

from app.core.soft_delete import SoftDeleteServiceMixin
from app.exceptions import ForbiddenError, NotFoundError
from app.models.branches import Branches
from app.models.users import Users
from app.services.base_service import CrudService
from app.services.company_scope import CompanyScope

class BranchService(SoftDeleteServiceMixin, CrudService[Branches]):
    model = Branches
    label = "Branch"
    search_column = "branch_name"

    def get_all_for(self, current_user: Users, skip: int = 0, limit: int = 100) -> list[Branches]:
        query = self._scoped(current_user, self._active())
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def get_for_or_404(self, current_user: Users, branch_id) -> Branches:
        query = self._scoped(current_user, self._active()).where(Branches.branch_id == branch_id)
        branch = self.db.scalar(query)
        if branch is None:
            raise NotFoundError(f"{self.label} not found")
        return branch

    def get_deleted_for(self, current_user: Users, skip: int = 0, limit: int = 50, q: str | None = None) -> list[Branches]:
        query = self._scoped(current_user, self._trashed(q)).order_by(Branches.deleted_at.desc())
        return list(self.db.scalars(query.offset(skip).limit(min(max(limit, 1), 200))))

    def count_deleted_for(self, current_user: Users, q: str | None = None) -> int:
        subquery = self._scoped(current_user, self._trashed(q)).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def get_deleted_for_or_404(self, current_user: Users, branch_id) -> Branches:
        query = self._scoped(current_user, self._trashed()).where(Branches.branch_id == branch_id)
        branch = self.db.scalar(query)
        if branch is None:
            raise NotFoundError(f"{self.label} yang dihapus tidak ditemukan")
        return branch

    def create_as(self, current_user: Users, data) -> Branches:
        self._ensure_company(current_user, data.company_id)
        return self.create(data)

    def update_as(self, current_user: Users, branch: Branches, data) -> Branches:
        if data.company_id is not None:
            self._ensure_company(current_user, data.company_id)
        return self.update(branch, data)

    def get_all_by_ids(self, branch_ids: list) -> list[Branches]:
        if not branch_ids:
            return []

        query = self._active().where(Branches.branch_id.in_(branch_ids))
        return list(self.db.scalars(query))

    def get_all_by_company(self, company_id) -> list[Branches]:
        query = self._active().where(Branches.company_id == company_id)
        return list(self.db.scalars(query))

    @staticmethod
    def _scoped(current_user: Users, query):
        if current_user.is_superadmin:
            return query
        if current_user.is_admin:
            return query.where(Branches.company_id == CompanyScope(current_user).company_id)
        if current_user.branch_id is None:
            return query.where(false())
        return query.where(Branches.branch_id == current_user.branch_id)

    @staticmethod
    def _ensure_company(current_user: Users, company_id) -> None:
        scope = CompanyScope(current_user)
        if scope.restricted and company_id != scope.company_id:
            raise ForbiddenError("Branch hanya dapat dikelola untuk company Anda")
