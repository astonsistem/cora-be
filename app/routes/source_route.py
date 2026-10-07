import uuid

from fastapi import APIRouter, Depends, status

from app.dependencies import get_source_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.source_schema import SourceCreate, SourceResponse, SourceUpdate
from app.services.source_service import SourceService

router = APIRouter(prefix="/sources", tags=["Source"])

@router.get("/", response_model=list[SourceResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, service: SourceService = Depends(get_source_service)):
    return service.get_all(skip=skip, limit=limit)

@router.get("/{source_id}", response_model=SourceResponse, dependencies=[Depends(get_current_user)])
def get_item(source_id: uuid.UUID, service: SourceService = Depends(get_source_service)):
    return service.get_or_404(source_id)

@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: SourceCreate, service: SourceService = Depends(get_source_service)):
    return service.create(data)

@router.patch("/{source_id}", response_model=SourceResponse, dependencies=[Depends(admin_only)])
def update_item(source_id: uuid.UUID, data: SourceUpdate, service: SourceService = Depends(get_source_service)):
    return service.update(service.get_or_404(source_id), data)

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(source_id: uuid.UUID, service: SourceService = Depends(get_source_service)):
    service.delete(service.get_or_404(source_id))
