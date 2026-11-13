from app.core.soft_delete import SoftDeleteServiceMixin
from app.exceptions import NotFoundError
from app.models.companies import Companies
from app.models.users import Users
from app.services.base_service import CrudService

class CompanyService(SoftDeleteServiceMixin, CrudService[Companies]):
    model = Companies
    label = "Company"
    search_column = "company_name"

    def get_all_for(self, current_user: Users, skip: int = 0, limit: int = 100) -> list[Companies]:
        query = self._active()
        if not current_user.is_superadmin:
            query = query.where(Companies.company_id == current_user.company_id)
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def get_for_or_404(self, current_user: Users, company_id) -> Companies:
        if not current_user.is_superadmin and company_id != current_user.company_id:
            raise NotFoundError(f"{self.label} not found")
        return self.get_or_404(company_id)
