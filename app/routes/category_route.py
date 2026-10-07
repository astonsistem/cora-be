import uuid

from fastapi import APIRouter, Depends, status

from app.dependencies import get_category_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.category_schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Category"])

@router.get("/", response_model=list[CategoryResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, service: CategoryService = Depends(get_category_service)):
    return service.get_all(skip=skip, limit=limit)

@router.get("/{category_id}", response_model=CategoryResponse, dependencies=[Depends(get_current_user)])
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
