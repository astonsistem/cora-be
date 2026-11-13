from app.core.soft_delete import SoftDeleteServiceMixin
from app.models.companies import Companies
from app.services.base_service import CrudService

class CompanyService(SoftDeleteServiceMixin, CrudService[Companies]):
    model = Companies
    label = "Company"
    search_column = "company_name"
