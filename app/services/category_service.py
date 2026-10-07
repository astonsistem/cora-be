from app.models.category import Category
from app.services.base_service import CrudService

class CategoryService(CrudService[Category]):
    model = Category
    label = "Category"
