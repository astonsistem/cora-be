import uuid

from fastapi import Depends, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_branch_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.models.users import Users
from app.schemas.branch_schema import BranchCreate, BranchResponse, BranchUpdate
from app.services.branch_service import BranchService

router = ApiRouter(prefix="/branches", tags=["Branch"])

@router.get("/", response_model=list[BranchResponse])
def list_items(
    skip: int = 0,
    limit: int = 100,
    service: BranchService = Depends(get_branch_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_all_for(current_user, skip=skip, limit=limit)

@router.get("/{branch_id}", response_model=BranchResponse)
def get_item(
    branch_id: uuid.UUID,
    service: BranchService = Depends(get_branch_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_for_or_404(current_user, branch_id)

@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: BranchCreate, service: BranchService = Depends(get_branch_service)):
    return service.create(data)

@router.patch("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(admin_only)])
def update_item(branch_id: uuid.UUID, data: BranchUpdate, service: BranchService = Depends(get_branch_service)):
    return service.update(service.get_or_404(branch_id), data)

@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(branch_id: uuid.UUID, service: BranchService = Depends(get_branch_service)):
    service.delete(service.get_or_404(branch_id))
