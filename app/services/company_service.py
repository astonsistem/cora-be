from app.models.companies import Companies
from app.services.base_service import CrudService

class CompanyService(CrudService[Companies]):
    model = Companies
    label = "Company"
