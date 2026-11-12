from app.core.soft_delete import SoftDeleteServiceMixin
from app.models.category import Category
from app.services.base_service import CrudService

class CategoryService(SoftDeleteServiceMixin, CrudService[Category]):
    model = Category
    label = "Category"
    search_column = "name"
