from app.models.sources import Sources
from app.services.base_service import CrudService

class SourceService(CrudService[Sources]):
    model = Sources
    label = "Source"
