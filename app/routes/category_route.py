import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_category_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.category_schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category_service import CategoryService

router = ApiRouter(prefix="/categories", tags=["Category"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[CategoryResponse])
def list_items(skip: int = 0, limit: int = 100, service: CategoryService = Depends(get_category_service)):
    return service.get_all(skip=skip, limit=limit)

@router.get("/deleted", response_model=list[CategoryResponse], dependencies=[Depends(admin_only)])
def list_deleted_items(
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    service: CategoryService = Depends(get_category_service),
):
    response.headers["X-Total-Count"] = str(service.count_deleted(q=q))
    return service.get_deleted(skip=skip, limit=limit, q=q)

@router.get("/{category_id}", response_model=CategoryResponse)
def get_item(category_id: uuid.UUID, service: CategoryService = Depends(get_category_service)):
    return service.get_or_404(category_id)

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: CategoryCreate, service: CategoryService = Depends(get_category_service)):
    return service.create(data)

@router.patch("/{category_id}", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
def update_item(category_id: uuid.UUID, data: CategoryUpdate, service: CategoryService = Depends(get_category_service)):
    return service.update(service.get_or_404(category_id), data)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(category_id: uuid.UUID, service: CategoryService = Depends(get_category_service)):
    service.delete(service.get_or_404(category_id))

@router.post("/{category_id}/restore", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
def restore_item(category_id: uuid.UUID, service: CategoryService = Depends(get_category_service)):
    return service.restore(service.get_deleted_or_404(category_id))
