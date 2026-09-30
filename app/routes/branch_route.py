import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.branch_schema import BranchCreate, BranchResponse, BranchUpdate
from app.services import branch_service

router = APIRouter(prefix="/branches", tags=["Branch"])

def _get_or_404(db: Session, branch_id: uuid.UUID):
    obj = branch_service.get_by_id(db, branch_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Branch not found")
    return obj

@router.get("/", response_model=list[BranchResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return branch_service.get_all(db, skip=skip, limit=limit)

@router.get("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(get_current_user)])
def get_item(branch_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, branch_id)

@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: BranchCreate, db: Session = Depends(get_db)):
    try:
        return branch_service.create_branch(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.patch("/{branch_id}", response_model=BranchResponse, dependencies=[Depends(admin_only)])
def update_item(branch_id: uuid.UUID, data: BranchUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, branch_id)
    try:
        return branch_service.update_branch(db, obj, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(branch_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = _get_or_404(db, branch_id)
    try:
        branch_service.delete_branch(db, obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Branch is still referenced by other data")
