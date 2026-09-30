import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.company_schema import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services import company_service

router = APIRouter(prefix="/companies", tags=["Company"])

def _get_or_404(db: Session, company_id: uuid.UUID):
    obj = company_service.get_by_id(db, company_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return obj

@router.get("/", response_model=list[CompanyResponse], dependencies=[Depends(get_current_user)])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return company_service.get_all(db, skip=skip, limit=limit)

@router.get("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(get_current_user)])
def get_item(company_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, company_id)

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_only)])
def create_item(data: CompanyCreate, db: Session = Depends(get_db)):
    try:
        return company_service.create_company(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.patch("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(admin_only)])
def update_item(company_id: uuid.UUID, data: CompanyUpdate, db: Session = Depends(get_db)):
    obj = _get_or_404(db, company_id)
    try:
        return company_service.update_company(db, obj, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or reference")

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_item(company_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = _get_or_404(db, company_id)
    try:
        company_service.delete_company(db, obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Company is still referenced by other data")
