import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.source_schema import SourceCreate, SourceResponse, SourceUpdate
from app.services import source_service

router = APIRouter(prefix="/sources", tags=["Source"])

def _get_or_404(db: Session, source_id: uuid.UUID):
    obj = source_service.get_by_id(db, source_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Source not found")
    return obj


@router.get("/", response_model=list[SourceResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return source_service.get_all(db, skip=skip, limit=limit)


@router.get("/{source_id}", response_model=SourceResponse, dependencies=[Depends(get_current_user)])
def get_item(source_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, source_id)


@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: SourceCreate, db: Session = Depends(get_db)):
    try:
        return source_service.create_source(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")


@router.patch("/{source_id}", response_model=SourceResponse, dependencies=[Depends(admin_only)])
def update_item(source_id: uuid.UUID, data: SourceUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, source_id)
    try:
        return source_service.update_source(db, obj, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(source_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = _get_or_404(db, source_id)
    try:
        source_service.delete_source(db, obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Source is still referenced by other data")
