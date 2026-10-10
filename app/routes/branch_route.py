import uuid

from fastapi import APIRouter, Depends, status

from app.dependencies import get_branch_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.branch_schema import BranchCreate, BranchResponse, BranchUpdate
from app.services.branch_service import BranchService

router = APIRouter(prefix="/branches", tags=["Branch"], dependencies=[Depends(admin_only)])

@router.get("/", response_model=list[BranchResponse])
def list_items(skip: int = 0, limit: int = 100, service: BranchService = Depends(get_branch_service)):
    return service.get_all(skip=skip, limit=limit)

@router.get("/{branch_id}", response_model=BranchResponse)
def get_item(branch_id: uuid.UUID, service: BranchService = Depends(get_branch_service)):
    return service.get_or_404(branch_id)

@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_item(data: BranchCreate, service: BranchService = Depends(get_branch_service)):
    return service.create(data)

@router.patch("/{branch_id}", response_model=BranchResponse)
def update_item(branch_id: uuid.UUID, data: BranchUpdate, service: BranchService = Depends(get_branch_service)):
    return service.update(service.get_or_404(branch_id), data)

@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(branch_id: uuid.UUID, service: BranchService = Depends(get_branch_service)):
    service.delete(service.get_or_404(branch_id))
