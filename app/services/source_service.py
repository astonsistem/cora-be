from app.core.soft_delete import SoftDeleteServiceMixin
from app.models.sources import Sources
from app.services.base_service import CrudService

class SourceService(SoftDeleteServiceMixin, CrudService[Sources]):
    model = Sources
    label = "Source"
    search_column = "name"
