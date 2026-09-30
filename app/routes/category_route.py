import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.category_schema import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["Category"])

def _get_or_404(db: Session, category_id: uuid.UUID):
    obj = category_service.get_by_id(db, category_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Category not found")
    return obj

@router.get("/", response_model=list[CategoryResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return category_service.get_all(db, skip=skip, limit=limit)

@router.get("/{category_id}", response_model=CategoryResponse, dependencies=[Depends(get_current_user)])
def get_item(category_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, category_id)

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: CategoryCreate, db: Session = Depends(get_db)):
    try:
        return category_service.create_category(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.patch("/{category_id}", response_model=CategoryResponse, dependencies=[Depends(admin_only)])
def update_item(category_id: uuid.UUID, data: CategoryUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, category_id)
    try:
        return category_service.update_category(db, obj, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(category_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = _get_or_404(db, category_id)
    try:
        category_service.delete_category(db, obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category is still referenced by other data")
