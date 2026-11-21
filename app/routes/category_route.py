import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_category_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.models.users import Users
from app.schemas.category_schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category_service import CategoryService

router = ApiRouter(prefix="/categories", tags=["Category"])

@router.get("/", response_model=list[CategoryResponse])
def list_items(
    company_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_all_for(current_user, company_id=company_id, skip=skip, limit=limit)

@router.get("/deleted", response_model=list[CategoryResponse])
def list_deleted_items(
    company_id: uuid.UUID | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(admin_only),
):
    response.headers["X-Total-Count"] = str(service.count_deleted_for(current_user, company_id=company_id, q=q))
    return service.get_deleted_for(current_user, company_id=company_id, skip=skip, limit=limit, q=q)

@router.get("/{category_id}", response_model=CategoryResponse)
def get_item(
    category_id: uuid.UUID,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_for_or_404(current_user, category_id)

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(admin_only),
):
    return service.create_as(current_user, data)

@router.patch("/{category_id}", response_model=CategoryResponse)
def update_item(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(admin_only),
):
    return service.update(service.get_for_or_404(current_user, category_id), data)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    category_id: uuid.UUID,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(admin_only),
):
    service.delete(service.get_for_or_404(current_user, category_id))

@router.post("/{category_id}/restore", response_model=CategoryResponse)
def restore_item(
    category_id: uuid.UUID,
    service: CategoryService = Depends(get_category_service),
    current_user: Users = Depends(admin_only),
):
    return service.restore(service.get_deleted_for_or_404(current_user, category_id))
